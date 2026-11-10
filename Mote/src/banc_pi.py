"""
Banc PPK2, côté Raspberry Pi : séquence de messages LoRaWAN avec repères sur D0.

Voir Mote/banc-ppk2.md. Ce script tourne sur `pi-ppk2`, lancé par
`banc_ppk2.py` (WSL) pendant que `ppk2_record.py` (Windows) alimente la mote et
enregistre le courant. Il pilote le RN2483 par l'UART du Pi (`/dev/ttyAMA0`).

Pour chaque répétition :
1. `sys sleep` : le module dort, la carte ne consomme que son fond (sert de
   référence pour soustraire le fond de la carte). La durée est au moins le
   repos imposé par le duty cycle après une émission à ce SF, pour limiter
   les refus `no_free_ch` ;
2. réveil, resynchronisation de la liaison (break puis 0x55), courte attente
   au repos ;
3. repère haut sur GPIO17 (relié à D0 du PPK2), puis `mac tx` ;
4. lecture de la réponse immédiate, puis de la réponse asynchrone (fin de RX2) ;
5. repère bas.

Le repère est posé dans le flux du PPK2 : le découpage des messages ne dépend
d'aucune horloge d'ordinateur. Les instants de l'horloge monotone du Pi sont
quand même transmis, pour situer la fenêtre de fond et contrôler qu'aucun
échantillon n'a été perdu entre deux repères.

Le duty cycle du module reste actif (1 %, comme sur le terrain) : si la
commande répond `no_free_ch`, la tentative est marquée et la répétition est
retentée après un nouveau sommeil.

Session ABP factice et locale (aucun réseau n'est censé recevoir) : DevAddr de
la plage expérimentale, clés factices, sans `mac save`, pour ne pas écraser
l'identité OTAA enregistrée dans le module. En mode `cnf`, `retx` vaut 0 : sans
réseau, l'ACK n'arrive jamais et le message mesuré est une sonde ratée.

Une ligne JSON par tentative est écrite sur la sortie standard. Une chaîne de
version reçue sans l'avoir demandée signale un redémarrage du module
(`reset_seen`) : la tentative concernée est à rejeter.

GPIO14 (TX du Pi) est mis en TXD0 au début et remis en entrée à la fin, même
en cas d'erreur : quand le PPK2 ne l'alimente plus, la mote ne doit pas être
alimentée par sa ligne série.
"""

from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
import time

import serial

PORT = "/dev/ttyAMA0"
MARKER_GPIO = "17"
TX_GPIO = "14"
DR_FOR_SF = {7: 5, 8: 4, 9: 3, 10: 2, 11: 1, 12: 0}
SETTLE_S = 0.3  # repos entre le réveil et le repère haut
ASYNC_TIMEOUT_S = 15.0
LORAWAN_OVERHEAD_BYTES = 13  # MHDR + FHDR (sans FOpts) + FPort + MIC
DUTY_CYCLE_FACTOR = 101  # 3 canaux par défaut à 0,33 % chacun : ~1 % en moyenne


def airtime_seconds(sf: int, payload_bytes: int) -> float:
    """Temps d'émission LoRa, 125 kHz, CR 4/5, préambule 8, en-tête explicite, CRC."""

    ldro = 1 if sf >= 11 else 0
    numerator = 8 * payload_bytes - 4 * sf + 28 + 16
    symbols = 8 + max(math.ceil(numerator / (4 * (sf - 2 * ldro))) * 5, 0)
    return (8 + 4.25 + symbols) * (2**sf) / 125_000


def sleep_ms_for(sf: int, args: argparse.Namespace) -> int:
    """Sommeil avant chaque tentative : au moins le temps de repos imposé par le duty cycle."""

    airtime = airtime_seconds(sf, args.payload + LORAWAN_OVERHEAD_BYTES)
    return max(args.sleep_ms, math.ceil(airtime * DUTY_CYCLE_FACTOR * 1000))


def pinctrl(*args: str) -> None:
    subprocess.run(["pinctrl", "set", *args], check=True)


def emit(record: dict) -> None:
    print(json.dumps(record), flush=True)


class Mote:
    """Liaison série avec le RN2483, avec détection des redémarrages."""

    def __init__(self) -> None:
        self.ser = serial.Serial(PORT, 57600, timeout=2)
        self.resets: list[str] = []

    def resync(self) -> None:
        self.ser.send_break(0.05)
        time.sleep(0.02)
        self.ser.write(b"\x55")
        time.sleep(0.05)
        self.drain()

    def drain(self) -> None:
        """Vide l'entrée en relevant les chaînes de version spontanées."""

        for raw in self.ser.read(self.ser.in_waiting).split(b"\n"):
            line = raw.decode("ascii", "replace").strip()
            if line.startswith("RN2483"):
                self.resets.append(line)

    def readline(self, timeout: float) -> str:
        self.ser.timeout = timeout
        line = self.ser.readline().decode("ascii", "replace").strip()
        if line.startswith("RN2483"):
            self.resets.append(line)
        return line

    def cmd(self, command: str, timeout: float = 2.0) -> str:
        self.drain()
        self.ser.write(f"{command}\r\n".encode())
        return self.readline(timeout)

    def expect(self, command: str, answer: str = "ok") -> None:
        reply = self.cmd(command)
        if reply != answer:
            raise RuntimeError(f"{command!r} -> {reply!r} (attendu {answer!r})")


