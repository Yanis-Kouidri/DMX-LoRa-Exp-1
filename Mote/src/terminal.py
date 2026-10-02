"""Shell interactif pour communiquer avec une Mote RN2483 (LoRa)."""

from __future__ import annotations

import argparse
import atexit
import re
import readline
import sys
import threading
import time
from pathlib import Path

from serial import SerialException

from serial_connection import RN2483Connection

PROMPT = "rn2483> "

HISTORY_FILE = Path.home() / ".rn2483_history"
HISTORY_MAX_LENGTH = 1000

# Commandes contenant une clé secrète : jamais enregistrées dans l'historique.
SECRET_COMMAND = re.compile(r"^\s*mac\s+set\s+(appkey|nwkskey|appskey)\b", re.IGNORECASE)

# Délai de lecture du thread série : borne le temps d'arrêt du thread.
READER_POLL_INTERVAL = 0.1

# Attente maximale de la réponse immédiate avant de réafficher l'invite.
IMMEDIATE_RESPONSE_DELAY = 0.5

# Un octet reçu sans fin de ligne depuis ce délai est affiché tel quel :
# c'est le symptôme d'un débit désynchronisé ou d'un module en bootloader.
PARTIAL_LINE_TIMEOUT = 0.5

# Durée pendant laquelle les réponses parasites d'un 'resync' sont ignorées.
RESYNC_DISCARD_DELAY = 0.5

BUILTIN_COMMANDS = ("help", "clear", "exit", "quit", "resync", "hex on", "hex off")

# Commandes RN2483 proposées à la complétion (guide DS40001784G, chapitre 2).
# 'sys eraseFW' en est volontairement absente : elle efface le firmware.
_MAC_SET_PARAMS = (
    "devaddr deveui appeui nwkskey appskey appkey pwridx dr adr bat retx "
    "linkchk rxdelay1 ar rx2 sync upctr dnctr"
)
_MAC_GET_PARAMS = (
    "devaddr deveui appeui dr band pwridx adr retx rxdelay1 rxdelay2 ar rx2 "
    "dcycleps mrgn gwnb status sync upctr dnctr"
)
_RADIO_PARAMS = "bt mod freq pwr sf afcbw rxbw bitrate fdev prlen crc iqi cr wdt bw sync"

RN2483_COMMANDS = (
    "sys sleep",
    "sys reset",
    "sys factoryRESET",
    "sys set nvm",
    "sys set pindig",
    "sys set pinmode",
    "sys get ver",
    "sys get nvm",
    "sys get vdd",
    "sys get hweui",
    "sys get pindig",
    "sys get pinana",
    "mac reset 868",
    "mac reset 433",
    "mac tx cnf",
    "mac tx uncnf",
    "mac join otaa",
    "mac join abp",
    "mac save",
    "mac forceENABLE",
    "mac pause",
    "mac resume",
    *(f"mac set {param}" for param in _MAC_SET_PARAMS.split()),
    *(f"mac set ch {param}" for param in ("freq", "dcycle", "drrange", "status")),
    *(f"mac get {param}" for param in _MAC_GET_PARAMS.split()),
    *(f"mac get ch {param}" for param in ("freq", "dcycle", "drrange", "status")),
    "radio rx",
    "radio tx",
    "radio cw on",
    "radio cw off",
    *(f"radio set {param}" for param in _RADIO_PARAMS.split()),
    *(f"radio get {param}" for param in _RADIO_PARAMS.split()),
    "radio get snr",
    "radio get rssi",
)

COMPLETION_TREE = tuple(tuple(cmd.split()) for cmd in BUILTIN_COMMANDS + RN2483_COMMANDS)

USING_LIBEDIT = getattr(readline, "backend", None) == "editline" or "libedit" in (readline.__doc__ or "")


def print_help() -> None:
    print(
        """
Available commands:
  help               Show this help
  clear              Clear the screen
  exit, quit         Exit the shell
  resync             Re-sync the mote baudrate (Break + 0x55)
  hex on | hex off   Also show received bytes in hexadecimal

Navigation:
  Up / Down arrows   Recall previous commands (persisted across sessions)
  Tab                Autocomplete commands word by word (Tab twice to list)

Any other command is sent directly to the RN2483. Responses are displayed
as they arrive, including delayed ones (mac join, mac tx, radio rx...).
Commands setting a key (mac set appkey/nwkskey/appskey) are not saved
in the history.

Examples:
  sys get ver
  sys get hweui
  radio get sf
  radio get freq
  mac pause
  radio tx 48656C6C6F
"""
    )


def clear_screen() -> None:
    print("\033[2J\033[H", end="")


