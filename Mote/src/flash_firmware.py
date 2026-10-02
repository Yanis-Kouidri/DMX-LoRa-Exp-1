"""Mise à jour du firmware d'un RN2483 via son bootloader UART.

Implémente le protocole décrit au chapitre 3 du "RN2483 LoRa Technology Module
Command Reference User's Guide" (DS40001784G), complété par la lecture du source
du bootloader (pic18f_bootload.asm, dépôt MicrochipTech/RN2xx3_LORAWAN_FIRMWARE).

Points importants issus du source du bootloader :
- Le bootloader occupe 0x0000-0x02FF et n'est PAS protégé en écriture. Il ne
  vérifie pas les adresses reçues : toute écriture/effacement sous 0x300 le
  détruirait (récupération uniquement via ICSP). Ce script refuse donc toute
  adresse hors de [APP_START, APP_END[.
- Au démarrage, le bootloader calcule la somme des mots 16 bits de 0x300 à
  0xFFFD et la compare au mot stocké en 0xFFFE. Si elle ne correspond pas, il
  reste en mode bootloader : une mise à jour interrompue est donc rattrapable
  en relançant ce script avec --resume.
- Chaque commande est précédée de 0x55 (auto-baud) ; chaque réponse commence
  par 0x55 suivi de l'écho de l'en-tête de commande.
"""

from __future__ import annotations

import argparse
import struct
import sys
import time
from pathlib import Path

from serial import Serial

APP_START = 0x300
APP_END = 0x10000  # exclu
ROW_SIZE = 0x40  # taille d'effacement et de latch d'écriture (PIC18LF46K22)

STX = 0x55
KEY1 = 0x55
KEY2 = 0xAA

CMD_VERSION = 0x00
CMD_READ = 0x01  # non documenté dans le guide, mais présent dans le source
CMD_WRITE = 0x02
CMD_ERASE = 0x03
CMD_CHECKSUM = 0x08
CMD_RESET = 0x09

HEADER_SIZE = 9  # CMD, LenL, LenH, Key1, Key2, Addr (4 octets)


class BootloaderError(RuntimeError):
    pass


# --------------------------------------------------------------------------- #
# Fichier Intel HEX
# --------------------------------------------------------------------------- #


