"""
Bilan du régime 1a : PDR par mote et par SF, et santé de la gateway fixe.

S'exécute sur un poste d'analyse, pas sur les Pi. Le dossier de données
contient :

- les journaux des motes, copiés depuis chaque Pi :
  `scp pi@pi-mote-N:lora-logs/regime_1a_pi-mote-N.csv <dossier>/` ;
- `uplinks.csv` et `gateway_events.csv`, exportés depuis la base
  `lorawan_experiments` (instance AWS, `docker compose exec -T postgres psql
  -U grafana_reader -d lorawan_experiments -c "\\copy (...) TO STDOUT CSV HEADER"`) :

      SELECT received_at, dev_eui, f_cnt, spreading_factor, rssi_dbm, snr_db,
             encode(decode(payload_base64, 'base64'), 'hex') AS payload
      FROM uplinks WHERE received_at > '<début>'

      SELECT time, event_type, m_type, dev_eui, rssi_dbm
      FROM gateway_events WHERE time > '<début>'

- facultatif, `netwatch.log` : le journal du netwatch de la gateway (heures
  de Paris), `ssh wap-gateway '/log print where message~"netwatch backhaul"'
  > <dossier>/netwatch.log`. Le journal de la gateway ne garde que les
  derniers jours : l'exporter à chaque bilan.

Méthode : chaque émission du journal d'une mote (`event=tx`, réponse
immédiate `ok`, y compris les `mac_err`) est cherchée dans `uplinks` par sa
charge utile (cycle, DR, marqueur 0x1A), unique par mote. PDR = reçus / émis.

Exclusions (docs/plan-experimental.md, section 10, règle du 10 novembre
2026) : une émission est exclue si son `utc_tx_start` tombe dans une fenêtre
E1 (gateway sans statistiques plus de 75 s), E2 (relance de la LoRa, plus
30 s), E3 (heure de réception dégradée, d'après les trames des autres réseaux
LoRa) ou E4 (intervention documentée, donnée par `--exclure`). E1 à E3 sont
détectées automatiquement ; le PDR est donné avec et sans E3. La référence
d'E3 est calculée séparément pour chaque position de la gateway
(`--deplacement-gateway`).

La santé de la gateway est donnée heure par heure : nombre de statistiques
reçues (120 par heure quand elle est connectée) et trames des autres réseaux
LoRa (nombre et RSSI médian), qui servent de référence de sensibilité.
"""

from __future__ import annotations

import argparse
import bisect
import csv
import re
import statistics
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

PARIS = timezone(timedelta(hours=1))  # CET ; à adapter en heure d'été
SF_RANGE = range(7, 13)
MATCH_WINDOW_S = 2  # écart max entre une trame de la gateway et un uplink des motes

# Règle d'exclusion (plan, section 10)
STATS_GAP = timedelta(seconds=75)          # E1 : statistiques toutes les 30 s
NETWATCH_LEAD = timedelta(seconds=10)      # E1 : alerte « down » moins 10 s
NETWATCH_SEARCH = timedelta(minutes=2)     # E1 : alerte rattachée à un écart proche
RESTART_TAIL = timedelta(seconds=30)       # E2 : 26 s mesurées pour une relance
CONN_CLUSTER = timedelta(seconds=60)       # E2 : événements de connexion d'une même relance
E3_RSSI_DROP_DB = 10.0
E3_COUNT_RATIO = 1 / 3

Window = tuple[datetime, datetime, str]    # début, fin, motif


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


def excluded(when: datetime, windows: list[Window]) -> str | None:
    """Motif de la première fenêtre qui contient `when`, sinon None."""

    for start, end, rule in windows:
        if start <= when < end:
            return rule
    return None


def tx_time(row: dict[str, str]) -> datetime:
    """Heure d'émission : `utc_tx_start` (début de `mac tx`), sinon `utc`."""

    return parse_time(row.get("utc_tx_start") or row["utc"])


def read_netwatch(path: Path) -> tuple[list[datetime], list[datetime]]:
    """Alertes « down » et relances de la LoRa du journal du netwatch."""

    downs, restarts = [], []
    if not path.exists():
        return downs, restarts
    stamp = re.compile(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})")
    for line in path.read_text(errors="replace").splitlines():
        found = stamp.search(line)
        if not found:
            continue
        when = parse_time(found.group(1))
        if "netwatch backhaul down" in line:
            downs.append(when)
        elif "restarting LoRa" in line:
            restarts.append(when)
    return downs, restarts


class GatewayData:
    """Statistiques, connexions et trames étrangères de `gateway_events.csv`."""

    def __init__(self, data_dir: Path, our_euis: set[str], uplinks: list[dict[str, str]]) -> None:
        our_times = sorted(parse_time(u["received_at"]) for u in uplinks if u["dev_eui"] in our_euis)
        self.stats: list[datetime] = []
        self.conn: list[datetime] = []
        self.foreign: list[tuple[datetime, int]] = []
        for event in read_csv(data_dir / "gateway_events.csv"):
            when = parse_time(event["time"])
            if event["event_type"] == "stats":
                self.stats.append(when)
            elif event["event_type"] == "conn":
                self.conn.append(when)
            elif event["event_type"] == "up" and event["dev_eui"] not in our_euis:
                # les uplinks de données n'ont pas de DevEUI dans gateway_events :
                # on écarte ceux qui coïncident avec un uplink d'une de nos motes
                if event["m_type"] != "JoinRequest" and near(our_times, when):
                    continue
                self.foreign.append((when, int(event["rssi_dbm"])))
        self.stats.sort()
        self.conn.sort()
        self.foreign.sort()


