"""
Test de réception par Spreading Factor, sans contrainte de duty cycle.

Rejoint le réseau en OTAA si le module n'est pas déjà joint (arrêt avec un
message d'erreur en cas d'échec), puis envoie PACKETS_PER_DR paquets pour
chaque DR (donc chaque SF) avec une pause fixe entre deux envois.

Le duty cycle est volontairement ignoré : le script le désactive aussi dans
le module (sinon celui-ci répondrait "no_free_ch"). À n'utiliser qu'en
environnement fermé. La configuration n'est pas sauvegardée (pas de
`mac save`), un `mac reset` ou un redémarrage restaure les valeurs par défaut.

Hypothèse : région EU868, bande passante 125 kHz.
"""

from __future__ import annotations

import sys
import time

from serial_connection import RN2483Connection
from sf_test_campaign import DR_TO_SF, build_payload

PORT = "/dev/ttyACM0"

PACKETS_PER_DR = 20
DELAY_BETWEEN_PACKETS_S = 5.0
MAX_CHANNELS = 16        # canaux 0 à 15 sur le RN2483 (EU868)
TX_ASYNC_TIMEOUT_S = 10.0  # couvre l'airtime SF12 + fenêtres RX1/RX2


def ensure_joined(mote: RN2483Connection) -> None:
    """Rejoint le réseau en OTAA si nécessaire, sinon quitte avec une erreur claire."""

    if mote.is_joined():
        print("Module déjà joint au réseau, pas de nouveau join.")
        return

    print("Module non joint : lancement du join OTAA...")
    immediate, async_resp = mote.join_otaa()

    if immediate.lower() != "ok":
        sys.exit(
            f"ERREUR : le module a refusé 'mac join otaa' (réponse : {immediate!r}). "
            "Vérifiez deveui/appeui/appkey (keys_not_init) ou l'état du module."
        )

    if async_resp.lower() != "accepted":
        reason = "aucune réponse (timeout)" if not async_resp else repr(async_resp)
        sys.exit(
            f"ERREUR : échec du join OTAA, {reason}. "
            "Vérifiez que la gateway et ChirpStack sont joignables et que les "
            "clés correspondent au device enregistré."
        )

    print("Join OTAA accepté.")


def disable_duty_cycle(mote: RN2483Connection) -> None:
    """Passe tous les canaux à 100 % de duty cycle (après le join, qui peut en ajouter)."""

    for channel in range(MAX_CHANNELS):
        response = mote.set_channel_duty_cycle(channel, 0)
        if response.lower() != "ok":
            print(f"  mac set ch dcycle {channel} 0 -> {response} (canal ignoré)")


def run() -> None:
    mote = RN2483Connection(PORT)
    results: dict[int, int] = {}
    first_packet = True

    try:
        ensure_joined(mote)

        print(f"mac set adr off -> {mote.set_adr(False)}")
        print("Désactivation du duty cycle sur les canaux...")
        disable_duty_cycle(mote)

        for dr, sf in DR_TO_SF.items():
            print(f"\n=== DR{dr} (SF{sf}) ===")

            dr_response = mote.set_dr(dr)
            print(f"  mac set dr {dr} -> {dr_response}")

            if dr_response.lower() != "ok":
                print(f"  ATTENTION : configuration DR{dr} refusée, ce DR est ignoré.")
                continue

            results[dr] = 0

            for seq in range(PACKETS_PER_DR):
                if not first_packet:
                    time.sleep(DELAY_BETWEEN_PACKETS_S)
                first_packet = False

                # Le réseau peut imposer un autre DR via LinkADRReq (notamment
                # sur le premier downlink après un join), même avec l'ADR coupé.
                current_dr = mote.get_dr()
                if current_dr != dr:
                    print(f"  DR modifié par le réseau (DR{current_dr}), retour à DR{dr} -> {mote.set_dr(dr)}")

                payload = build_payload(seq, dr)
                immediate, async_resp = mote.send_mac_tx(
                    payload, async_timeout=TX_ASYNC_TIMEOUT_S
                )

                print(
                    f"  [{seq + 1}/{PACKETS_PER_DR}] payload={payload} "
                    f"immediate={immediate!r} async={async_resp!r}"
                )

                if async_resp.lower() == "mac_tx_ok" or async_resp.lower().startswith("mac_rx"):
                    results[dr] += 1

        print("\nRésumé (paquets émis avec succès côté module) :")
        for dr, sent in results.items():
            print(f"  DR{dr} (SF{DR_TO_SF[dr]}) : {sent}/{PACKETS_PER_DR}")

    finally:
        mote.close()


if __name__ == "__main__":
    run()
