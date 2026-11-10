"""
Banc PPK2 : orchestration d'une série de mesures et calcul de l'énergie par message.

Voir Mote/banc-ppk2.md. À lancer depuis WSL, dans le dossier Mote/ :

    uv run python src/banc_ppk2.py --sf 7 --reps 3 --mode uncnf --payload 6

1. `ppk2_record.py` est copié dans `C:\\Users\\<user>\\banc-ppk2\\` et lancé en
   Python natif Windows : il alimente la mote (source de tension) et
   enregistre le courant et les voies logiques.
2. `banc_pi.py` est envoyé au Pi par SSH (entrée standard, donc toujours la
   version de ce dépôt) : il enchaîne sommeil, réveil, repère haut sur D0,
   `mac tx`, réponse, repère bas.
3. L'enregistrement est arrêté, puis chaque message est découpé grâce aux
   repères de D0.

Contrôle d'intégrité : entre deux repères hauts successifs, le nombre
d'échantillons doit valoir 100 000 par seconde de l'horloge du Pi, à
`TOLERANCE_SAMPLES` près (latence de `pinctrl`). Une tentative qui échoue à ce
contrôle, qui n'a pas émis (`no_free_ch`) ou pendant laquelle le module a
redémarré est conservée dans le CSV mais exclue du résumé.

Énergie d'un message : du premier échantillon au-dessus de `TX_THRESHOLD_UA`
(début de l'émission) au dernier au-dessus de `ACTIVE_THRESHOLD_UA` (fin de
RX2), E = (∫ I dt − I_fond × durée) × V, avec I_fond le courant moyen de la
carte pendant le sommeil du module qui précède (sans sa première seconde ni
ses 0,5 dernière seconde) et V la tension de la source.

Sorties dans `C:\\Users\\<user>\\banc-ppk2\\data\\` : échantillons bruts
(`.cur.f32`, `.dig.u8`), un CSV par tentative et un JSON de métadonnées
(arguments, commit du dépôt, empreintes des scripts, réglages relus sur le
module, résumé de l'enregistreur).
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import statistics
import subprocess
import sys
import time
from array import array
from datetime import datetime
from pathlib import Path

RATE = 100_000
TX_THRESHOLD_UA = 30_000
ACTIVE_THRESHOLD_UA = 8_000
RX_MIN_SAMPLES = 200  # 2 ms
RX_MERGE_GAP = 50  # 0,5 ms
TOLERANCE_SAMPLES = 500  # 5 ms
PI_HOST = "pi@pi-ppk2"
MOTE_ID = "7330"

SRC = Path(__file__).resolve().parent
WIN_USER_DIR = Path("/mnt/c/Users/yanis/banc-ppk2")
WIN_USER_DIR_WIN = r"C:\Users\yanis\banc-ppk2"
UV_WINDOWS = (
    "uv run --no-project --python 3.14 --with ppk2-api==0.9.2 --with pyserial==3.5 python"
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def git_state() -> str:
    head = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"], cwd=SRC, capture_output=True, text=True
    ).stdout.strip()
    dirty = subprocess.run(
        ["git", "status", "--porcelain", "--", "."], cwd=SRC, capture_output=True, text=True
    ).stdout.strip()
    return f"{head}{'+modifié' if dirty else ''}"


# --- Lecture des fichiers bruts -----------------------------------------------


def find_edges(dig_path: Path, chunk: int = 1 << 24) -> tuple[list[int], list[int]]:
    """Indices des fronts montants et descendants de D0."""

    table = bytes(b & 1 for b in range(256))
    rises: list[int] = []
    falls: list[int] = []
    previous = b"\x00"
    offset = 0
    with open(dig_path, "rb") as f:
        while block := f.read(chunk):
            bits = previous + block.translate(table)
            for pattern, out in ((b"\x00\x01", rises), (b"\x01\x00", falls)):
                i = bits.find(pattern)
                while i != -1:
                    out.append(offset + i)  # index de l'échantillon après le front
                    i = bits.find(pattern, i + 1)
            previous = bits[-1:]
            offset += len(block)
    return rises, falls


def read_current(cur_path: Path, start: int, stop: int) -> array:
    data = array("f")
    stop = min(stop, cur_path.stat().st_size // 4)
    with open(cur_path, "rb") as f:
        f.seek(start * 4)
        data.fromfile(f, max(0, stop - start))
    return data


def mean_ma(cur_path: Path, start: int, stop: int) -> float:
    window = read_current(cur_path, start, stop)
    return sum(window) / len(window) / 1000 if window else float("nan")


# --- Analyse d'une tentative --------------------------------------------------


def runs(values: array, low: float, high: float) -> list[tuple[int, int]]:
    """Plages contiguës où low < v <= high, fusionnées si l'écart est court."""

    out: list[list[int]] = []
    start = None
    for i, v in enumerate(values):
        inside = low < v <= high
        if inside and start is None:
            start = i
        elif not inside and start is not None:
            if out and start - out[-1][1] <= RX_MERGE_GAP:
                out[-1][1] = i
            else:
                out.append([start, i])
            start = None
    if start is not None:
        out.append([start, len(values)])
    return [(a, b) for a, b in out if b - a >= RX_MIN_SAMPLES]


