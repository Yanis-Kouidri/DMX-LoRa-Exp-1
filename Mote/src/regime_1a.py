"""
Régime 1a de la phase 1 : balayage entrelacé SF7 → SF12, sans ACK, en continu.

Voir docs/plan-experimental.md (section 7, phase 1). Chaque cycle envoie un
uplink non confirmé par SF, dans un ordre tiré au hasard à chaque cycle, sur
six créneaux régulièrement espacés. La période du cycle découle du duty cycle
réglementaire de 1 % : temps d'émission cumulé des six SF / 1 %, plus une
marge. Le duty cycle du module reste actif : si aucun canal n'est libre
(`no_free_ch`), l'envoi est retenté jusqu'à la fin du créneau, puis abandonné
et journalisé comme tel.

Chaque événement (configuration, join, émission, abandon, erreur) est ajouté
au journal CSV `<log-dir>/regime_1a_<hôte>.csv`, avec l'heure UTC (horloge
synchronisée par NTP) et le compteur de trames (FCnt) utilisé. Pour une
émission, `utc_tx_start` est l'envoi de la commande `mac tx` et `utc` la fin
des fenêtres RX1 et RX2. Ce journal est
le dénominateur du PDR : il se croise avec les réceptions de la base par
DevEUI et FCnt, ou par le numéro de cycle contenu dans la charge utile.

Charge utile (6 octets, comme le dimensionnement du plan) :
    [cycle, 4 octets big-endian] [DR, 1 octet] [0x1A, marqueur du régime]

Hypothèse : région EU868, bande passante 125 kHz.
"""

from __future__ import annotations

import argparse
import csv
import random
import signal
import socket
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from serial import SerialException

from serial_connection import RN2483Connection
from sf_test_campaign import DR_TO_SF, airtime_seconds

PORT = "/dev/ttyACM0"
DEFAULT_LOG_DIR = Path.home() / "lora-logs"

PAYLOAD_BYTES = 6
LORAWAN_OVERHEAD_BYTES = 13  # MHDR + FHDR (sans FOpts) + FPort + MIC
REGIME_MARKER = 0x1A

PWRIDX = 1               # 14 dBm en EU868, fixe pendant toute la phase 1
DUTY_CYCLE = 0.01
SAFETY_MARGIN = 1.1
NO_FREE_CH_RETRY_S = 5.0
SLOT_GUARD_S = 10.0      # pas de nouvel essai dans les dernières secondes du créneau
TX_ASYNC_TIMEOUT_S = 15.0  # airtime SF12 + RX1 + RX2, avec marge
JOIN_DR = 0              # join en SF12 : seul SF garanti à tous les emplacements
JOIN_RETRY_S = (60, 120, 300, 600)
SERIAL_RETRY_S = 30.0

FIELDNAMES = [
    "utc", "host", "deveui", "event", "cycle", "slot", "dr", "sf", "upctr",
    "payload_hex", "attempts", "immediate", "async", "utc_tx_start", "airtime_ms",
    "detail",
]

AIRTIME_S = {
    dr: airtime_seconds(sf, PAYLOAD_BYTES + LORAWAN_OVERHEAD_BYTES)
    for dr, sf in DR_TO_SF.items()
}
CYCLE_PERIOD_S = sum(AIRTIME_S.values()) / DUTY_CYCLE * SAFETY_MARGIN
SLOT_S = CYCLE_PERIOD_S / len(DR_TO_SF)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def build_payload(cycle: int, dr: int) -> str:
    return (cycle.to_bytes(4, "big") + bytes([dr, REGIME_MARKER])).hex().upper()