def near(sorted_times: list[datetime], when: datetime) -> bool:
    i = bisect.bisect_left(sorted_times, when - timedelta(seconds=MATCH_WINDOW_S))
    return i < len(sorted_times) and abs((sorted_times[i] - when).total_seconds()) < MATCH_WINDOW_S


def detect_windows(
    gw: GatewayData, downs: list[datetime], restarts: list[datetime], start: datetime, end: datetime,
    gateway_moves: list[datetime],
) -> list[Window]:
    """Fenêtres E1 à E3 de la règle d'exclusion, sur la période analysée."""

    windows: list[Window] = []

    # E1 : écart de plus de 75 s entre deux statistiques, élargi par le netwatch
    stats = [t for t in gw.stats if start - timedelta(hours=1) <= t <= end + timedelta(hours=1)]
    for before, after in zip(stats, stats[1:]):
        if after - before <= STATS_GAP:
            continue
        lo, hi = before, after
        for d in downs:
            if before - NETWATCH_SEARCH <= d <= after:
                lo = min(lo, d - NETWATCH_LEAD)
        for r in restarts:
            if before <= r <= after + NETWATCH_SEARCH:
                hi = max(hi, r + RESTART_TAIL)
        windows.append((lo, hi, "E1"))

    # E2 : relance de la LoRa, d'après le netwatch et les connexions au serveur
    for r in restarts:
        windows.append((r, r + RESTART_TAIL, "E2"))
    cluster: list[datetime] = []
    for t in gw.conn + [datetime.max.replace(tzinfo=PARIS)]:
        if cluster and t - cluster[-1] > CONN_CLUSTER:
            windows.append((cluster[0], cluster[-1] + RESTART_TAIL, "E2"))
            cluster = []
        cluster.append(t)

    # E3 : heure dont les trames étrangères sont trop faibles ou trop rares. La
    # référence est calculée séparément pour chaque position de la gateway ; l'heure
    # d'un déplacement n'est pas jugée (le déplacement est une intervention, E4).
    by_hour: defaultdict[datetime, list[int]] = defaultdict(list)
    for when, rssi in gw.foreign:
        if start <= when < end:
            by_hour[when.replace(minute=0, second=0, microsecond=0)].append(rssi)
    bounds = [start] + sorted(m for m in gateway_moves if start < m < end) + [end]
    for seg_start, seg_end in zip(bounds, bounds[1:]):
        hours = []
        h = seg_start.replace(minute=0, second=0, microsecond=0)
        while h < seg_end:
            if not any(h <= m < h + timedelta(hours=1) for m in gateway_moves):
                hours.append(h)
            h += timedelta(hours=1)
        full_hours = [h for h in hours if h >= seg_start and h + timedelta(hours=1) <= seg_end]
        all_rssi = [rssi for h in hours for rssi in by_hour[h]]
        if not (all_rssi and full_hours):
            continue
        rssi_ref = statistics.median(all_rssi)
        count_ref = statistics.median(len(by_hour[h]) for h in full_hours)
        for h in hours:
            rssi = by_hour[h]
            # une heure entamée n'est jugée que sur le RSSI, pas sur le nombre de trames
            partial = h not in full_hours
            weak = bool(rssi) and statistics.median(rssi) < rssi_ref - E3_RSSI_DROP_DB
            rare = not partial and len(rssi) < count_ref * E3_COUNT_RATIO
            if weak or rare:
                windows.append((h, h + timedelta(hours=1), "E3"))

    return [w for w in windows if w[1] > start and w[0] < end]


