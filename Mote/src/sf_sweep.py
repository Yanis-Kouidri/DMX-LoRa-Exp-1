"""
Balayage des Spreading Factors : un message par SF, envoyés à la suite.

Rejoint le réseau en OTAA si le module n'est pas déjà joint (arrêt avec un
message d'erreur en cas d'échec), désactive le duty cycle, puis envoie un
message en DR0 (SF12) jusqu'à DR5 (SF7), sans pause entre deux envois
(chaque `mac tx` attend déjà la fin des fenêtres RX1/RX2).

Le duty cycle étant désactivé, à n'utiliser qu'en environnement fermé.
La configuration n'est pas sauvegardée (pas de `mac save`), un `sys reset`
ou un redémarrage restaure les valeurs par défaut.

Hypothèse : région EU868, bande passante 125 kHz.
"""

from __future__ import annotations

from disable_duty_cycle import disable_duty_cycle
from serial_connection import RN2483Connection
from sf_burst_test import ensure_joined
from sf_test_campaign import DR_TO_SF, build_payload

PORT = "/dev/ttyACM0"

TX_ASYNC_TIMEOUT_S = 10.0  # couvre l'airtime SF12 + fenêtres RX1/RX2


def run() -> None:
    mote = RN2483Connection(PORT)
    results: dict[int, str] = {}

    try:
        ensure_joined(mote)

        print(f"mac set adr off -> {mote.set_adr(False)}")
        disable_duty_cycle(mote)

        for seq, (dr, sf) in enumerate(DR_TO_SF.items()):
            print(f"\n=== DR{dr} (SF{sf}) ===")

            dr_response = mote.set_dr(dr)
            if dr_response.lower() != "ok":
                print(f"  mac set dr {dr} -> {dr_response}, DR ignoré.")
                results[dr] = f"DR refusé ({dr_response})"
                continue

            # Le réseau peut imposer un autre DR via LinkADRReq (notamment
            # sur le premier downlink après un join), même avec l'ADR coupé.
            current_dr = mote.get_dr()
            if current_dr != dr:
                print(f"  DR modifié par le réseau (DR{current_dr}), retour à DR{dr} -> {mote.set_dr(dr)}")

            payload = build_payload(seq, dr)
            immediate, async_resp = mote.send_mac_tx(
                payload, async_timeout=TX_ASYNC_TIMEOUT_S
            )
            print(f"  payload={payload} immediate={immediate!r} async={async_resp!r}")

            if async_resp.lower() == "mac_tx_ok" or async_resp.lower().startswith("mac_rx"):
                results[dr] = "émis"
            else:
                results[dr] = f"échec ({immediate or '-'} / {async_resp or '-'})"

        print("\nRésumé (côté module) :")
        for dr, sf in DR_TO_SF.items():
            print(f"  DR{dr} (SF{sf}) : {results.get(dr, 'non tenté')}")

    finally:
        mote.close()


if __name__ == "__main__":
    run()
