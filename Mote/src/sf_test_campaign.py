"""
Campagne de test : variation du Spreading Factor (via Data Rate LoRaWAN)
et mesure du taux de réception côté gateway/ChirpStack.

Ce script gère uniquement le côté Mote : il envoie N paquets numérotés pour
chaque DR (donc chaque SF) testé, en respectant une pause conforme au duty
cycle EU868, et journalise chaque tentative dans un CSV.

Le taux de réception réel doit être calculé a posteriori en croisant ce CSV
avec les uplinks effectivement reçus dans ChirpStack (historique de
l'application, ou API HTTP/gRPC de ChirpStack) :
    taux(SF) = nb_uplinks_reçus(SF) / nb_paquets_envoyés(SF)

Hypothèse : région EU868, bande passante 125 kHz (à adapter si votre
configuration RN2483 diffère).
"""

from __future__ import annotations

import csv
import math
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from serial_connection import RN2483Connection

PORT = "/dev/ttyACM0"
CSV_PATH = Path("campagne_sf.csv")

# EU868, BW 125 kHz : correspondance DR -> SF
DR_TO_SF = {0: 12, 1: 11, 2: 10, 3: 9, 4: 8, 5: 7}

PACKETS_PER_DR = 1      # nombre de paquets envoyés par SF testé
DUTY_CYCLE = 0.01        # 1 % (canaux EU868 par défaut 868.1/868.3/868.5)
MIN_DELAY_S = 10.0        # plancher de sécurité entre deux envois
SAFETY_MARGIN = 1.2      # marge appliquée sur le temps de repos calculé


def airtime_seconds(
    sf: int,
    payload_bytes: int,
    bw_hz: int = 125_000,
    coding_rate: int = 1,          # 1 = 4/5
    preamble_symbols: int = 8,
    explicit_header: bool = True,
    crc_enabled: bool = True,
) -> float:
    """Calcule le temps d'antenne (airtime) selon la formule standard LoRa (Semtech)."""

    t_symbol = (2 ** sf) / bw_hz

    # Low Data Rate Optimization obligatoire en SF11/SF12 @ 125 kHz
    low_data_rate_optimize = 1 if (sf >= 11 and bw_hz == 125_000) else 0
    # Formule Semtech (AN1200.13) : H = 0 quand l'en-tête explicite est présent
    h = 0 if explicit_header else 1

    numerator = (
        8 * payload_bytes - 4 * sf + 28 + 16 * (1 if crc_enabled else 0) - 20 * h
    )
    denominator = 4 * (sf - 2 * low_data_rate_optimize)

    payload_symb_nb = 8 + max(math.ceil(numerator / denominator) * (coding_rate + 4), 0)

    t_preamble = (preamble_symbols + 4.25) * t_symbol
    t_payload = payload_symb_nb * t_symbol

    return t_preamble + t_payload


def delay_for_duty_cycle(airtime: float) -> float:
    """Pause minimale entre deux émissions pour respecter le duty cycle réglementaire."""

    period = airtime / DUTY_CYCLE
    off_time = (period - airtime) * SAFETY_MARGIN
    return max(off_time, MIN_DELAY_S)


@dataclass
class Attempt:
    timestamp: str
    dr: int
    sf: int
    seq: int
    payload_hex: str
    immediate_response: str
    async_response: str
    airtime_ms: float


def build_payload(seq: int, dr: int) -> str:
    """
    Payload de test : [seq (1 octet, 0-255)] [dr (1 octet)] [octet de bourrage].

    Le numéro de séquence permet de faire correspondre, côté ChirpStack,
    chaque uplink reçu à la tentative d'émission correspondante dans le CSV
    (et donc de détecter précisément quels paquets ont été perdus).
    """

    return bytes([seq % 256, dr, 0xAA]).hex().upper()


def run_campaign() -> None:
    mote = RN2483Connection(PORT)

    file_exists = CSV_PATH.exists()

    try:
        adr_response = mote.set_adr(False)
        print(f"mac set adr off -> {adr_response}")

        with CSV_PATH.open("a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "timestamp", "dr", "sf", "seq", "payload_hex",
                    "immediate_response", "async_response", "airtime_ms",
                ],
            )
            if not file_exists:
                writer.writeheader()

            for dr, sf in DR_TO_SF.items():
                print(f"\n=== DR{dr} (SF{sf}) ===")

                dr_response = mote.set_dr(dr)
                print(f"  mac set dr {dr} -> {dr_response}")

                if dr_response.lower() != "ok":
                    print(f"  ATTENTION : configuration DR{dr} refusée, ce DR est ignoré.")
                    continue

                for seq in range(PACKETS_PER_DR):
                    payload = build_payload(seq, dr)
                    airtime = airtime_seconds(sf, payload_bytes=len(payload) // 2)

                    immediate, async_resp = mote.send_mac_tx(payload, confirmed=False)

                    timestamp = datetime.now(timezone.utc).isoformat()

                    print(
                        f"  [{seq + 1}/{PACKETS_PER_DR}] payload={payload} "
                        f"immediate={immediate!r} async={async_resp!r} "
                        f"airtime={airtime * 1000:.1f} ms"
                    )

                    writer.writerow(
                        {
                            "timestamp": timestamp,
                            "dr": dr,
                            "sf": sf,
                            "seq": seq,
                            "payload_hex": payload,
                            "immediate_response": immediate,
                            "async_response": async_resp,
                            "airtime_ms": round(airtime * 1000, 2),
                        }
                    )
                    f.flush()

                    if immediate.lower() != "ok":
                        # Commande rejetée (ex: no_free_ch = duty cycle qui bloque
                        # encore le canal) : on attend un peu avant de retenter,
                        # sans appliquer le délai complet basé sur l'airtime.
                        time.sleep(MIN_DELAY_S)
                        continue

                    time.sleep(delay_for_duty_cycle(airtime))

        print(f"\nCampagne terminée. Résultats enregistrés dans {CSV_PATH.resolve()}")

    finally:
        mote.close()


if __name__ == "__main__":
    run_campaign()