def analyse(record: dict, rise: int, fall: int, cur_path: Path, mv: int) -> dict:
    row = {k: record[k] for k in (
        "attempt", "rep", "sf", "mode", "payload_bytes", "upctr", "immediate", "final",
        "reset_seen")}
    row.update(rise=rise, fall=fall)
    marker_s = record["t_fall"] - record["t_rise"]
    row["marker_ms"] = round(marker_s * 1000, 2)
    row["marker_samples_error"] = (fall - rise) - round(marker_s * RATE)

    def at(t: float) -> int:
        return rise + round((t - record["t_rise"]) * RATE)

    row["i_sleep_ma"] = round(mean_ma(cur_path, at(record["t_sleep"] + 1.0),
                                      at(record["t_wake"] - 0.5)), 4)
    row["i_idle_ma"] = round(mean_ma(cur_path, at(record["t_wake"] + 0.15),
                                     rise - RATE // 100), 4)
    if record["immediate"] != "ok":
        return row

    window = read_current(cur_path, rise, fall + RATE // 20)
    start = next((i for i, v in enumerate(window) if v > TX_THRESHOLD_UA), None)
    if start is None:
        row["note"] = "aucune émission vue"
        return row
    end = max(i for i in range(start, len(window)) if window[i] > ACTIVE_THRESHOLD_UA) + 1
    event = window[start:end]
    seconds = len(event) / RATE
    charge_mc = sum(event) / RATE / 1000
    row.update(
        tx_start_ms=round(start / RATE * 1000, 2),
        duration_ms=round(seconds * 1000, 2),
        charge_mc=round(charge_mc, 4),
        tx_ms=round(sum(1 for v in event if v > TX_THRESHOLD_UA) / RATE * 1000, 2),
        energy_mj=round((charge_mc - row["i_sleep_ma"] * seconds) * mv / 1000, 3),
    )
    rx = runs(event, ACTIVE_THRESHOLD_UA, TX_THRESHOLD_UA)
    row["rx_windows_ms"] = " ".join(f"{(b - a) / RATE * 1000:.1f}" for a, b in rx)
    return row


# --- Orchestration -------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--sf", type=int, nargs="+", default=[7])
    parser.add_argument("--reps", type=int, default=3)
    parser.add_argument("--mode", choices=["uncnf", "cnf"], default="uncnf")
    parser.add_argument("--payload", type=int, default=6)
    parser.add_argument("--sleep-ms", type=int, default=4000)
    parser.add_argument("--rxdelay1", type=int, default=1000)
    parser.add_argument("--mv", type=int, default=3300)
    parser.add_argument("--label", default="")
    args = parser.parse_args()

    sfs = "-".join(f"sf{sf}" for sf in args.sf)
    name = (f"{datetime.now():%Y-%m-%d_%H%M}_{MOTE_ID}_smu{args.mv}_"
            f"abp-{args.mode}-{sfs}-{args.payload}o-x{args.reps}{args.label}")
    data_dir = WIN_USER_DIR / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(SRC / "ppk2_record.py", WIN_USER_DIR / "ppk2_record.py")

    recorder = subprocess.Popen(
        ["powershell.exe", "-NoProfile", "-Command",
         f"cd '{WIN_USER_DIR_WIN}'; {UV_WINDOWS} -u ppk2_record.py "
         f"'{WIN_USER_DIR_WIN}\\data' '{name}' --mv {args.mv}"],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True,
    )
    for line in recorder.stdout:
        if line.strip() == "READY":
            break
    else:
        sys.exit("l'enregistreur n'a pas démarré")
    print(f"PPK2 : mote alimentée à {args.mv} mV, enregistrement {name}", flush=True)

    pi_args = (f"--sf {' '.join(map(str, args.sf))} --reps {args.reps} --mode {args.mode} "
               f"--payload {args.payload} --sleep-ms {args.sleep_ms} "
               f"--rxdelay1 {args.rxdelay1}")
    records: list[dict] = []
    with open(SRC / "banc_pi.py", "rb") as script:
        pi = subprocess.Popen(
            ["ssh", "-o", "BatchMode=yes", PI_HOST,
             f"cd ~/DMX-LoRa-Exp-1/Mote && ~/.local/bin/uv run python - {pi_args}"],
            stdin=script, stdout=subprocess.PIPE, text=True,
        )
        for line in pi.stdout:
            record = json.loads(line)
            records.append(record)
            if record["event"] == "tx":
                print(f"  tentative {record['attempt']:3d}  SF{record['sf']}  "
                      f"{record['immediate']:>11s}  {record['final']}"
                      f"{'  REDÉMARRAGE' if record['reset_seen'] else ''}", flush=True)
            else:
                print(f"  {record}", flush=True)
        pi.wait()

    time.sleep(1.0)  # un peu de repos enregistré après la dernière tentative
    recorder.stdin.write("stop\n")
    recorder.stdin.flush()
    summary = json.loads(recorder.stdout.read().strip().splitlines()[-1])
    recorder.wait()

    cur_path = data_dir / f"{name}.cur.f32"
    dig_path = data_dir / f"{name}.dig.u8"
    rises, falls = find_edges(dig_path)
    tx = [r for r in records if r["event"] == "tx"]
    print(f"{summary['samples']} échantillons ({summary['samples'] / summary['host_seconds']:,.0f}"
          f" éch./s d'horloge) ; {len(rises)} repères pour {len(tx)} tentatives", flush=True)
    if len(rises) != len(tx) or len(falls) != len(tx):
        sys.exit(f"repères incohérents : {len(rises)} montants, {len(falls)} descendants")

    rows = []
    for k, (record, rise, fall) in enumerate(zip(tx, rises, falls)):
        row = analyse(record, rise, fall, cur_path, args.mv)
        if k:
            expected = round((record["t_rise"] - tx[k - 1]["t_rise"]) * RATE)
            row["gap_samples_error"] = (rise - rises[k - 1]) - expected
        else:
            row["gap_samples_error"] = 0
        row["valid"] = (
            record["immediate"] == "ok"
            and not record["reset_seen"]
            and "energy_mj" in row
            and abs(row["gap_samples_error"]) <= TOLERANCE_SAMPLES
            and abs(row["marker_samples_error"]) <= TOLERANCE_SAMPLES
        )
        rows.append(row)

    fields = list(dict.fromkeys(k for row in rows for k in row))
    with open(data_dir / f"{name}.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    meta = {
        "name": name,
        "args": vars(args),
        "git": git_state(),
        "sha256": {p: sha256(SRC / p) for p in ("banc_pi.py", "ppk2_record.py", "banc_ppk2.py")},
        "setup": next((r for r in records if r["event"] == "setup"), None),
        "end": records[-1] if records else None,
        "recorder": summary,
        "thresholds_ua": {"tx": TX_THRESHOLD_UA, "active": ACTIVE_THRESHOLD_UA},
        "tolerance_samples": TOLERANCE_SAMPLES,
    }
    (data_dir / f"{name}.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False))

    print(f"\n{'SF':>3} {'n':>3} {'E moy. (mJ)':>12} {'écart-type':>10} {'min':>7} {'max':>7}"
          f" {'durée (ms)':>10} {'I fond (mA)':>11}")
    for sf in args.sf:
        ok = [r for r in rows if r["sf"] == sf and r["valid"]]
        if not ok:
            print(f"{sf:>3}   0")
            continue
        e = [r["energy_mj"] for r in ok]
        print(f"{sf:>3} {len(e):>3} {statistics.fmean(e):>12.2f} "
              f"{statistics.stdev(e) if len(e) > 1 else 0:>10.2f} {min(e):>7.2f} {max(e):>7.2f} "
              f"{statistics.fmean(r['duration_ms'] for r in ok):>10.1f} "
              f"{statistics.fmean(r['i_sleep_ma'] for r in ok):>11.3f}")
    rejected = [r for r in rows if not r["valid"]]
    print(f"{len(rejected)} tentative(s) écartée(s) ; fichiers : {WIN_USER_DIR_WIN}\\data\\{name}.*")


if __name__ == "__main__":
    main()
