"""
Traitement du régime 1a sur le serveur : journaux des motes → tables de suivi.

Lancé après chaque collecte (regime1a-collecte.service, toutes les 10 min),
dans le conteneur `regime1a-traitement` de la pile (voir ../README.md). Il :

1. charge les journaux copiés dans /srv/regime1a/journaux/<pi>/ :
   émissions dans regime_1a_tx, autres lignes dans regime_1a_events (les
   lignes déjà chargées sont ignorées) ;
2. charge l'état des collectes dans regime_1a_collection ;
3. recalcule, depuis REGIME1A_DEBUT jusqu'à maintenant, les fenêtres
   d'exclusion (regime_1a_exclusions) et les comptes horaires par mote et par
   SF (regime_1a_hourly), avec le code de Mote/src/bilan_regime_1a.py : mêmes
   règles et mêmes chiffres que le bilan en ligne de commande.

Le journal du netwatch n'est pas accessible depuis le serveur : E1 n'est pas
élargie à l'alerte « down », et E2 vient des connexions de la gateway au
serveur. Le bilan en ligne de commande avec netwatch.log peut donc exclure
quelques secondes de plus.
"""

from __future__ import annotations

import csv
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import psycopg

REPO = Path(os.getenv("REGIME1A_REPO", "/repo"))
sys.path.insert(0, str(REPO / "Mote" / "src"))

import bilan_regime_1a as bilan  # noqa: E402

DSN = os.environ["POSTGRES_DSN"]
BASE = Path(os.getenv("REGIME1A_BASE", "/srv/regime1a"))
START = bilan.parse_time(os.getenv("REGIME1A_DEBUT", "2026-11-06T11:53:00+01:00"))

TX_COLUMNS = (
    "host", "dev_eui", "utc", "utc_tx_start", "cycle", "slot", "dr", "sf", "upctr",
    "payload_hex", "attempts", "immediate", "async_response", "airtime_ms",
)


def blank_to_none(value: str | None) -> str | None:
    return value if value not in ("", None) else None


def journals() -> dict[str, list[dict[str, str]]]:
    """Journal de chaque Pi (fichier regime_1a_<pi>.csv à la racine de son dossier)."""

    found = {}
    for path in sorted((BASE / "journaux").glob("*/regime_1a_*.csv")):
        rows = bilan.read_csv(path)
        if any(r.get("deveui") for r in rows):
            found[path.parent.name] = rows
    return found


def load_journals(cur: psycopg.Cursor, by_host: dict[str, list[dict[str, str]]]) -> tuple[int, int]:
    tx, events = [], []
    for host, rows in by_host.items():
        deveui = bilan.journal_deveui(rows)
        for line_no, r in enumerate(rows, start=1):
            if r["event"] == "tx":
                tx.append((
                    host, deveui, r["utc"], blank_to_none(r.get("utc_tx_start")), int(r["cycle"]),
                    blank_to_none(r["slot"]), int(r["dr"]), int(r["sf"]), blank_to_none(r["upctr"]),
                    r["payload_hex"].upper(), blank_to_none(r["attempts"]), r["immediate"],
                    r["async"], blank_to_none(r.get("airtime_ms")),
                ))
            else:
                events.append((
                    host, line_no, (r.get("deveui") or deveui).lower(), r["utc"], r["event"],
                    blank_to_none(r.get("cycle")), blank_to_none(r.get("dr")), blank_to_none(r.get("sf")),
                    blank_to_none(r.get("immediate")), blank_to_none(r.get("async")),
                    blank_to_none(r.get("detail")),
                ))
    cur.executemany(
        f"insert into regime_1a_tx ({', '.join(TX_COLUMNS)}) values ({', '.join(['%s'] * len(TX_COLUMNS))}) "
        "on conflict (dev_eui, payload_hex) do nothing",
        tx,
    )
    n_tx = cur.rowcount
    cur.executemany(
        "insert into regime_1a_events (host, line_no, dev_eui, utc, event, cycle, dr, sf, immediate, "
        "async_response, detail) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) "
        "on conflict (host, line_no) do nothing",
        events,
    )
    return n_tx, cur.rowcount