def setup_readline() -> None:
    """Configure l'historique persistant et l'auto-complétion."""

    readline.set_history_length(HISTORY_MAX_LENGTH)

    if HISTORY_FILE.exists():
        readline.read_history_file(HISTORY_FILE)
        purge_secret_history()

    atexit.register(save_history)

    readline.set_completer(complete)
    # Seuls les espaces séparent les mots : 'text' est alors le mot en cours.
    readline.set_completer_delims(" \t")

    # La syntaxe de configuration diffère entre GNU readline et libedit
    # (backend par défaut de certains Python, dont celui de ce projet).
    if USING_LIBEDIT:
        readline.parse_and_bind("bind ^I rl_complete")
    else:
        readline.parse_and_bind("tab: complete")


def completion_candidates(line: str) -> list[str]:
    """
    Retourne les mots possibles pour compléter le dernier mot de `line`.

    La complétion se fait mot par mot : avec 'mac g', propose 'get' ;
    avec 'mac get ', propose tous les paramètres de 'mac get'.
    """

    words = line.split()
    if line and not line[-1].isspace():
        prefix_words, partial = words[:-1], words[-1]
    else:
        prefix_words, partial = words, ""

    depth = len(prefix_words)
    matches = {
        cmd[depth]
        for cmd in COMPLETION_TREE
        if len(cmd) > depth
        and [w.lower() for w in cmd[:depth]] == [w.lower() for w in prefix_words]
        and cmd[depth].lower().startswith(partial.lower())
    }
    return sorted(matches)


_completion_matches: list[str] = []


def complete(text: str, state: int) -> str | None:
    """Fonction de complétion readline (appelée avec state = 0, 1, 2...)."""

    global _completion_matches
    if state == 0:
        line = readline.get_line_buffer()[: readline.get_endidx()]
        _completion_matches = completion_candidates(line)
        # GNU readline ajoute un espace après une complétion unique, pas libedit.
        if USING_LIBEDIT and len(_completion_matches) == 1:
            _completion_matches = [f"{_completion_matches[0]} "]
    return _completion_matches[state] if state < len(_completion_matches) else None


def purge_secret_history() -> None:
    """Retire de l'historique chargé les commandes contenant une clé."""

    # Les index readline commencent à 1 ; on parcourt à l'envers pour supprimer sans décaler.
    for index in range(readline.get_current_history_length(), 0, -1):
        item = readline.get_history_item(index)
        if item and SECRET_COMMAND.match(item):
            readline.remove_history_item(index - 1)


def forget_last_command(raw_input: str) -> None:
    """Retire la dernière saisie de l'historique (ajoutée automatiquement par input())."""

    # input() n'alimente l'historique qu'en mode interactif : on vérifie que
    # la dernière entrée est bien la saisie avant de la supprimer.
    length = readline.get_current_history_length()
    if length and readline.get_history_item(length) == raw_input:
        readline.remove_history_item(length - 1)


def save_history() -> None:
    try:
        readline.write_history_file(HISTORY_FILE)
    except OSError as exc:
        print(f"Warning: could not save command history: {exc}")


