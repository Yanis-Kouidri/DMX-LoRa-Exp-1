# Mote

Scripts Python de pilotage des motes **Microchip RN2483 LoRa Technology Mote**
par liaison série USB, depuis un Raspberry Pi ou un PC.

| Document | Contenu |
|---|---|
| [`config.md`](config.md) | Commandes RN2483 : configuration pour ChirpStack, join OTAA, désactivation du duty cycle |
| [`mote.md`](mote.md) | Inventaire des 6 motes, mote défectueuse retirée |
| [`raspberry-pi.md`](raspberry-pi.md) | Matériel, OS et installation des Raspberry Pi (eduroam, Tailscale) |

## Matériel

- **Carte** : Microchip RN2483 LoRa Technology Mote, carte d'évaluation LoRa et
  LoRaWAN.
- **Modem LoRa** : Microchip RN2483A (868 MHz, EU868).
- **Liaison** : USB CDC (identifiant `04d8:000a`), vue comme `/dev/ttyACM0`,
  57 600 bauds.

## Firmware

Toutes les motes doivent tourner en **RN2483 1.0.6 RC4** (EU868, LoRaWAN
1.0.2), la dernière version publiée par Microchip pour le RN2483. Les motes
neuves sont livrées en 1.0.1 et doivent être flashées avant l'installation.

- **Source** : dépôt
  [MicrochipTech/RN2xx3_LORAWAN_FIRMWARE](https://github.com/MicrochipTech/RN2xx3_LORAWAN_FIRMWARE),
  fichier `software/firmware/RN2483EU_1.0.6_RC4/Binary/offset/RN2483_Parser.production.hex`
  (blob git `46f6913c06273d5d8a7fcdd86519c1cc72402def`).
- **Version affichée** : `sys get ver` répond
  `RN2483 1.0.6 RC3 May 18 2021 18:35:00`. C'est normal : Microchip n'a pas mis
  à jour la chaîne de version dans le binaire RC4.
- **LoRaWAN 1.0.2** : c'est la version la plus récente prise en charge
  officiellement sur ce module. Aucun firmware officiel du RN2483 n'implémente
  LoRaWAN 1.0.4 ou 1.1.
- **LoRaWAN 1.1 hors de portée** : le RN2483 tourne sur un PIC18LF46K22 (64 Ko
  de flash, environ 3,9 Ko de RAM), et l'image 1.0.6 RC4 occupe déjà 904 des
  1012 lignes de flash (environ 7 Ko libres). LoRaWAN 1.1 refond la couche de
  sécurité (NwkKey et AppKey, trois clés de session réseau, nouveau calcul du
  MIC, chiffrement des FOpts, procédures de rekey et de rejoin), ce qui ne
  tiendrait pas dans la place restante.

### Flasher une mote

Le firmware n'est pas versionné (`firmware/` est ignoré par git). Depuis le
dossier `Mote/`, le télécharger :

```bash
curl -fL --create-dirs -o firmware/RN2483EU_1.0.6_RC4/RN2483_Parser.production.hex https://raw.githubusercontent.com/MicrochipTech/RN2xx3_LORAWAN_FIRMWARE/main/software/firmware/RN2483EU_1.0.6_RC4/Binary/offset/RN2483_Parser.production.hex
```

Puis flasher :

```bash
uv run python src/flash_firmware.py firmware/RN2483EU_1.0.6_RC4/RN2483_Parser.production.hex
```

- `--dry-run` vérifie le fichier HEX sans toucher au module.
- Si le flash est interrompu, le module reste en bootloader : relancer avec
  `--resume`.
- Le flash ne touche pas à la configuration LoRaWAN sauvegardée
  (`mac save`) : DevEUI, AppEUI et AppKey sont conservés.

## Installation

Le projet utilise [uv](https://docs.astral.sh/uv/), qui installe Python 3.14
(`.python-version`) et les dépendances (`pyserial`). Depuis le dossier
`Mote/` :

```bash
uv sync
```

Sur les Raspberry Pi, uv et le dépôt sont installés par
[`scripts/setup-pi.sh`](scripts/setup-pi.sh) (voir
[`raspberry-pi.md`](raspberry-pi.md)).

## Connexion de la mote sous WSL 2

Pour utiliser la mote depuis WSL, la rattacher à WSL avec
[usbipd-win](https://github.com/dorssel/usbipd-win), dans PowerShell sous
Windows :

```powershell
usbipd attach --wsl --hardware-id 04d8:000a
```

Ou, avec le numéro de bus relevé par `usbipd list` :

```powershell
usbipd attach --wsl --busid <busid>
```

## Scripts

À lancer depuis le dossier `Mote/` avec `uv run python src/<script>.py`. Sauf
mention contraire, ils utilisent le port `/dev/ttyACM0`.

| Script | Rôle |
|---|---|
| `terminal.py` | Shell interactif RN2483 : complétion, historique (les commandes contenant une clé ne sont pas enregistrées), attente des réponses asynchrones, `resync` du débit, affichage `hex on`. Options `-p` (port) et `-b` (débit) |
| `print_info.py` | Affiche l'état du module : firmware, HWEUI, alimentation, paramètres radio et LoRaWAN |
| `flash_firmware.py` | Flashe un firmware par le bootloader UART (voir [Firmware](#firmware)) |
| `disable_duty_cycle.py` | Désactive le duty cycle sur les 16 canaux et vérifie chaque valeur (voir [`config.md`](config.md)) |
| `send_data_tuple.py` | Envoie toutes les 30 s un uplink non confirmé avec des mesures fictives (température, humidité, batterie). La mote doit déjà avoir rejoint le réseau |
| `sf_test_campaign.py` | Envoie des paquets numérotés de SF12 à SF7, sans ACK, en respectant le duty cycle, et les journalise dans `campagne_sf.csv` (non versionné) |
| `sf_burst_test.py` | Join OTAA si besoin, puis 100 tours entrelacés SF7 → SF12, un paquet toutes les 5 s. **Désactive le duty cycle** |
| `sf_sweep.py` | Join OTAA si besoin, puis un paquet par SF, de SF12 à SF7, sans pause. **Désactive le duty cycle** |
| `serial_connection.py` | Classe `RN2483Connection`, utilisée par tous les scripts |

⚠️ `sf_burst_test.py`, `sf_sweep.py` et `disable_duty_cycle.py` ne respectent
pas le duty cycle réglementaire de 1 % en EU868 : à n'utiliser qu'en
environnement fermé, jamais sur le campus. Ils ne font pas de `mac save` : un
`sys reset` restaure les valeurs par défaut.
