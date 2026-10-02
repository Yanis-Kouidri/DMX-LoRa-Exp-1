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

BUILTIN_COMMANDS = ("help", "clear", "exit", "quit")

# Complétion basique : commandes intégrées + quelques commandes AT courantes,
# utile comme point de départ avec Tab.
KNOWN_COMMANDS = BUILTIN_COMMANDS + (
    "sys get ver",
    "sys get hweui",
    "sys reset",
    "radio get sf",
    "radio get freq",
    "radio get pwr",
    "radio set sf",
    "radio set freq",
    "radio tx",
    "radio rx",
    "mac pause",
    "mac resume",
)


def print_help() -> None:
    print(
        """
Available commands:
  help               Show this help
  clear              Clear the screen
  exit, quit         Exit the shell

Navigation:
  Up / Down arrows   Recall previous commands (persisted across sessions)
  Tab                Autocomplete known commands

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

    def completer(text: str, state: int) -> str | None:
        matches = [cmd for cmd in KNOWN_COMMANDS if cmd.startswith(text)]
        return matches[state] if state < len(matches) else None

    readline.set_completer(completer)
    readline.parse_and_bind("tab: complete")


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

    def stop(self) -> None:
        self._stop_event.set()

    def run(self) -> None:
        buffer = b""
        while not self._stop_event.is_set():
            try:
                buffer += self._mote.read_available()
            except SerialException as exc:
                self._print(f"Serial communication error: {exc}")
                return

            while b"\n" in buffer:
                line, buffer = buffer.split(b"\n", 1)
                text = line.decode(errors="replace").strip()
                if text:
                    self._print(text)

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
