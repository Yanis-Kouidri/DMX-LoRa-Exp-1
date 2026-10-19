# Motes RN2483

Inventaire des 6 motes Microchip RN2483, chacune branchée en USB
(`/dev/ttyACM0`) sur un Raspberry Pi (voir `raspberry-pi.md`).

## Inventaire

État relevé le 16 octobre 2026 avec `sys get ver`, `sys get hweui` et
`mac get deveui`.

| Pi          | HWEUI              | Firmware actuel | DevEUI configuré |
| ----------- | ------------------ | --------------- | ---------------- |
| `pi-mote-1` | `0004A30B0023F200` | 1.0.6 RC4       | oui (= HWEUI)    |
| `pi-mote-2` | `0004A30B00FD7996` | 1.0.6 RC4       | oui (= HWEUI)    |
| `pi-mote-3` | `0004A30B002428B8` | 1.0.6 RC4       | oui (= HWEUI)    |
| `pi-mote-4` | `0004A30B0023F575` | 1.0.6 RC4       | oui (= HWEUI)    |
| `pi-mote-5` | `0004A30B00240C83` | 1.0.6 RC4       | oui (= HWEUI)    |
| `pi-mote-6` | `0004A30B00240BA2` | 1.0.6 RC4       | oui (= HWEUI)    |

Toutes les motes sont livrées avec le firmware d'origine 1.0.1.

Le DevEUI est égal au HWEUI et l'AppEUI vaut `0000000000000000`. Le RN2483
ne permet pas de relire l'AppKey : elle n'apparaît donc pas dans ce tableau.

## Firmware 1.0.6 RC4

- Source : dépôt
  [MicrochipTech/RN2xx3_LORAWAN_FIRMWARE](https://github.com/MicrochipTech/RN2xx3_LORAWAN_FIRMWARE),
  fichier `software/firmware/RN2483EU_1.0.6_RC4/Binary/offset/RN2483_Parser.production.hex`,
  copié dans `firmware/RN2483EU_1.0.6_RC4/` (ignoré par git).
- `sys get ver` affiche `RN2483 1.0.6 RC3 May 18 2021 18:35:00` : Microchip
  n'a pas mis à jour la chaîne de version dans le binaire RC4.
- Flash avec `src/flash_firmware.py`, lancé depuis le Pi :

  ```bash
  uv run python src/flash_firmware.py firmware/RN2483EU_1.0.6_RC4/RN2483_Parser.production.hex
  ```

  Le flash ne touche pas à la configuration LoRaWAN sauvegardée (`mac save`) :
  `pi-mote-2` a gardé son DevEUI.

## Problème connu : mote de `pi-mote-4`

Liaison série instable : la mote se bloque au bout de quelques dizaines à
quelques centaines de commandes et seule une coupure de l'alimentation USB la
relance. Changer de port USB n'a rien corrigé (19 octobre 2026). Le flash en
RC4 a demandé 20 coupures. Détails dans `raspberry-pi.md`, section « Problème
connu : liaison série de `pi-mote-4` ».