class Journal:
    """Journal CSV en ajout, vidé après chaque ligne pour survivre à une coupure."""

    def __init__(self, path: Path, host: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        new_file = not path.exists() or path.stat().st_size == 0
        self.path = path
        self.host = host
        self.deveui = ""
        self._file = path.open("a", newline="", encoding="utf-8")
        self._writer = csv.DictWriter(self._file, fieldnames=FIELDNAMES)
        if new_file:
            self._writer.writeheader()
            self._file.flush()

    def write(self, event: str, **fields: object) -> None:
        row = {"utc": utc_now(), "host": self.host, "deveui": self.deveui, "event": event}
        row.update(fields)
        self._writer.writerow(row)
        self._file.flush()
        print(" ".join(f"{k}={v}" for k, v in row.items() if v not in ("", None)), flush=True)

    def close(self) -> None:
        self._file.close()


def last_cycle(path: Path) -> int:
    """Dernier numéro de cycle du journal, pour ne jamais réutiliser un numéro après un redémarrage."""

    if not path.exists():
        return -1
    with path.open(newline="", encoding="utf-8") as f:
        cycles = [int(row["cycle"]) for row in csv.DictReader(f) if row.get("cycle")]
    return max(cycles, default=-1)


def configure(mote: RN2483Connection, journal: Journal) -> None:
    """Fixe les paramètres de la phase 1 et journalise l'état du module."""

    journal.deveui = mote.send_command("mac get deveui")
    responses = {
        "adr off": mote.set_adr(False),
        f"pwridx {PWRIDX}": mote.send_command(f"mac set pwridx {PWRIDX}"),
    }
    if any(r.lower() != "ok" for r in responses.values()):
        raise RuntimeError(f"Configuration refusée par le module : {responses}")

    state = {
        "ver": mote.send_command("sys get ver"),
        "pwridx": mote.send_command("mac get pwridx"),
        "rxdelay1": mote.send_command("mac get rxdelay1"),
        "rx2": mote.send_command("mac get rx2 868"),
        "dcycleps": mote.send_command("mac get dcycleps"),
        "cycle_period_s": round(CYCLE_PERIOD_S, 1),
        "slot_s": round(SLOT_S, 1),
    }
    journal.write("config", detail=state)


def join(mote: RN2483Connection, journal: Journal) -> None:
    """Join OTAA en SF12, retenté avec un délai croissant jusqu'au succès."""

    attempt = 0
    while True:
        attempt += 1
        mote.set_dr(JOIN_DR)
        immediate, async_resp = mote.join_otaa()
        journal.write(
            "join", dr=JOIN_DR, sf=DR_TO_SF[JOIN_DR], attempts=attempt,
            immediate=immediate, **{"async": async_resp},
        )
        if async_resp.lower() == "accepted":
            journal.write("channels", detail=channel_table(mote))
            return
        time.sleep(JOIN_RETRY_S[min(attempt - 1, len(JOIN_RETRY_S) - 1)])


def channel_table(mote: RN2483Connection) -> dict[int, str]:
    """Canaux actifs après le join (CFList) : fréquence et duty cycle du module."""

    table = {}
    for ch in range(16):
        if mote.send_command(f"mac get ch status {ch}") == "on":
            freq = mote.send_command(f"mac get ch freq {ch}")
            dcycle = mote.send_command(f"mac get ch dcycle {ch}")
            table[ch] = f"{freq}/{dcycle}"
    return table


def send_slot(
    mote: RN2483Connection, journal: Journal, cycle: int, slot: int, dr: int, deadline: float,
) -> None:
    """Envoie le paquet d'un créneau, en retentant sur `no_free_ch` jusqu'à `deadline`."""

    sf = DR_TO_SF[dr]
    payload = build_payload(cycle, dr)
    common = {
        "cycle": cycle, "slot": slot, "dr": dr, "sf": sf, "payload_hex": payload,
        "airtime_ms": round(AIRTIME_S[dr] * 1000, 1),
    }

    response = mote.set_dr(dr)
    if response.lower() != "ok":
        journal.write("error", **common, detail=f"mac set dr {dr} -> {response}")
        return

    attempts = 0
    while True:
        attempts += 1
        upctr = mote.send_command("mac get upctr")
        start = utc_now()
        immediate, async_resp = mote.send_mac_tx(payload, async_timeout=TX_ASYNC_TIMEOUT_S)

        if immediate.lower() == "ok":
            journal.write(
                "tx", **common, upctr=upctr, attempts=attempts, immediate=immediate,
                utc_tx_start=start, **{"async": async_resp},
            )
            return
        if immediate.lower() == "not_joined":
            journal.write("skip", **common, attempts=attempts, immediate=immediate)
            join(mote, journal)
            return
        if immediate.lower() != "no_free_ch" or time.monotonic() + NO_FREE_CH_RETRY_S > deadline:
            journal.write("skip", **common, upctr=upctr, attempts=attempts, immediate=immediate)
            return
        time.sleep(NO_FREE_CH_RETRY_S)


def run(port: str, log_path: Path, max_cycles: int) -> None:
    journal = Journal(log_path, socket.gethostname())
    cycle = last_cycle(log_path) + 1
    done = 0
    mote: RN2483Connection | None = None

    try:
        while max_cycles == 0 or done < max_cycles:
            try:
                if mote is None:
                    mote = RN2483Connection(port, exclusive=True)
                    configure(mote, journal)
                    if not mote.is_joined():
                        join(mote, journal)

                order = random.sample(sorted(DR_TO_SF), k=len(DR_TO_SF))
                cycle_start = time.monotonic()
                for slot, dr in enumerate(order):
                    slot_start = cycle_start + slot * SLOT_S
                    time.sleep(max(0.0, slot_start - time.monotonic()))
                    send_slot(mote, journal, cycle, slot, dr, slot_start + SLOT_S - SLOT_GUARD_S)
                time.sleep(max(0.0, cycle_start + CYCLE_PERIOD_S - time.monotonic()))

            except (SerialException, OSError, RuntimeError) as exc:
                journal.write("error", cycle=cycle, detail=repr(exc))
                if mote is not None:
                    mote.close()
                    mote = None
                time.sleep(SERIAL_RETRY_S)

            cycle += 1
            done += 1
    finally:
        if mote is not None:
            mote.close()
        journal.write("stop", cycle=cycle)
        journal.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("-p", "--port", default=PORT)
    parser.add_argument("--log-dir", type=Path, default=DEFAULT_LOG_DIR)
    parser.add_argument(
        "--cycles", type=int, default=0, help="nombre de cycles (0 : sans fin, par défaut)",
    )
    args = parser.parse_args()

    # systemd arrête le service par SIGTERM : on passe par le bloc finally
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))

    log_path = args.log_dir / f"regime_1a_{socket.gethostname()}.csv"
    print(
        f"Cycle de {CYCLE_PERIOD_S:.0f} s, créneaux de {SLOT_S:.0f} s, journal {log_path}",
        flush=True,
    )
    run(args.port, log_path, args.cycles)


if __name__ == "__main__":
    main()