class SerialReader(threading.Thread):
    """
    Lit le port série en continu et affiche chaque ligne dès sa réception.

    Indispensable pour les commandes à double réponse (mac join, mac tx,
    radio tx/rx...) dont la seconde réponse arrive plusieurs secondes après.
    """

    def __init__(self, mote: RN2483Connection) -> None:
        super().__init__(daemon=True)
        self._mote = mote
        self._stop_event = threading.Event()
        self._interactive = sys.stdin.isatty()
        self.last_activity = time.monotonic()
        # Positionné par la boucle principale pendant qu'input() attend une saisie.
        self.prompt_active = threading.Event()
        # Affiche aussi les octets reçus en hexadécimal (commande 'hex on').
        self.hex_mode = False
        # Les lignes reçues avant cet instant sont ignorées (voir 'resync').
        self.discard_until = 0.0

    def stop(self) -> None:
        self._stop_event.set()

    def run(self) -> None:
        buffer = b""
        last_byte_at = time.monotonic()
        while not self._stop_event.is_set():
            try:
                data = self._mote.read_available()
            except SerialException as exc:
                self._print(f"Serial communication error: {exc}")
                return

            if data:
                buffer += data
                last_byte_at = time.monotonic()

            while b"\n" in buffer:
                line, buffer = buffer.split(b"\n", 1)
                self._handle_line(line, complete_line=True)

            # Octets sans fin de ligne : une réponse RN2483 se termine toujours
            # par \r\n, on les affiche donc comme anomalie après un délai.
            if buffer and time.monotonic() - last_byte_at > PARTIAL_LINE_TIMEOUT:
                self._handle_line(buffer, complete_line=False)
                buffer = b""

    def _handle_line(self, raw: bytes, complete_line: bool) -> None:
        raw = raw.rstrip(b"\r")
        if not raw or time.monotonic() < self.discard_until:
            return

        text = raw.decode(errors="replace").strip()
        if self.hex_mode:
            text = f"{text}  [{raw.hex(' ')}]"

        readable = all(0x20 <= byte < 0x7F or byte == 0x09 for byte in raw)
        if readable and complete_line:
            self._print(text)
            return

        self._print(f"{text}  [{raw.hex(' ')}]" if not self.hex_mode else text)
        self._print(
            "Warning: unreadable or unterminated response. The baudrate may be out of "
            "sync: try 'resync'. If every command gets 2 garbled bytes back, the mote "
            "is probably in bootloader mode: reflash it with 'flash_firmware.py --resume'."
        )

    def _print(self, text: str) -> None:
        """Affiche une ligne sans casser la saisie en cours."""

        self.last_activity = time.monotonic()
        if self._interactive and self.prompt_active.is_set():
            # Efface la ligne d'invite, affiche la réponse, puis redessine
            # l'invite avec ce que l'utilisateur était en train de taper.
            sys.stdout.write(f"\r\033[K{text}\n{PROMPT}{readline.get_line_buffer()}")
        else:
            sys.stdout.write(f"{text}\n")
        sys.stdout.flush()

    def wait_for_response(self, since: float, timeout: float) -> None:
        """Attend une réponse reçue après `since`, au plus `timeout` secondes."""

        deadline = since + timeout
        while self.last_activity <= since and time.monotonic() < deadline:
            time.sleep(READER_POLL_INTERVAL / 2)

    def wait_until_idle(self, quiet_period: float) -> None:
        """Attend qu'aucune réponse ne soit arrivée depuis `quiet_period` secondes."""

        while time.monotonic() - self.last_activity < quiet_period:
            time.sleep(READER_POLL_INTERVAL)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Interactive shell for the RN2483 LoRa mote.")
    parser.add_argument(
        "-p",
        "--port",
        default="/dev/ttyACM0",
        help="Serial port the mote is connected to (default: %(default)s)",
    )
    parser.add_argument(
        "-b",
        "--baudrate",
        type=int,
        default=57600,
        help="Serial baudrate (default: %(default)s)",
    )
    parser.add_argument(
        "-t",
        "--timeout",
        type=float,
        default=1.0,
        help=(
            "When stdin is not a terminal, seconds to wait for a response after each "
            "command and for pending responses before exiting (default: %(default)s)"
        ),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    setup_readline()

    try:
        mote = RN2483Connection(args.port, baudrate=args.baudrate, timeout=READER_POLL_INTERVAL)
    except SerialException as exc:
        print(f"Could not open serial port {args.port!r}: {exc}")
        return

    interactive = sys.stdin.isatty()
    reader = SerialReader(mote)
    reader.start()

    print("RN2483 Interactive Shell")
    print(f"Connected to {args.port} at {args.baudrate} baud.")
    print("Type 'help' for available commands.\n")

    try:
        while True:
            reader.prompt_active.set()
            try:
                raw_input = input(PROMPT if interactive else "")
            except EOFError:
                if not interactive:
                    reader.wait_until_idle(args.timeout)
                print()
                break
            finally:
                reader.prompt_active.clear()

            command = raw_input.strip()

            if not command:
                continue

            if SECRET_COMMAND.match(command):
                forget_last_command(raw_input)

            if command in {"exit", "quit"}:
                break

            if command == "help":
                print_help()
                continue

            if command == "clear":
                clear_screen()
                continue

            if command in {"hex on", "hex off"}:
                reader.hex_mode = command == "hex on"
                print(f"Hexadecimal display {'enabled' if reader.hex_mode else 'disabled'}.")
                continue

            if command == "resync":
                print("Re-syncing baudrate, then checking with 'sys get ver'...")
                # Le Break et le 0x55 laissent des octets parasites dans le tampon de
                # commande du module : une ligne vide le vide, et sa réponse
                # 'invalid_param' est ignorée.
                reader.discard_until = time.monotonic() + RESYNC_DISCARD_DELAY
                try:
                    mote.resync_baudrate()
                    time.sleep(0.1)
                    mote.write_command("")
                except SerialException as exc:
                    print(f"Serial communication error: {exc}")
                    continue
                time.sleep(RESYNC_DISCARD_DELAY)
                command = "sys get ver"

            if not interactive:
                print(f"> {command}", flush=True)

            sent_at = time.monotonic()
            try:
                mote.write_command(command)
            except SerialException as exc:
                print(f"Serial communication error: {exc}")
                continue

            if interactive:
                # Laisse la réponse immédiate s'afficher avant de redonner l'invite ;
                # les réponses tardives s'intercalent ensuite dans la saisie.
                reader.wait_for_response(sent_at, IMMEDIATE_RESPONSE_DELAY)
            else:
                # Sans terminal, les commandes arrivent d'un bloc : on laisse au
                # module le temps de répondre avant d'envoyer la suivante.
                reader.wait_for_response(sent_at, args.timeout)

    except KeyboardInterrupt:
        print("\nInterrupted.")

    finally:
        reader.stop()
        reader.join()
        mote.close()
        print("Connection closed.")


if __name__ == "__main__":
    main()
