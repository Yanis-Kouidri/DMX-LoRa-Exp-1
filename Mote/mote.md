# Motes RN2483

Inventaire des 6 motes Microchip RN2483 de la campagne, chacune branchée en
USB (`/dev/ttyACM0`) sur un Raspberry Pi (voir [`raspberry-pi.md`](raspberry-pi.md)).
La mote N est pilotée par `pi-mote-N`. Une 7e mote sert aux tests et au banc
PPK2 ([mote de test](#mote-de-test-0004a30b00fd7330)). Emplacements :
[`docs/emplacements.md`](../docs/emplacements.md).

## Inventaire

État relevé le 16 octobre 2026 avec `sys get ver`, `sys get hweui` et
`mac get deveui`, puis le 19 octobre 2026 pour `pi-mote-4` (mote remplacée).

| Pi          | HWEUI              | Firmware actuel | DevEUI configuré |
| ----------- | ------------------ | --------------- | ---------------- |
| `pi-mote-1` | `0004A30B0023F200` | 1.0.6 RC4       | oui (= HWEUI)    |
| `pi-mote-2` | `0004A30B00FD7996` | 1.0.6 RC4       | oui (= HWEUI)    |
| `pi-mote-3` | `0004A30B002428B8` | 1.0.6 RC4       | oui (= HWEUI)    |
| `pi-mote-4` | `0004A30B0023EE8A` | 1.0.6 RC4       | oui (= HWEUI)    |
| `pi-mote-5` | `0004A30B00240C83` | 1.0.6 RC4       | oui (= HWEUI)    |
| `pi-mote-6` | `0004A30B00240BA2` | 1.0.6 RC4       | oui (= HWEUI)    |

Toutes les motes ont été livrées en 1.0.1, puis flashées en 1.0.6 RC4 (voir
[`README.md`](README.md#firmware)).

Le DevEUI est égal au HWEUI et l'AppEUI vaut `0000000000000000` (configuration :
[`config.md`](config.md)). Le RN2483 ne permet pas de relire l'AppKey : elle
n'apparaît donc pas dans ce tableau.

## Mote de test `0004A30B00FD7330`

Mote hors campagne, non déployée : tests et mesure du coût énergétique avec le
PPK2 (banc de la
[section 9 du plan](../docs/plan-experimental.md#9-modèle-énergétique-et-banc-ppk2)).
Relevé du 29 octobre 2026 :

- Livrée en 1.0.5, avec la configuration d'un ancien usage (DevEUI
  `DEADDEAD00090005`, AppEUI `DEAD25DEAD25DEAD`), effacée par `mac reset 868`.
- Flashée en 1.0.6 RC4 avec `src/flash_firmware.py` du premier coup, contenu
  relu et vérifié.
- DevEUI = HWEUI, AppEUI `0000000000000000`, `mac save`, conservés après
  `sys reset`.
- Device `mote-test` créé dans ChirpStack (application `mote-rn2483`, profil
  `rn2483-eu868-otaa`, tag `role=test` pour l'exclure des analyses), AppKey
  propre configurée et sauvegardée (`mac save`).
- 3 × 3000 `sys get ver` sur 3000 en 1.0.6 RC4.
- Join OTAA tenté hors du campus : `denied`, aucune gateway n'a reçu la
  requête (hors de portée). Join à refaire sur le campus ; en cas d'échec,
  vérifier dans ChirpStack (LoRaWAN frames) l'absence d'erreur MIC (AppKey).

## Mote défectueuse `0004A30B0023F575` (retirée)

Défaut matériel : la mote a été remplacée sur `pi-mote-4` par
`0004A30B0023EE8A` le 19 octobre 2026 et ne doit pas servir pour la campagne.

### Symptômes

- La liaison série s'arrête en pleine réponse (par exemple
  `RN2483 1.0.6 RC3 May 18 202`, coupée au 27e caractère), puis plus rien ne
  sort : ni retour à la ligne seul, ni break suivi de `0x55`, ni port rouvert.
- La mote reste visible en USB et le noyau ne signale aucune erreur.
- Seule une coupure de l'alimentation USB la relance (voir
  [`raspberry-pi.md`](raspberry-pi.md#coupure-usb-à-distance-sur-pi-mote-4)).
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

Pistes non explorées, si la mote devait resservir : vérifier qu'elle n'est pas
alimentée par des piles AAA faibles (sélecteur d'alimentation, piles restées
dans le boîtier), puis reflasher le firmware du PIC (programmateur PICkit sur
le connecteur ICSP de la carte).

### Mote de remplacement `0004A30B0023EE8A`

- Livrée en 1.0.1, avec la configuration d'un ancien usage (DevEUI
  `DEADDEAD00090007`, AppEUI `DEAD25DEAD25DEAD`), effacée par `mac reset 868`.
- 3 × 3000 `sys get ver` sur 3000 en 1.0.1, puis 3000 sur 3000 en 1.0.6 RC4.
- Flashée en 1.0.6 RC4 avec `src/flash_firmware.py` du premier coup, contenu
  relu et vérifié.
- DevEUI = HWEUI, AppEUI `0000000000000000`, `mac save`, conservés après
  `sys reset`.
