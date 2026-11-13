"""
Chargement des résultats du banc PPK2 dans la base, pour Grafana.

Lit les séries versionnées dans Mote/banc-ppk2/ (un CSV et un JSON par série,
écrits par Mote/src/banc_ppk2.py) et remplace d'un bloc le contenu des tables
ppk2_series et ppk2_messages (migration 006). Les fichiers du dépôt font foi :
la base n'en est qu'une copie, et les échantillons bruts n'y vont pas.

Sur le serveur, après un `git pull` (voir ../README.md) :

    docker compose --profile jobs run --rm banc-ppk2-chargement

Sans base, pour contrôler la lecture des fichiers :

    python3 LoRaWAN-Infra/banc-ppk2/chargement.py --verifier
"""

from __future__ import annotations

import csv
import json
import os
import re
import sys
from pathlib import Path

REPO = Path(os.getenv("BANC_PPK2_REPO", Path(__file__).resolve().parents[2]))
RESULTS = REPO / "Mote" / "banc-ppk2"

SERIES_COLUMNS = (
    "name", "started_at", "hweui", "firmware", "mode", "payload_bytes", "reps",
    "rx1_delay_ms", "rx2_sf", "sleep_ms", "source_mv", "no_duty_cycle", "warmup",
    "label", "in_results", "acquisition_git",
)
MESSAGE_COLUMNS = (
    "series", "attempt", "rep", "sf", "mode", "payload_bytes", "upctr", "immediate",
    "final", "reset_seen", "warmup", "i_sleep_ma", "i_idle_ma", "tx_start_ms",
    "duration_ms", "charge_mc", "tx_ms", "energy_mj", "rx_windows_ms", "rx1_ms",
    "rx2_ms", "gap_samples_error", "marker_samples_error", "valid",
)
NAME = re.compile(r"^(\d{4}-\d{2}-\d{2})_(\d{2})(\d{2})_")


def number(value: str | None, kind: type = float):
    return kind(value) if value not in ("", None) else None


def boolean(value: str | None) -> bool | None:
    return {"True": True, "False": False}.get(value or "")


def read_series(meta_path: Path) -> tuple[dict, list[dict]]:
    """Une série : sa ligne de ppk2_series et ses lignes de ppk2_messages."""

    meta = json.loads(meta_path.read_text())
    name, args, setup = meta["name"], meta["args"], meta.get("setup") or {}
    match = NAME.match(name)
    if not match:
        raise ValueError(f"{name} : nom de série sans date")
    day, hour, minute = match.groups()
    # RX2 : débit lu sur le module au lancement (« DR fréquence »), sinon
    # l'argument, sinon le défaut du module (DR0). EU868 : SF = 12 − DR.
    rx2_dr = int(setup["rx2"].split()[0]) if setup.get("rx2") else int(args.get("rx2_dr", 0))
    label = args.get("label", "")
    no_duty_cycle = bool(args.get("no_duty_cycle", False))
    series = {
        "name": name,
        # Heure locale du banc (Europe/Paris), convertie par la base
        "started_at": f"{day} {hour}:{minute}",
        "hweui": setup.get("hweui"),
        "firmware": setup.get("version"),
        "mode": args["mode"],
        "payload_bytes": int(args["payload"]),
        "reps": int(args["reps"]),
        "rx1_delay_ms": int(args["rxdelay1"]),
        "rx2_sf": 12 - rx2_dr,
        "sleep_ms": number(args.get("sleep_ms"), int),
        "source_mv": int(args["mv"]),
        "no_duty_cycle": no_duty_cycle,
        "warmup": int(args.get("warmup", 0)),
        "label": label,
        # Contrôles de méthode, hors résultats (voir Mote/banc-ppk2/README.md)
        "in_results": not no_duty_cycle and "validation" not in label,
        "acquisition_git": (meta.get("acquisition") or {}).get("git"),
    }

    messages = []
    with meta_path.with_suffix(".csv").open(newline="") as f:
        for r in csv.DictReader(f):
            windows = [float(w) for w in r["rx_windows_ms"].split()]
            rx1, rx2 = windows if len(windows) == 2 else (None, None)
            messages.append({
                "series": name,
                "attempt": int(r["attempt"]),
                "rep": int(r["rep"]),
                "sf": int(r["sf"]),
                "mode": r["mode"],
                "payload_bytes": int(r["payload_bytes"]),
                "upctr": number(r.get("upctr"), int),
                "immediate": r["immediate"] or None,
                "final": r["final"] or None,
                "reset_seen": boolean(r["reset_seen"]),
                "warmup": boolean(r.get("warmup")) or False,
                "i_sleep_ma": number(r["i_sleep_ma"]),
                "i_idle_ma": number(r["i_idle_ma"]),
                "tx_start_ms": number(r["tx_start_ms"]),
                "duration_ms": number(r["duration_ms"]),
                "charge_mc": number(r["charge_mc"]),
                "tx_ms": number(r["tx_ms"]),
                "energy_mj": number(r["energy_mj"]),
                "rx_windows_ms": r["rx_windows_ms"] or None,
                "rx1_ms": rx1,
                "rx2_ms": rx2,
                "gap_samples_error": number(r["gap_samples_error"], int),
                "marker_samples_error": number(r.get("marker_samples_error"), int),
                "valid": boolean(r["valid"]),
            })
    return series, messages


def read_all() -> tuple[list[dict], list[dict]]:
    all_series, all_messages = [], []
    for meta_path in sorted(RESULTS.glob("*.json")):
        # Une série a un CSV de même nom ; *.recorder.json n'en a pas
        if not meta_path.with_suffix(".csv").exists():
            continue
        series, messages = read_series(meta_path)
        all_series.append(series)
        all_messages += messages
    return all_series, all_messages


def insert(table: str, columns: tuple[str, ...]) -> str:
    values = ["%s::timestamp at time zone 'Europe/Paris'" if c == "started_at" else "%s" for c in columns]
    return f"insert into {table} ({', '.join(columns)}) values ({', '.join(values)})"


def main() -> None:
    all_series, all_messages = read_all()
    if not all_series:
        sys.exit(f"aucune série dans {RESULTS}")
    kept = sum(1 for s in all_series if s["in_results"])
    summary = (
        f"{len(all_series)} séries ({kept} dans les résultats), {len(all_messages)} messages, "
        f"{sum(1 for m in all_messages if m['valid'])} retenus"
    )
    if "--verifier" in sys.argv[1:]:
        for s in all_series:
            n = sum(1 for m in all_messages if m["series"] == s["name"])
            print(f"{s['name']} : {n} messages, RX2 SF{s['rx2_sf']}, "
                  f"{'résultats' if s['in_results'] else 'hors résultats'}")
        print(summary)
        return

    import psycopg

    with psycopg.connect(os.environ["POSTGRES_DSN"]) as conn, conn.cursor() as cur:
        # Remplacement d'un bloc, dans une transaction : la base reflète le dépôt
        cur.execute("delete from ppk2_messages")
        cur.execute("delete from ppk2_series")
        cur.executemany(
            insert("ppk2_series", SERIES_COLUMNS),
            [tuple(s[c] for c in SERIES_COLUMNS) for s in all_series],
        )
        cur.executemany(
            insert("ppk2_messages", MESSAGE_COLUMNS),
            [tuple(m[c] for c in MESSAGE_COLUMNS) for m in all_messages],
        )
    print(f"chargé : {summary}")


if __name__ == "__main__":
    main()
