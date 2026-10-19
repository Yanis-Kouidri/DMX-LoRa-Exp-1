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

## Mote défectueuse : `0004A30B0023F575` (`pi-mote-4`)

**Conclusion : défaut matériel de la mote. À remplacer pour la campagne.**

### Symptômes

- La liaison série s'arrête en pleine réponse (par exemple
  `RN2483 1.0.6 RC3 May 18 202`, coupée au 27e caractère), puis plus rien ne
  sort : ni retour à la ligne seul, ni break suivi de `0x55`, ni port rouvert.
- La mote reste visible en USB et le noyau ne signale aucune erreur.
- Seule une coupure de l'alimentation USB la relance (voir `raspberry-pi.md`,
  section « Coupure USB à distance sur `pi-mote-4` »).
- Le blocage survient au bout de quelques dizaines à quelques centaines de
  commandes. Les commandes `mac tx` passent par la même liaison : la campagne
  y serait exposée.
- Le passage en 1.0.6 RC4 a demandé 20 coupures USB sur 1012 lignes écrites :
  `src/flash_firmware.py` échoue sur cette mote, il a fallu un flash qui
  reprend à la ligne bloquée après chaque coupure.

### Essais

Test : 3000 `sys get ver` d'affilée, coupure USB entre deux passages. Mote
témoin : `0004A30B00240C83` (`pi-mote-5`), 3000 sur 3000 à chaque passage.

| Date            | Montage                                    | Mote `…F575`                             | Mote témoin                  |
| --------------- | ------------------------------------------ | ---------------------------------------- | ---------------------------- |
| 16 octobre 2026 | `pi-mote-4`, port USB 3 du hub             | bloquée après 211 commandes (sur 500)    | 500 sur 500                  |
| 19 octobre 2026 | `pi-mote-4`, port USB 4 du hub, même câble | bloquée après 339, 62 puis 144 commandes | 3000 sur 3000                |
| 19 octobre 2026 | câbles échangés entre `pi-mote-4` et `-5`  | bloquée après 257, 307 puis 23 commandes | 3000 sur 3000                |
| 19 octobre 2026 | `pi-mote-4` redémarré                      | bloquée après 90, 276 puis 62 commandes  | —                            |
| 19 octobre 2026 | motes échangées entre `pi-mote-4` et `-5`  | bloquée après 72 commandes (sur `-5`)    | 3 × 3000 sur 3000 (sur `-4`) |

Le défaut suit la mote : le Pi, le port USB et le câble sont hors de cause.
Les motes ont ensuite été remises à leur place.

### Pourquoi un défaut matériel

- **Firmware du RN2483 hors de cause** : le blocage existait en 1.0.1, existe
  en 1.0.6 RC4, et survient même dans le bootloader pendant le flash. Le
  bootloader est identique sur toutes les motes et n'utilise pas la
  configuration stockée.
- **Rien ne la distingue des motes saines côté logiciel** : même identité USB
  (`04d8:000a`, `bcdDevice 1.00`, « CDC RS-232 Emulation Demo ») et même
  firmware RN2483.
- **Reste le matériel** : alimentation du module, horloge, soudure, ou le PIC
  qui fait le pont entre l'USB et le RN2483.

Seule piste logicielle restante, peu probable : reflasher le firmware du PIC
(programmateur PICkit sur le connecteur ICSP de la carte). Avant de remplacer
la mote, vérifier qu'elle n'est pas alimentée par des piles AAA faibles
(sélecteur d'alimentation, piles restées dans le boîtier).
