"""
Banc PPK2, côté PC Windows : alimente la mote et enregistre le courant.

Voir Mote/banc-ppk2.md. Lancé par `banc_ppk2.py` (WSL) en Python natif
Windows : le Raspberry Pi perd environ 16 % des échantillons du PPK2, Windows
aucun (contrôle par repères du 9 novembre 2026).

    uv run --no-project --python 3.14 --with ppk2-api==0.9.2 --with pyserial==3.5 \
        python ppk2_record.py <dossier> <nom> [--mv 3300]

Le PPK2 est mis en source de tension (`--mv`), sa sortie est activée, puis
l'enregistrement démarre (100 kS/s). Une ligne `READY` est écrite quand la mote
est alimentée et que le flux arrive. L'enregistrement s'arrête à la réception
d'une ligne `stop` (ou de la fin) sur l'entrée standard ; la sortie du PPK2 se
coupe ensuite d'elle-même à la fermeture du port.

Une lecture continue empile les octets bruts ; un second fil les décode dans
l'ordre (le décodeur de ppk2-api garde un reste entre deux blocs) et les écrit
sur disque au fil de l'eau :
- `<nom>.cur.f32` : courant en µA, float32 petit-boutiste, un par échantillon ;
- `<nom>.dig.u8` : octet des voies logiques D0-D7, un par échantillon.
Un résumé JSON est écrit sur la sortie standard à la fin.
"""

from __future__ import annotations

import argparse
import json
import queue
import sys
import threading
import time
from array import array
from pathlib import Path

from ppk2_api.ppk2_api import PPK2_API
from serial.tools import list_ports

NORDIC_VID = 0x1915


def drain(ppk2: PPK2_API) -> None:
    """Arrête un flux resté actif et vide le port jusqu'au silence."""

    ppk2.stop_measuring()
    quiet = start = time.monotonic()
    while time.monotonic() - quiet < 0.5 and time.monotonic() - start < 10:
        if ppk2.ser.read(ppk2.ser.in_waiting or 1):
            quiet = time.monotonic()


def open_ppk2() -> tuple[PPK2_API, str, dict]:
    """Ouvre le port de commande du PPK2 (celui qui renvoie les métadonnées)."""

    for port in sorted(p.device for p in list_ports.comports() if p.vid == NORDIC_VID):
        try:
            ppk2 = PPK2_API(port, timeout=1, write_timeout=1)
            drain(ppk2)
            if ppk2.get_modifiers():
                return ppk2, port, ppk2.modifiers
            ppk2.ser.close()
        except Exception as exc:  # noqa: BLE001 - port suivant
            print(f"{port}: {type(exc).__name__}: {exc}", file=sys.stderr)
    raise SystemExit("PPK2 introuvable")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("directory", type=Path)
    parser.add_argument("name")
    parser.add_argument("--mv", type=int, default=3300)
    args = parser.parse_args()
    args.directory.mkdir(parents=True, exist_ok=True)
    cur_path = args.directory / f"{args.name}.cur.f32"
    dig_path = args.directory / f"{args.name}.dig.u8"

    ppk2, port, modifiers = open_ppk2()
    ppk2.use_source_meter()
    ppk2.set_source_voltage(args.mv)
    ppk2.toggle_DUT_power("ON")

    raw: queue.Queue[bytes | None] = queue.Queue()
    stop = threading.Event()
    counts = {"bytes": 0, "samples": 0}

    def reader() -> None:
        ppk2.ser.timeout = 0.005
        while not stop.is_set():
            data = ppk2.ser.read(65536)
            if data:
                counts["bytes"] += len(data)
                raw.put(data)
        raw.put(None)

    def decoder() -> None:
        with open(cur_path, "wb") as cur, open(dig_path, "wb") as dig:
            while (data := raw.get()) is not None:
                samples, bits = ppk2.get_samples(data)
                array("f", samples).tofile(cur)
                dig.write(bytes(b & 0xFF for b in bits))
                counts["samples"] += len(samples)

    ppk2.start_measuring()
    t_start = time.monotonic()
    threads = [threading.Thread(target=reader), threading.Thread(target=decoder)]
    for th in threads:
        th.start()
    time.sleep(1.0)
    print("READY", flush=True)

    for line in sys.stdin:
        if line.strip() == "stop":
            break
    t_stop = time.monotonic()
    stop.set()
    threads[0].join()
    ppk2.stop_measuring()
    threads[1].join()

    print(json.dumps({
        "port": port,
        "mv": args.mv,
        "calibrated": modifiers.get("Calibrated"),
        "hw": modifiers.get("HW"),
        "bytes": counts["bytes"],
        "samples": counts["samples"],
        "host_seconds": t_stop - t_start,
        "cur": str(cur_path),
        "dig": str(dig_path),
    }), flush=True)


if __name__ == "__main__":
    main()
