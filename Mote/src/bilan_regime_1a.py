"""
Bilan du régime 1a : PDR par mote et par SF, et santé de la gateway fixe.

S'exécute sur un poste d'analyse, pas sur les Pi. Le dossier de données
contient :

- les journaux des motes, copiés depuis chaque Pi :
  `scp pi@pi-mote-N:lora-logs/regime_1a_pi-mote-N.csv <dossier>/` ;
- `uplinks.csv` et `gateway_events.csv`, exportés depuis la base
  `lorawan_experiments` (instance AWS, `docker compose exec -T postgres psql
  -U chirpstack -d lorawan_experiments -c "\\copy (...) TO STDOUT CSV HEADER"`) :

      SELECT received_at, dev_eui, f_cnt, spreading_factor, rssi_dbm, snr_db,
             encode(decode(payload_base64, 'base64'), 'hex') AS payload
      FROM uplinks WHERE received_at > '<début>'

      SELECT time, event_type, m_type, dev_eui, rssi_dbm
      FROM gateway_events WHERE time > '<début>'

Méthode : chaque émission du journal d'une mote (`event=tx`, réponse
immédiate `ok`, y compris les `mac_err`) est cherchée dans `uplinks` par sa
charge utile (cycle, DR, marqueur 0x1A), unique par mote. PDR = reçus / émis.
Les émissions dans une fenêtre d'exclusion (`--exclure`) ne comptent pas.

La santé de la gateway est donnée heure par heure : nombre de statistiques
reçues (120 par heure quand elle est connectée) et trames des autres réseaux
LoRa (nombre et RSSI médian), qui servent de référence de sensibilité.
"""

from __future__ import annotations

import argparse
import csv
import statistics
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

PARIS = timezone(timedelta(hours=1))  # CET ; à adapter en heure d'été
SF_RANGE = range(7, 13)
MATCH_WINDOW_S = 2  # écart max entre une trame de la gateway et un uplink des motes


def parse_time(value: str) -> datetime:
    """Heure ISO (journal des motes ou export PostgreSQL), convertie en heure de Paris."""

    parsed = datetime.fromisoformat(value.replace(" ", "T"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=PARIS)
    return parsed.astimezone(PARIS)


def parse_window(value: str) -> tuple[datetime, datetime]:
    start, end = value.split("/")
    return parse_time(start), parse_time(end)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as f:
        # un redémarrage du service réécrit l'en-tête dans le journal
        return [row for row in csv.DictReader(f) if row.get("utc") != "utc"]


def excluded(when: datetime, windows: list[tuple[datetime, datetime]]) -> bool:
    return any(start <= when < end for start, end in windows)


def gateway_health(data_dir: Path, our_euis: set[str], uplinks: list[dict[str, str]]) -> None:
    our_times = [parse_time(u["received_at"]) for u in uplinks if u["dev_eui"] in our_euis]
    stats: Counter[str] = Counter()
    foreign: defaultdict[str, list[int]] = defaultdict(list)

    for event in read_csv(data_dir / "gateway_events.csv"):
        when = parse_time(event["time"])
        hour = when.strftime("%Y-%m-%d %Hh")
        if event["event_type"] == "stats":
            stats[hour] += 1
        elif event["event_type"] == "up" and event["dev_eui"] not in our_euis:
            # les uplinks de données n'ont pas de DevEUI dans gateway_events :
            # on écarte ceux qui coïncident avec un uplink d'une de nos motes
            if event["m_type"] != "JoinRequest" and any(
                abs((when - t).total_seconds()) < MATCH_WINDOW_S for t in our_times
            ):
                continue
            foreign[hour].append(int(event["rssi_dbm"]))

    print("Gateway fixe, heure par heure (heure de Paris)")
    print(f"{'heure':16} {'stats':>5} {'étrangères':>10} {'RSSI médian':>12}")
    for hour in sorted(set(stats) | set(foreign)):
        rssi = foreign[hour]
        median = f"{statistics.median(rssi):.1f}" if rssi else "-"
        print(f"{hour:16} {stats[hour]:5d} {len(rssi):10d} {median:>12}")


def mote_report(
    journal: Path,
    uplinks: list[dict[str, str]],
    start: datetime,
    end: datetime,
    windows: list[tuple[datetime, datetime]],
) -> str:
    rows = read_csv(journal)
    deveui = next(r["deveui"] for r in rows if r.get("deveui")).lower()
    received = {u["payload"].upper(): u for u in uplinks if u["dev_eui"] == deveui}

    joins = [r for r in rows if r["event"] == "join"]
    accepted = [parse_time(r["utc"]).strftime("%d/%m %H:%M") for r in joins if r["async"] == "accepted"]
    print(f"\n=== {journal.stem.removeprefix('regime_1a_')} ({deveui})")
    print(f"joins : {len(joins)} {dict(Counter(r['async'] or r['immediate'] for r in joins))}, acceptés : {accepted}")

    tx = [
        r for r in rows
        if r["event"] == "tx" and r["immediate"] == "ok"
        and start <= parse_time(r["utc"]) < end and not excluded(parse_time(r["utc"]), windows)
    ]
    print(f"réponses : {dict(Counter(r['async'] or '(aucune)' for r in tx))}")
    print(f"{'SF':>4} {'reçus':>6} {'émis':>5} {'PDR':>7} {'SNR médian':>11}")
    for sf in SF_RANGE:
        sent = [r for r in tx if r["sf"] == str(sf)]
        got = [received[r["payload_hex"].upper()] for r in sent if r["payload_hex"].upper() in received]
        pdr = f"{100 * len(got) / len(sent):.1f} %" if sent else "-"
        snr = f"{statistics.median(float(g['snr_db']) for g in got):.2f}" if got else "-"
        print(f"{sf:>4} {len(got):>6} {len(sent):>5} {pdr:>7} {snr:>11}")
    return deveui


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("dossier", type=Path, help="dossier des journaux et des exports")
    parser.add_argument("--debut", type=parse_time, required=True, help="ex. 2026-11-03T17:05 (heure de Paris)")
    parser.add_argument("--fin", type=parse_time, required=True, help="ex. 2026-11-04T08:50 (heure de Paris)")
    parser.add_argument(
        "--exclure", type=parse_window, action="append", default=[],
        help="fenêtre d'exclusion DÉBUT/FIN, répétable (voir docs/emplacements.md)",
    )
    args = parser.parse_args()

    uplinks = read_csv(args.dossier / "uplinks.csv")
    print(f"Période : {args.debut:%Y-%m-%d %H:%M} → {args.fin:%Y-%m-%d %H:%M} (heure de Paris)")
    euis = {
        mote_report(journal, uplinks, args.debut, args.fin, args.exclure)
        for journal in sorted(args.dossier.glob("regime_1a_*.csv"))
    }
    print()
    gateway_health(args.dossier, euis, uplinks)


if __name__ == "__main__":
    main()