def load_hex(path: Path) -> dict[int, int]:
    """Charge un fichier Intel HEX et retourne {adresse: octet}."""

    memory: dict[int, int] = {}
    base = 0

    for line_number, line in enumerate(path.read_text().splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        if not line.startswith(":"):
            raise ValueError(f"Ligne {line_number} : format Intel HEX invalide")

        record = bytes.fromhex(line[1:])
        if sum(record) & 0xFF:
            raise ValueError(f"Ligne {line_number} : checksum Intel HEX invalide")

        length, address, record_type = record[0], (record[1] << 8) | record[2], record[3]
        data = record[4 : 4 + length]

        if record_type == 0x00:
            for offset, value in enumerate(data):
                memory[base + address + offset] = value
        elif record_type == 0x01:
            break
        elif record_type == 0x02:
            base = ((data[0] << 8) | data[1]) << 4
        elif record_type == 0x04:
            base = ((data[0] << 8) | data[1]) << 16
        else:
            raise ValueError(f"Ligne {line_number} : type d'enregistrement {record_type:#x} non géré")

    return memory


def build_image(memory: dict[int, int]) -> bytearray:
    """
    Construit l'image applicative [APP_START, APP_END[ (remplie à 0xFF).

    Refuse toute donnée de mémoire programme sous APP_START (zone bootloader).
    Les données hors mémoire programme (User ID 0x200000, config 0x300000)
    sont ignorées : le bootloader ne doit pas toucher aux fusibles.
    """

    below = [a for a in memory if a < APP_START]
    if below:
        raise ValueError(
            f"Le fichier contient {len(below)} octets sous {APP_START:#x} (zone bootloader). "
            "Utiliser le fichier 'offset' et non 'combined'."
        )

    ignored = sorted(a for a in memory if a >= APP_END)
    if ignored:
        print(f"Info : {len(ignored)} octets hors mémoire programme ignorés (ID/config).")

    image = bytearray(b"\xff" * (APP_END - APP_START))
    for address, value in memory.items():
        if APP_START <= address < APP_END:
            image[address - APP_START] = value

    return image


def word_checksum(data: bytes) -> int:
    """Somme des mots 16 bits little-endian (algorithme du bootloader)."""

    if len(data) % 2:
        data = data + b"\xff"
    return sum(struct.unpack(f"<{len(data) // 2}H", data)) & 0xFFFF


def check_app_checksum(image: bytearray) -> int:
    """Vérifie que le mot en 0xFFFE correspond à la somme de 0x300-0xFFFD."""

    expected = word_checksum(bytes(image[:-2]))
    stored = image[-2] | (image[-1] << 8)
    if expected != stored:
        raise ValueError(
            f"Checksum applicatif incohérent : calculé {expected:#06x}, stocké {stored:#06x}. "
            "Le module resterait en bootloader après reset."
        )
    return stored


# --------------------------------------------------------------------------- #
# Protocole bootloader
# --------------------------------------------------------------------------- #


class Bootloader:
    def __init__(self, serial: Serial, verbose: bool = False) -> None:
        self._serial = serial
        self._verbose = verbose

    @staticmethod
    def _check_range(address: int, size: int) -> None:
        if address < APP_START or address + size > APP_END:
            raise BootloaderError(
                f"Accès refusé à [{address:#x}, {address + size:#x}[ : hors zone applicative"
            )

    def _transact(
        self,
        command: int,
        length: int,
        address: int,
        payload: bytes = b"",
        keys: bool = False,
        response_size: int = 0,
        timeout: float = 2.0,
    ) -> bytes:
        """Envoie une commande et retourne la réponse (sans le 0x55 initial)."""

        header = struct.pack(
            "<BBBBBI",
            command,
            length & 0xFF,
            0x00,
            KEY1 if keys else 0x00,
            KEY2 if keys else 0x00,
            address,
        )
        frame = bytes([STX]) + header + payload

        self._serial.reset_input_buffer()
        self._serial.write(frame)
        self._serial.flush()

        deadline = time.monotonic() + timeout

        # On ignore les éventuels octets parasites avant le 0x55 de réponse.
        while True:
            if time.monotonic() > deadline:
                raise BootloaderError(f"Pas de réponse à la commande {command:#04x}")
            byte = self._serial.read(1)
            if byte == bytes([STX]):
                break
            if byte and self._verbose:
                print(f"  (octet ignoré : {byte.hex()})")

        response = bytearray()
        while len(response) < response_size:
            if time.monotonic() > deadline:
                raise BootloaderError(
                    f"Réponse incomplète à la commande {command:#04x} : "
                    f"{len(response)}/{response_size} octets ({response.hex()})"
                )
            response += self._serial.read(response_size - len(response))

        if response[0] == 0xFF:
            raise BootloaderError(f"Commande {command:#04x} rejetée par le bootloader")
        if response[0] != command:
            raise BootloaderError(
                f"Écho de commande inattendu : {response[0]:#04x} au lieu de {command:#04x}"
            )
        echoed_address = struct.unpack_from("<I", response, 5)[0]
        if echoed_address & 0xFFFFFF != address & 0xFFFFFF:
            raise BootloaderError(
                f"Écho d'adresse inattendu : {echoed_address:#x} au lieu de {address:#x}"
            )

        return bytes(response)

    def get_version(self) -> dict[str, int]:
        response = self._transact(CMD_VERSION, 0, 0, response_size=HEADER_SIZE + 16)
        info = response[HEADER_SIZE:]
        return {
            "version": info[0] | (info[1] << 8),
            "device_id": info[6] | (info[7] << 8),
            "erase_row_size": info[10],
            "write_latch_size": info[11],
        }

    def erase(self, address: int, rows: int) -> None:
        if not 1 <= rows <= 256:
            raise ValueError("rows doit être compris entre 1 et 256")
        self._check_range(address, rows * ROW_SIZE)
        response = self._transact(
            CMD_ERASE, rows & 0xFF, address, keys=True, response_size=HEADER_SIZE + 1, timeout=10.0
        )
        if response[HEADER_SIZE] != 0x01:
            raise BootloaderError(f"Échec d'effacement à {address:#x}")

    def write_row(self, address: int, data: bytes) -> None:
        if len(data) != ROW_SIZE or address % ROW_SIZE:
            raise ValueError("Écriture limitée à une ligne complète et alignée")
        self._check_range(address, len(data))
        response = self._transact(
            CMD_WRITE, len(data), address, payload=data, keys=True, response_size=HEADER_SIZE + 1
        )
        if response[HEADER_SIZE] != 0x01:
            raise BootloaderError(f"Échec d'écriture à {address:#x}")

    def read(self, address: int, size: int) -> bytes:
        if not 1 <= size <= ROW_SIZE:
            raise ValueError(f"Lecture limitée à {ROW_SIZE} octets")
        self._check_range(address, size)
        response = self._transact(CMD_READ, size, address, response_size=HEADER_SIZE + size)
        return response[HEADER_SIZE:]

    def checksum(self, address: int, size: int) -> int:
        if not 2 <= size <= 254 or size % 2:
            raise ValueError("Taille de checksum paire, entre 2 et 254")
        self._check_range(address, size)
        response = self._transact(CMD_CHECKSUM, size, address, response_size=HEADER_SIZE + 2)
        return response[HEADER_SIZE] | (response[HEADER_SIZE + 1] << 8)

    def reset(self) -> None:
        frame = bytes([STX]) + struct.pack("<BBBBBI", CMD_RESET, 0, 0, 0, 0, 0)
        self._serial.write(frame)
        self._serial.flush()


# --------------------------------------------------------------------------- #
# Séquence de mise à jour
# --------------------------------------------------------------------------- #


def erase_plan() -> list[tuple[int, int]]:
    """Découpe [APP_START, APP_END[ en commandes d'effacement de 256 lignes max."""

    plan = []
    address = APP_START
    while address < APP_END:
        rows = min(256, (APP_END - address) // ROW_SIZE)
        plan.append((address, rows))
        address += rows * ROW_SIZE
    return plan


def read_text_line(serial: Serial, timeout: float) -> str:
    original_timeout = serial.timeout
    serial.timeout = timeout
    try:
        return serial.readline().decode(errors="replace").strip()
    finally:
        serial.timeout = original_timeout


def enter_bootloader(serial: Serial) -> None:
    """Vérifie que le firmware répond, puis l'efface avec sys eraseFW."""

    serial.reset_input_buffer()
    serial.write(b"sys get ver\r\n")
    version = read_text_line(serial, timeout=2.0)
    if not version.startswith("RN2483"):
        raise BootloaderError(
            f"Réponse inattendue à 'sys get ver' : {version!r}. "
            "Une réponse vide ou de 2 octets illisibles indique en général que le module "
            "est déjà en bootloader : relancer avec --resume."
        )
    print(f"Firmware actuel : {version}")

    print("Envoi de 'sys eraseFW'...")
    serial.write(b"sys eraseFW\r\n")
    serial.flush()
    time.sleep(2.0)
    serial.reset_input_buffer()


def resync_bootloader(serial: Serial) -> None:
    """
    Remet le bootloader en attente d'auto-baud.

    S'il a reçu du texte (ex: 'sys get ver'), il a calé son débit sur un mauvais
    caractère et peut être au milieu d'une trame. Une série de 0x55 recale
    l'auto-baud et complète la trame en cours avec la commande 0x55, toujours
    rejetée (réponse 0x55 0xFF) : sans effet sur la flash.
    """

    for _ in range(3):
        serial.write(bytes([STX]) * (HEADER_SIZE + 1))
        serial.flush()
        time.sleep(0.3)
    serial.reset_input_buffer()


def connect_bootloader(bootloader: Bootloader, serial: Serial, attempts: int = 5) -> dict[str, int]:
    resync_bootloader(serial)
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            return bootloader.get_version()
        except BootloaderError as exc:
            last_error = exc
            print(f"  tentative {attempt}/{attempts} : {exc}")
            time.sleep(0.5)
            resync_bootloader(serial)
    raise BootloaderError(f"Bootloader injoignable : {last_error}")


def flash(bootloader: Bootloader, image: bytearray) -> None:
    print("Effacement de la zone applicative...")
    for address, rows in erase_plan():
        print(f"  erase {address:#06x} ({rows} lignes)")
        bootloader.erase(address, rows)

    rows = [
        (APP_START + offset, bytes(image[offset : offset + ROW_SIZE]))
        for offset in range(0, len(image), ROW_SIZE)
    ]
    to_write = [(a, d) for a, d in rows if d != b"\xff" * ROW_SIZE]

    print(f"Écriture de {len(to_write)} lignes de {ROW_SIZE} octets...")
    start = time.monotonic()
    for index, (address, data) in enumerate(to_write, start=1):
        bootloader.write_row(address, data)
        if index % 64 == 0 or index == len(to_write):
            print(f"  {index}/{len(to_write)} ({address:#06x}) - {time.monotonic() - start:.1f}s")


def verify(bootloader: Bootloader, image: bytearray) -> None:
    """Relit toute la zone applicative, ou compare des checksums si la lecture n'est pas supportée."""

    print("Vérification...")
    try:
        bootloader.read(APP_START, ROW_SIZE)
        use_read = True
    except BootloaderError as exc:
        print(f"  lecture non supportée ({exc}), vérification par checksum")
        use_read = False

    for offset in range(0, len(image), ROW_SIZE):
        address = APP_START + offset
        expected = bytes(image[offset : offset + ROW_SIZE])
        if use_read:
            actual = bootloader.read(address, ROW_SIZE)
            if actual != expected:
                raise BootloaderError(f"Contenu différent à {address:#06x}")
        else:
            actual_sum = bootloader.checksum(address, ROW_SIZE)
            if actual_sum != word_checksum(expected):
                raise BootloaderError(f"Checksum différent à {address:#06x}")

    print("  contenu vérifié")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Update RN2483 firmware via its UART bootloader.")
    parser.add_argument("hex_file", type=Path, help="Firmware HEX file ('offset' variant)")
    parser.add_argument("-p", "--port", default="/dev/ttyACM0", help="Serial port (default: %(default)s)")
    parser.add_argument("-b", "--baudrate", type=int, default=57600, help="Baudrate (default: %(default)s)")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only parse and check the HEX file, do not touch the module",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Module is already in bootloader mode (skip 'sys eraseFW')",
    )
    parser.add_argument("--yes", action="store_true", help="Do not ask for confirmation")
    parser.add_argument("-v", "--verbose", action="store_true", help="Show ignored bytes")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    image = build_image(load_hex(args.hex_file))
    app_checksum = check_app_checksum(image)
    used_rows = sum(
        1 for offset in range(0, len(image), ROW_SIZE) if image[offset : offset + ROW_SIZE] != b"\xff" * ROW_SIZE
    )
    print(f"Fichier : {args.hex_file}")
    print(f"Zone applicative : {APP_START:#06x}-{APP_END - 1:#06x}, {used_rows} lignes utilisées")
    print(f"Checksum applicatif : {app_checksum:#06x} (cohérent)")
    print("Plan d'effacement : " + ", ".join(f"{a:#06x}x{r}" for a, r in erase_plan()))

    if args.dry_run:
        print("Dry run : aucune action sur le module.")
        return 0

    if not args.yes:
        answer = input("Le firmware actuel va être effacé. Taper 'FLASH' pour continuer : ")
        if answer.strip() != "FLASH":
            print("Annulé.")
            return 1

    with Serial(args.port, baudrate=args.baudrate, timeout=0.5) as serial:
        bootloader = Bootloader(serial, verbose=args.verbose)

        if not args.resume:
            enter_bootloader(serial)

        info = connect_bootloader(bootloader, serial)
        print(
            f"Bootloader v{info['version'] >> 8}.{info['version'] & 0xFF}, "
            f"device ID {info['device_id']:#06x}, "
            f"erase row {info['erase_row_size']}, write latch {info['write_latch_size']}"
        )
        if info["erase_row_size"] != ROW_SIZE or info["write_latch_size"] != ROW_SIZE:
            raise BootloaderError("Tailles de ligne inattendues, arrêt par sécurité")

        flash(bootloader, image)
        verify(bootloader, image)

        print("Reset du module...")
        bootloader.reset()
        banner = read_text_line(serial, timeout=3.0)
        if banner:
            print(f"Au démarrage : {banner}")

        serial.reset_input_buffer()
        serial.write(b"sys get ver\r\n")
        version = read_text_line(serial, timeout=2.0)
        print(f"sys get ver : {version or '(pas de réponse)'}")

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (BootloaderError, ValueError) as exc:
        print(f"Erreur : {exc}")
        print("Si le firmware a déjà été effacé, le module est en bootloader : relancer avec --resume.")
        sys.exit(1)
