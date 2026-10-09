"""
Désactive le duty cycle du RN2483, pour les tests en environnement fermé.

Passe tous les canaux à 100 % (`mac set ch dcycle <ch> 0`) et lève la
limite globale que le réseau peut imposer via DutyCycleReq
(`mac set dcycleps 1`), puis relit les valeurs pour vérifier.

À lancer APRÈS le join : un join OTAA peut ajouter des canaux (CFList)
avec leur duty cycle par défaut.

La configuration n'est pas sauvegardée (pas de `mac save`) : un
`sys reset` ou un redémarrage restaure les valeurs par défaut. Ne pas
sauvegarder cette configuration, elle n'est pas conforme hors
environnement fermé.
"""

from __future__ import annotations

from serial_connection import RN2483Connection

PORT = "/dev/ttyACM0"

MAX_CHANNELS = 16  # canaux 0 à 15 sur le RN2483 (EU868)


def run() -> None:
    mote = RN2483Connection(PORT)

    try:
        print("Duty cycle des canaux :")
        for channel in range(MAX_CHANNELS):
            response = mote.set_channel_duty_cycle(channel, 0)
            if response.lower() != "ok":
                print(f"  canal {channel:2d} : ignoré ({response})")
                continue

            value = mote.send_command(f"mac get ch dcycle {channel}")
            status = "OK" if value == "0" else "ÉCHEC"
            print(f"  canal {channel:2d} : dcycle={value} -> {status}")

        response = mote.send_command("mac set dcycleps 1")
        value = mote.send_command("mac get dcycleps")
        status = "OK" if response.lower() == "ok" and value == "1" else "ÉCHEC"
        print(f"Prescaler global : dcycleps={value} -> {status}")

    finally:
        mote.close()


if __name__ == "__main__":
    run()