def load_collection(cur: psycopg.Cursor) -> None:
    path = BASE / "etat-collecte.csv"
    if not path.exists():
        return
    with path.open(newline="") as f:
        rows = [
            (r["utc"], r["host"], r["ip"], r["statut"], int(r["code_rsync"]), int(r["octets"]))
            for r in csv.DictReader(f)
        ]
    cur.executemany(
        "insert into regime_1a_collection (utc, host, ip, status, rsync_code, bytes) "
        "values (%s, %s, %s, %s, %s, %s) on conflict (utc, host) do nothing",
        rows,
    )


def fetch(cur: psycopg.Cursor, query: str, params: tuple, keys: tuple[str, ...]) -> list[dict[str, str]]:
    """Lignes de la base au format des exports CSV (heures en ISO, valeurs en texte)."""

    cur.execute(query, params)
    out = []
    for row in cur.fetchall():
        out.append({
            k: (v.isoformat() if isinstance(v, datetime) else "" if v is None else str(v))
            for k, v in zip(keys, row)
        })
    return out


def main() -> None:
    now = datetime.now(timezone.utc)
    end = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    by_host = journals()
    euis = {bilan.journal_deveui(rows) for rows in by_host.values()}

    with psycopg.connect(DSN) as conn, conn.cursor() as cur:
        n_tx, n_events = load_journals(cur, by_host)
        load_collection(cur)

        since = START - timedelta(hours=1)
        uplinks = fetch(
            cur,
            "select received_at, dev_eui, encode(decode(payload_base64, 'base64'), 'hex') "
            "from uplinks where received_at >= %s and dev_eui = any(%s)",
            (since, sorted(euis)), ("received_at", "dev_eui", "payload"),
        )
        events = fetch(
            cur,
            "select time, event_type, m_type, dev_eui, rssi_dbm from gateway_events "
            "where time >= %s and event_type in ('stats', 'conn', 'up')",
            (since,), ("time", "event_type", "m_type", "dev_eui", "rssi_dbm"),
        )
        gw = bilan.GatewayData(events, euis, uplinks)
        moves = bilan.read_moves(REPO / "docs" / "deplacements-gateway.csv")
        windows = bilan.detect_windows(gw, [], [], START, end, moves)
        windows += [w for w in bilan.read_e4(REPO / "docs" / "exclusions-e4.csv") if w[1] > START and w[0] < end]
        windows.sort()

        received: dict[str, set[str]] = {}
        for u in uplinks:
            received.setdefault(u["dev_eui"], set()).add(u["payload"].upper())
        hourly = []
        for host, rows in by_host.items():
            deveui = bilan.journal_deveui(rows)
            counts = bilan.hourly_counts(rows, received.get(deveui, set()), START, end, windows)
            hourly += [(hour, deveui, host, sf, *c) for (hour, sf), c in counts.items()]

        # Recalcul complet de la période : fenêtres et comptes remplacés d'un bloc
        cur.execute("delete from regime_1a_exclusions")
        cur.executemany(
            "insert into regime_1a_exclusions (rule, start_at, end_at) values (%s, %s, %s)",
            [(rule, a, b) for a, b, rule in windows],
        )
        cur.execute("delete from regime_1a_hourly")
        cur.executemany(
            "insert into regime_1a_hourly (hour, dev_eui, host, sf, sent, received, excluded, "
            "sent_without_e3, received_without_e3) values (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
            hourly,
        )

    print(
        f"{now:%Y-%m-%dT%H:%M:%SZ} : {len(by_host)} journaux, {n_tx} émissions et {n_events} "
        f"événements nouveaux, {len(windows)} fenêtres d'exclusion, {len(hourly)} lignes horaires "
        f"({START:%Y-%m-%d %H:%M} → {end:%Y-%m-%d %H:%M} UTC)"
    )


if __name__ == "__main__":
    main()