def setup(mote: Mote, args: argparse.Namespace) -> dict:
    mote.resync()
    version = mote.cmd("sys get ver")
    if not version.startswith("RN2483"):
        raise RuntimeError(f"module muet : {version!r}")
    mote.resets.clear()  # la chaîne demandée n'est pas un redémarrage
    for command in (
        "mac set devaddr 01ABCDEF",
        "mac set nwkskey 00112233445566778899AABBCCDDEEFF",
        "mac set appskey FFEEDDCCBBAA99887766554433221100",
        "mac set adr off",
        f"mac set pwridx {args.pwridx}",
        f"mac set rxdelay1 {args.rxdelay1}",
        "mac set rx2 0 869525000",
        "mac set retx 0",
    ):
        mote.expect(command)
    mote.expect("mac join abp")
    accepted = mote.readline(5)
    if accepted != "accepted":
        raise RuntimeError(f"join ABP : {accepted!r}")
    return {
        "event": "setup",
        "version": version,
        "vdd_mv": mote.cmd("sys get vdd"),
        "hweui": mote.cmd("sys get hweui"),
        "rxdelay1": mote.cmd("mac get rxdelay1"),
        "rxdelay2": mote.cmd("mac get rxdelay2"),
        "rx2": mote.cmd("mac get rx2 868"),
        "pwridx": mote.cmd("mac get pwridx"),
        "retx": mote.cmd("mac get retx"),
    }


def payload_hex(rep: int, sf: int, length: int) -> str:
    head = rep.to_bytes(2, "big") + bytes([sf])
    return (head + b"\xaa" * max(0, length - len(head)))[:length].hex().upper()


def attempt(mote: Mote, sf: int, rep: int, args: argparse.Namespace) -> dict:
    mote.expect(f"mac set dr {DR_FOR_SF[sf]}")
    upctr = mote.cmd("mac get upctr")
    sleep_ms = sleep_ms_for(sf, args)
    t_sleep = time.monotonic()
    wake = mote.cmd(f"sys sleep {sleep_ms}", timeout=sleep_ms / 1000 + 5)
    t_wake = time.monotonic()
    mote.resync()
    time.sleep(SETTLE_S)

    mode = "cnf" if args.mode == "cnf" else "uncnf"
    command = f"mac tx {mode} 1 {payload_hex(rep, sf, args.payload)}"
    resets_before = len(mote.resets)
    mote.drain()
    pinctrl(MARKER_GPIO, "op", "dh")
    t_rise = time.monotonic()
    mote.ser.write(f"{command}\r\n".encode())
    immediate = mote.readline(2)
    final = ""
    if immediate == "ok":
        while not final:
            line = mote.readline(ASYNC_TIMEOUT_S)
            if not line:
                final = "timeout"
            elif line in ("mac_tx_ok", "mac_err") or line.startswith("mac_rx"):
                final = line
    t_fall = time.monotonic()
    pinctrl(MARKER_GPIO, "op", "dl")
    return {
        "event": "tx",
        "rep": rep,
        "sf": sf,
        "mode": mode,
        "payload_bytes": args.payload,
        "upctr": upctr,
        "sleep_ms": sleep_ms,
        "sleep_reply": wake,
        "immediate": immediate,
        "final": final,
        "reset_seen": len(mote.resets) > resets_before,
        "t_sleep": t_sleep,
        "t_wake": t_wake,
        "t_rise": t_rise,
        "t_fall": t_fall,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--sf", type=int, nargs="+", default=[7])
    parser.add_argument("--reps", type=int, default=3, help="répétitions réussies par SF")
    parser.add_argument("--mode", choices=["uncnf", "cnf"], default="uncnf")
    parser.add_argument("--payload", type=int, default=6, help="octets de charge utile")
    parser.add_argument("--sleep-ms", type=int, default=4000)
    parser.add_argument("--rxdelay1", type=int, default=1000)
    parser.add_argument("--pwridx", type=int, default=1)
    parser.add_argument("--max-attempts", type=int, default=400)
    args = parser.parse_args()

    pinctrl(MARKER_GPIO, "op", "dl")
    pinctrl(TX_GPIO, "a4", "pn")  # TXD0 : la mote est alimentée par le PPK2
    mote = Mote()
    try:
        emit(setup(mote, args))
        attempts = 0
        for sf in args.sf:
            done = 0
            while done < args.reps:
                attempts += 1
                if attempts > args.max_attempts:
                    raise RuntimeError("trop de tentatives")
                record = attempt(mote, sf, done, args)
                record["attempt"] = attempts
                emit(record)
                if record["immediate"] == "ok" and not record["reset_seen"]:
                    done += 1
        emit({"event": "done", "attempts": attempts, "resets": mote.resets})
    except Exception as exc:  # noqa: BLE001 - rapporté à l'orchestrateur
        emit({"event": "error", "error": f"{type(exc).__name__}: {exc}", "resets": mote.resets})
        sys.exit(1)
    finally:
        pinctrl(MARKER_GPIO, "op", "dl")
        pinctrl(TX_GPIO, "ip", "pn")


if __name__ == "__main__":
    main()