def mote_report(
    journal: Path,
    uplinks: list[dict[str, str]],
    start: datetime,
    end: datetime,
    windows: list[Window],
    excluded_hours: Counter[int],
) -> str:
    rows = read_csv(journal)
    deveui = next(r["deveui"] for r in rows if r.get("deveui")).lower()
    received = {u["payload"].upper(): u for u in uplinks if u["dev_eui"] == deveui}

    joins = [r for r in rows if r["event"] == "join"]
    accepted = [parse_time(r["utc"]).strftime("%d/%m %H:%M") for r in joins if r["async"] == "accepted"]
    print(f"\n=== {journal.stem.removeprefix('regime_1a_')} ({deveui})")
    print(f"joins : {len(joins)} {dict(Counter(r['async'] or r['immediate'] for r in joins))}, acceptés : {accepted}")

    in_period = [
        r for r in rows
        if r["event"] == "tx" and r["immediate"] == "ok" and start <= tx_time(r) < end
    ]
    rules = {id(r): excluded(tx_time(r), windows) for r in in_period}
    for r in in_period:
        if rules[id(r)]:
            excluded_hours[tx_time(r).hour] += 1
    kept = [r for r in in_period if not rules[id(r)]]
    kept_without_e3 = [r for r in in_period if rules[id(r)] in (None, "E3")]
    print(f"émissions : {len(in_period)}, exclues : {dict(Counter(v for v in rules.values() if v))}")
    print(f"réponses : {dict(Counter(r['async'] or '(aucune)' for r in kept))}")

    def pdr(rows_: list[dict[str, str]], sf: int) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
        sent = [r for r in rows_ if r["sf"] == str(sf)]
        return sent, [received[r["payload_hex"].upper()] for r in sent if r["payload_hex"].upper() in received]

    print(f"{'SF':>4} {'reçus':>6} {'émis':>5} {'PDR':>7} {'SNR médian':>11} {'PDR sans E3':>12}")
    for sf in SF_RANGE:
        sent, got = pdr(kept, sf)
        sent3, got3 = pdr(kept_without_e3, sf)
        rate = f"{100 * len(got) / len(sent):.1f} %" if sent else "-"
        rate3 = f"{100 * len(got3) / len(sent3):.1f} %" if sent3 else "-"
        snr = f"{statistics.median(float(g['snr_db']) for g in got):.2f}" if got else "-"
        print(f"{sf:>4} {len(got):>6} {len(sent):>5} {rate:>7} {snr:>11} {rate3:>12}")
    return deveui


def gateway_health(gw: GatewayData) -> None:
    stats: Counter[str] = Counter(t.strftime("%Y-%m-%d %Hh") for t in gw.stats)
    foreign: defaultdict[str, list[int]] = defaultdict(list)
    for when, rssi in gw.foreign:
        foreign[when.strftime("%Y-%m-%d %Hh")].append(rssi)

    print("Gateway fixe, heure par heure (heure de Paris)")
    print(f"{'heure':16} {'stats':>5} {'étrangères':>10} {'RSSI médian':>12}")
    for hour in sorted(set(stats) | set(foreign)):
        rssi = foreign[hour]
        median = f"{statistics.median(rssi):.1f}" if rssi else "-"
        print(f"{hour:16} {stats[hour]:5d} {len(rssi):10d} {median:>12}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("dossier", type=Path, help="dossier des journaux et des exports")
    parser.add_argument("--debut", type=parse_time, required=True, help="ex. 2026-11-06T11:53 (heure de Paris)")
    parser.add_argument("--fin", type=parse_time, required=True, help="ex. 2026-11-10T14:10 (heure de Paris)")
    parser.add_argument(
        "--exclure", type=parse_window, action="append", default=[],
        help="intervention documentée (E4) DÉBUT/FIN, répétable (voir docs/emplacements.md)",
    )
    parser.add_argument(
        "--deplacement-gateway", type=parse_time, action="append", default=[],
        help="heure d'un changement de position de la gateway, répétable : la référence E3 "
             "est calculée séparément de part et d'autre (ex. 2026-11-03T17:00)",
    )
    args = parser.parse_args()

    uplinks = read_csv(args.dossier / "uplinks.csv")
    journals = sorted(args.dossier.glob("regime_1a_*.csv"))
    euis = {
        next(r["deveui"] for r in read_csv(j) if r.get("deveui")).lower() for j in journals
    }
    gw = GatewayData(args.dossier, euis, uplinks)
    downs, restarts = read_netwatch(args.dossier / "netwatch.log")

    windows = detect_windows(gw, downs, restarts, args.debut, args.fin, args.deplacement_gateway)
    windows += [(a, b, "E4") for a, b in args.exclure]
    windows.sort()

    print(f"Période : {args.debut:%Y-%m-%d %H:%M} → {args.fin:%Y-%m-%d %H:%M} (heure de Paris)")
    print(f"Netwatch : {'netwatch.log absent' if not (downs or restarts) else f'{len(downs)} alertes, {len(restarts)} relances'}")
    print("Fenêtres d'exclusion :")
    for a, b, rule in windows:
        print(f"  {rule}  {a:%Y-%m-%d %H:%M:%S} → {b:%Y-%m-%d %H:%M:%S}  ({(b - a).total_seconds():.0f} s)")
    total = Counter()
    for a, b, rule in windows:
        total[rule] += (min(b, args.fin) - max(a, args.debut)).total_seconds()
    period_s = (args.fin - args.debut).total_seconds()
    print("Durée exclue : " + ", ".join(f"{r} {s / 60:.1f} min" for r, s in sorted(total.items()))
          + f" (sur {period_s / 3600:.1f} h, fenêtres qui se chevauchent comptées une fois par motif)")

    excluded_hours: Counter[int] = Counter()
    for journal in journals:
        mote_report(journal, uplinks, args.debut, args.fin, windows, excluded_hours)
    print("\nÉmissions exclues par heure de la journée (concentration à vérifier) :")
    hours = " ".join(f"{h}h:{excluded_hours[h]}" for h in range(24) if excluded_hours[h])
    print("  " + (hours or "aucune"))
    print()
    gateway_health(gw)


if __name__ == "__main__":
    main()
