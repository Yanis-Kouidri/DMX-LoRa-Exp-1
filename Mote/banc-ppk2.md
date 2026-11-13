# Banc de mesure d'énergie (PPK2)

Montage du Nordic Power Profiler Kit II (PPK2) sur la
[mote de test](mote.md#mote-de-test-0004a30b00fd7330) `0004A30B00FD7330`,
pour mesurer le coût énergétique de chaque événement LoRaWAN (principe et
événements à mesurer : [section 9 du plan](../docs/plan-experimental.md#9-modèle-énergétique-et-banc-ppk2)).

> Procédure définie le 29 octobre 2026 à partir du schéma de la carte. Le
> [journal](#journal-des-modifications) est complété au fur et à mesure.
>
> **Changement de montage le 2 novembre 2026** : R4 est retirée, mais souder
> des fils sur ses pastilles 0603 s'est révélé impossible. Les étapes 4 à 7
> ci-dessous (fils sur R4, PPK2 en mode AMP) sont abandonnées au profit du
> [montage sans USB](#montage-retenu-sans-usb-2-novembre-2026). Cette page
> sera réécrite (procédure de montage complète) maintenant que ce montage est
> validé par le banc automatique du 10 novembre 2026.

## Montage retenu : sans USB (2 novembre 2026)

R4 retirée, le rail 3,3 V est isolé du régulateur, du boost et de l'entrée
piles. Sans USB ni piles, ce côté n'est pas alimenté, et on alimente le rail
directement (vérifié sur les figures A-1 et A-2 du guide) :

| De | Vers |
|---|---|
| PPK2 VOUT, mode **SMU** à 3300 mV | J4 `+3.3V` |
| PPK2 GND | J4 `GND` (masse commune sur une breadboard) |
| Raspberry Pi broche 8 (GPIO14, TX) | J4 `UARTRX` (entrée du module, broche 7) |
| Raspberry Pi broche 10 (GPIO15, RX) | J4 `UARTTX` (sortie du module, broche 6) |
| Raspberry Pi broche 6 (GND) | masse commune |
| Raspberry Pi broche 11 (GPIO17, repère) | PPK2 port logique D0 |
| Raspberry Pi broche 1 (3,3 V) | PPK2 port logique VCC (référence de niveau) |
| Raspberry Pi broche 9 (GND) | PPK2 port logique GND |
| J2 broche 1 (`MCLR` du PIC) | J2 broche 3 (`GND`) |

- **PIC en reset par J2** : sans USB, son firmware passerait en mode piles
  (join et envois automatiques, guide section 2.4.2) et occuperait la ligne
  série. En reset, ses broches sont en haute impédance. **J2 et non J5** : J5
  est le connecteur de programmation du RN2483 ; relier son MCLR à GND
  bloquerait le module.
- **Effets sur le fond** : écran et capteurs éteints (Q2 coupé par R17), LED
  D2 non alimentée. Résidu connu : R14, environ 330 µA (3,3 V / 10 kΩ).
  Fond mesuré, module en sommeil : environ 1,4 mA.
- **Mode SMU sans risque** : le boost n'est plus alimenté.
- **Acquisition sur le PC Windows** : le PPK2 est branché en USB sur le PC.
  Lu par le Raspberry Pi, il perd environ 16 % des échantillons (voir le
  journal, 9 novembre 2026).
- **Pilotage** : Raspberry Pi 5 `pi-ppk2` (Tailscale), UART0 activé sur
  GPIO14/15 (`dtparam=uart0=on`, `/dev/ttyAMA0`), dépôt cloné dans
  `~/DMX-LoRa-Exp-1`.
- **Repère sur D0** : le Pi bascule GPIO17 autour de chaque commande `mac tx`.
  Le repère est enregistré dans le flux du PPK2 : il sert au découpage des
  messages et au contrôle d'intégrité, sans dépendre d'aucune horloge
  d'ordinateur.
- **Risque identifié** : la grille de Q4 (`MODRST`) n'est reliée qu'au PIC et
  flotte quand il est en reset ; R20 maintient normalement le module actif.
  Un reset du module se détecte par l'envoi spontané de sa chaîne de version :
  la mesure en cours est alors rejetée.
- **Liaison série** : après une mise sous tension ou un sommeil, le RN2483
  attend une resynchronisation (break puis `0x55`) avant de répondre.
- **Précautions** : le TX du Pi ne doit être en sortie que lorsque le PPK2
  alimente la mote, sinon le Pi alimente le module par la ligne série. Le PPK2
  coupe sa sortie dès que le programme qui le pilote se ferme, et le Pi remet
  GPIO14 en TXD0 (niveau haut) à chaque démarrage : TX débranché, ou GPIO14 en
  entrée hors des mesures : le service `Mote/systemd/ppk2-tx-input.service`
  le fait à chaque démarrage, `banc_pi.py` à la fin de chaque série. Rétroéclairage débranché ;
  antenne vissée sur J3.
- **Sonde réussie** : nécessite un banc à portée de la gateway de l'IRIT et
  un join OTAA.

## Banc automatique (10 novembre 2026)

Trois scripts de `Mote/src/`, chacun sur sa machine :

| Script | Machine | Rôle |
|---|---|---|
| `ppk2_record.py` | PC Windows, Python natif | Alimente la mote (source de tension), enregistre courant et voies logiques à 100 kS/s sur disque |
| `banc_pi.py` | `pi-ppk2` | Session ABP factice, puis pour chaque tentative : sommeil, réveil, repère haut, `mac tx`, réponse, repère bas |
| `banc_ppk2.py` | WSL | Lance les deux autres, découpe chaque message grâce aux repères, contrôle l'intégrité, calcule l'énergie |

Depuis WSL, dans le dossier `Mote/` :

```bash
uv run python src/banc_ppk2.py --sf 7 8 9 10 11 12 --reps 30 --mode uncnf --payload 6
```

- **Sommeil avant chaque tentative** : au moins le repos imposé par le duty
  cycle de 1 % au SF concerné (environ 101 fois le temps d'émission), et au
  moins `--sleep-ms`. Le duty cycle du module reste actif ; une tentative
  refusée (`no_free_ch`) est retentée.
- **Énergie d'un message** : du début de l'émission (premier échantillon
  au-dessus de 30 mA) à la fin de RX2 (dernier au-dessus de 8 mA),
  E = (∫ I dt − I_fond × durée) × 3,3 V, avec I_fond le courant moyen pendant
  le sommeil qui précède (sans sa première seconde ni sa dernière
  demi-seconde).
- **Intégrité** : entre deux repères hauts successifs, le nombre d'échantillons
  doit valoir 100 000 par seconde de l'horloge du Pi, à 500 échantillons près.
  Une tentative hors tolérance, sans émission ou avec redémarrage du module
  reste dans le CSV mais est exclue du résumé.
- **Sorties** dans `C:\Users\<utilisateur>\banc-ppk2\data\` : échantillons
  bruts (`.cur.f32`, courant en µA ; `.dig.u8`, voies logiques), CSV par
  tentative, JSON de métadonnées (arguments, commit du dépôt, empreintes des
  scripts, réglages relus sur le module). Noms au format
  `AAAA-MM-JJ_HHMM_7330_smu3300_abp-<mode>-sf<…>-<octets>o-x<répétitions>`.

## Référence : schéma de la mote

*LoRa Mote User's Guide* (Microchip, DS40001808B), annexe A : schémas
(figures A-1 et A-2, pages 22 et 23) et nomenclature (page 24). Le PDF n'est
pas versionné (document Microchip) :
<https://ww1.microchip.com/downloads/en/DeviceDoc/LoRa%20Mote%20Users%20Guide.pdf>.
Les repères de notre carte (U1, U2, L1, D1, R4, C4) correspondent à cette
révision.

## Chaîne d'alimentation de la carte

```
VBUS 5 V ─► U1 MCP1825S-3002 (LDO 3,0 V) ─► D1 (Schottky) ─┐
                                                            ├─► U2 MCP16252 (boost) ─► R4 (0 Ω) ─► rail +3,3 V
Piles 2×AAA / V+ ─► S1 ─► Q1 (coupé si USB présent) ───────┘                              │
                                                                                     C4 (10 µF)
```

- **Les deux sources passent par un convertisseur boost** (U2), y compris
  l'USB. La tension du rail est fixée par le pont R6/R11 à environ 3,31 V.
- **Le rail +3,3 V est commun** : RN2483 (broches 12 et 34), PIC18LF45K50
  (pont USB-UART), LCD et son rétroéclairage, capteurs. Le `+3.3V` de J4 est
  ce même rail. Aucun cavalier ne permet d'isoler le module.
- **Hors du rail** : la LED rouge D2 (environ 7 mA sur le 5 V) et le diviseur
  `USB_DET`.
- **V+ / GND** sont l'entrée piles. Q1 la coupe dès que l'USB est branché :
  inutilisable pour une mesure pendant que la mote est pilotée en USB.

## Choix du point de mesure : R4

R4 est une résistance de 0 Ω (boîtier 0603) entre la sortie du boost et tout
le rail 3,3 V. On la remplace par le PPK2 en série.

Alternatives écartées :

| Point de mesure | Raison du rejet |
|---|---|
| VBUS 5 V (câble USB coupé) | Le courant traverse le LDO, D1 et le boost. Le rendement du boost varie avec la charge (fond de quelques mA contre environ 40 mA en émission) : l'erreur dépend de l'événement, donc du SF, et la soustraction du fond ne l'élimine pas. Seules les durées des phases seraient justes. |
| `+3.3V` / `GND` de J4 | Simple prise sur le rail, pas un point en série. |
| Entrée piles V+ | Coupée par Q1 quand l'USB est branché, donc plus de pilotage. |
| Pistes VDD du RN2483 (broches 12 et 34) | Mesure du module seul, mais modification lourde : solution de repli si la soustraction du fond s'avère trop bruitée. |

**Mode AMP, pas SMU** : C4, le condensateur de sortie du boost, est côté rail.
En mode SMU, le boost tournerait sans condensateur ni charge pendant que l'USB
est branché (risque de pics de tension sur sa sortie). En mode AMP, le boost
reste chargé par C4 et la carte, à travers le PPK2.

## Ce que le banc mesure

| Grandeur | Courant typique du module (fiche technique RN2483, 3,3 V) | Mesurable sur la carte |
|---|---|---|
| Émission, `pwridx 1` (14 dBm) | 38 mA | Oui |
| Réception (RX1, RX2) | 14 mA | Oui |
| Repos (attente entre émission et RX1) | 2,8 mA | Oui |
| Sleep (`sys sleep`) | 1,6 µA | **Non**, noyé dans le fond PIC + LCD : valeur de la fiche technique, à annoncer comme telle |

Énergie d'un événement : E = ∫ (I − I_fond) · V_rail dt, du début de
l'émission à la fin de RX2. I_fond est mesuré module en sleep, rétroéclairage
débranché. V_rail est la tension relevée à l'étape 1.

Contrôles qui justifient la soustraction du fond :

1. **Stabilité du fond** : plusieurs minutes d'enregistrement, module en
   sleep (moyenne et écart-type).
2. **Coût du pont USB-UART** : commande sans radio (`sys get ver`), pour
   chiffrer ce que le seul trafic série coûte au PIC.

Le banc mesure le coût du **module RN2483** par événement. Le microcontrôleur
et l'alimentation d'un vrai nœud sont propres à chaque produit et restent hors
du bilan, comme le Raspberry Pi.

## Procédure

### Matériel

- Fer à panne fine, flux, tresse à dessouder, brucelles, multimètre.
- Deux fils fins (AWG 28–30) d'environ 10 cm, terminés par des broches Dupont.
- Ruban Kapton ou colle chaude.
- Câbles Dupont femelle-femelle : deux pour le PPK2, un comme cavalier.

### Étape 1 : relevés avant modification

1. Photographier la zone de R4 (traçabilité).
2. Mote en USB : mesurer la tension entre `+3.3V` et `GND` de J4 et la noter
   dans le [journal](#journal-des-modifications).
3. Débrancher l'USB et retirer les piles AAA.

### Étape 2 : dessouder R4

1. Flux sur R4.
2. Chauffer les deux extrémités (en alternant, ou avec une goutte d'étain qui
   couvre les deux soudures), puis faire glisser la résistance.
3. Nettoyer les pastilles à la tresse, sans forcer pour ne pas les arracher.
4. Garder R4.

### Étape 3 : identifier les pastilles

Multimètre en continuité, mote débranchée :

- **Côté rail** : bipe avec `+3.3V` de J4.
- **Côté boost** : ne bipe pas (relié à la sortie de U2 et à R6/R11).

Repérer les deux fils en conséquence.

### Étape 4 : souder les fils

1. Étamer les pastilles et les fils, souder en contact bref.
2. Vérifier à la loupe l'absence de pont avec les pastilles voisines.
3. Immobiliser les fils (Kapton ou colle chaude) : aucun effort sur les
   pastilles.

### Étape 5 : contrôles avant mise sous tension

1. Multimètre en résistance, mote débranchée : pas de court-circuit entre
   chaque fil et GND. Côté boost, de l'ordre du MΩ (R6/R11). Côté rail, une
   valeur variable, mais pas 0 Ω.
2. Cavalier entre les deux fils, USB branché : la mote répond à `sys get ver`
   et J4 affiche toujours la tension notée à l'étape 1.

### Étape 6 : brancher le PPK2 en mode AMP

| PPK2 (connecteur P1) | Mote |
|---|---|
| VIN | fil côté **boost** (source) |
| VOUT | fil côté **rail** (charge) |
| GND | `GND` de J4 |

Ordre de mise sous tension :

1. PPK2 relié au PC par son port **USB DATA/POWER**, interrupteur sur ON.
2. nRF Connect for Desktop, application Power Profiler : mode
   **Ampere meter**, sortie activée (*Enable power output*, qui relie VIN à
   VOUT).
3. Brancher l'USB de la mote (`/dev/ttyACM0`).
4. À l'arrêt, dans l'ordre inverse : USB de la mote d'abord, PPK2 ensuite.

> **Règle** : USB de la mote branché ⇒ PPK2 actif en mode AMP, ou cavalier en
> place. Sinon le boost tourne à vide.

### Étape 7 : premier essai

1. Échantillonnage à 100 kS/s.
2. Environ 30 s de fond, avec puis sans le rétroéclairage du LCD (nappe rouge
   et noire). Le rétroéclairage est piloté en PWM par le PIC (`BACKLIGHT`,
   RE2) : on le laisse débranché pour les mesures.
3. Émission radio brute, sans join :

   ```
   mac pause
   radio set sf sf7
   radio set pwr 14
   radio tx 0102030405
   mac resume
   ```

   Attendu : un plateau d'environ 38 mA au-dessus du fond.

Pour la séquence LoRaWAN complète (émission, RX1, RX2), la mote doit avoir
rejoint le réseau. Hors de portée d'une gateway, un join ABP local suffit :
les fenêtres expirent sans réponse, ce qui reproduit une sonde ratée. Régler
alors `rxdelay1` comme sur le terrain.

## Port logique (synchronisation)

Prévu à l'origine pour enregistrer la liaison série (D0 sur `UARTRX`, D1 sur
`UARTTX`, VCC sur le rail de la mote), le port logique sert finalement au
repère posé par le Pi (GPIO17 sur D0, VCC sur le 3,3 V du Pi) : voir le
[montage retenu](#montage-retenu-sans-usb-2-novembre-2026). Alimenter VCC par
le rail mesuré ajouterait la consommation du port logique à la mesure.

## Journal des modifications

Les enregistrements bruts de Power Profiler (`.ppk2`, environ 2 Go par heure à 100 kS/s) ne sont pas versionnés. Ils sont rangés dans le dossier partagé de l'équipe (Google Drive), sous la forme `AAAA-MM-JJ_HHMM_<mote>_<montage>_<contenu>.ppk2` : date et heure de début (heure de Paris), 4 derniers caractères du HWEUI, mode et tension du PPK2, contenu. Le journal cite chaque fichier.

| Date | Opération | Relevé |
|---|---|---|
| 29 octobre 2026 | Tension du rail avant modification (étape 1), mote en USB, multimètre sur `+3.3V` / `GND` de J4 | 3,31 V |
| 29 octobre 2026 | R4 identifiée sur la carte (marquage `000`, entre C4 et U2) ; pastille gauche (vers C4) présumée côté rail, à confirmer à l'étape 3 | — |
| 29 octobre 2026 | Première tentative de dessoudage de R4 : échec, matériel inadapté. R4 toujours en place | Nouvelle tentative le 2 novembre 2026 avec du meilleur matériel |
| 2 novembre 2026 | R4 dessoudée ; flux nettoyé à l'alcool isopropylique | Pastilles intactes, pas de pont avec C4 |
| 2 novembre 2026 | Continuité (étape 3), mote débranchée | Pastille gauche ↔ droite : ouvert. Gauche ↔ `+3.3V` de J4 : continuité (côté rail confirmé). Gauche ↔ `GND` : pas de court-circuit |
| 2 novembre 2026 | Tentative de soudure de fils sur les pastilles de R4 (étape 4) : échec, pastilles trop petites | Montage sur R4 abandonné |
| 2 novembre 2026 | Choix du [montage sans USB](#montage-retenu-sans-usb-2-novembre-2026), vérifié sur le schéma | — |
| 4 novembre 2026 | Barrettes mâles enfichées dans J4 et J2, **non soudées** (pas de fer ni de multimètre ce jour) | Mote à ne pas alimenter avant soudure et tests |
| 4 novembre 2026 | nRF Connect for Desktop installé (avec SEGGER J-Link V9.82) ; Power Profiler v4.4.1 reconnaît le PPK2 | N° de série PPK2 : `EB86C5E77852` |
| 4 novembre 2026 | Essai à vide du PPK2 : mode Source meter, 3300 mV, rien de branché, 100 kS/s pendant 10 s | Moyenne 52,8 nA, max 0,56 µA (plancher de mesure du PPK2) |
| 4 novembre 2026 | Essai sur résistance (marron-noir-orange-doré, 10 kΩ ±5 %) entre VOUT et GND : Source meter, 3300 mV, 100 kS/s pendant 10 s | Moyenne 330,83 µA, max 335,12 µA, bruit crête à crête d'environ 6 µA ; R déduite 9,97 kΩ, conforme |
| 5 novembre 2026 | Barrettes mâles soudées dans J4 (12 broches) et J2 (6 broches) | — |
| 5 novembre 2026 | Tests de continuité, mote débranchée : J2 broche 3 ↔ J4 `GND` ; J2 broche 2 ↔ J4 `+3.3V` ; J4 `+3.3V` ↔ `GND` ; J2 broche 1 ↔ broche 3 | Continuité ; continuité (sens de J2 confirmé) ; ouvert (bip bref de charge de C4) ; ouvert |
| 5 novembre 2026 | Première mise sous tension de la mote par le PPK2 (sans Pi) : Source meter 3300 mV, 100 kS/s, cavalier J2 broche 1 ↔ 3, câble du rétroéclairage débranché (nappe de l'écran en place), antenne vissée, ni USB ni piles ; sortie active 34 s. Fichier `2026-11-05_1621_7330_smu3300_demarrage-reset.ppk2` (36,3 s) | Pas de court-circuit. Démarrage : pic d'appel de 96 mA, environ 7,4 mA pendant environ 0,2 s, salves à 22 mA et 15 mA, puis fond stable de 4,4 à 4,5 mA |
| 5 novembre 2026 | Un événement isolé vers 17 s après la mise sous tension | Même signature que le démarrage (creux bref vers 3,6 mA, pic à 45 mA, paliers vers 10 et 12,5 mA, salves à 22 et 15 mA, environ 0,25 s) : reset probable du RN2483 (grille flottante de Q4, ou contact du cavalier J2), à confirmer par la liaison série |
| 5 novembre 2026 | Enregistrement de 6 min 53 s (début à 16:33:48) sans manipulation, même montage (cavalier J2 vérifié). Fichier `2026-11-05_1633_7330_smu3300_fond-7min.ppk2` | Aucun événement hors du démarrage. Fond : 4,38 mA en moyenne sur une fenêtre de 2,6 s, de 4,2 à 4,53 mA |
| 5 novembre 2026 | Raspberry Pi du banc identifié par SSH (Ethernet, adresse DHCP 192.168.1.212) | Raspberry Pi 5 Model B Rev 1.0, nom `pi-ppk2`, Debian 13 (Trixie), noyau 6.18.50+rpt-rpi-2712, MAC `2c:cf:67:97:8a:b0`. `/dev/serial0` pointe sur `ttyAMA10` (connecteur de débogage, console système), pas sur GPIO14/15 |
| 5 novembre 2026 | Réseau de `pi-ppk2` : Wi-Fi du bureau géré par NetworkManager (profil netplan, connexion automatique), Tailscale installé | `tailscaled` activé au démarrage, connecté (100.126.54.98, Tailscale SSH actif) ; SSH vérifié par Tailscale. Redémarrage du 5 novembre 2026 à 17:20 : Tailscale et Wi-Fi revenus seuls, SSH par `pi-ppk2` en 10 s environ |
| 5 novembre 2026 | Port série du Raspberry Pi configuré : `dtparam=uart0=on` ajouté à `/boot/firmware/config.txt`, redémarrage | `/dev/ttyAMA0` présent (groupe `dialout`), GPIO14 = TXD0 et GPIO15 = RXD0 (`pinctrl`). `/dev/serial0` reste sur `ttyAMA10` (console de débogage) |
| 5 novembre 2026 | Logiciel de `pi-ppk2` : uv 0.13.7 (sans sudo), git 2.47.3, dépôt cloné dans `~/DMX-LoRa-Exp-1` (commit `826d607`), `uv sync` dans `Mote/` | Python 3.14.10, pyserial 3.5 (mêmes versions que les Pi de terrain) |
| 9 novembre 2026 | Câblage Pi ↔ J4, masses communes sur une breadboard (J4 `GND`, Pi broche 6, PPK2 GND). Premier essai : erreurs de câblage (un fil oublié, deux inversés) | Bruit permanent sur le RX du Pi, environ 2 000 octets/s sans commande |
| 9 novembre 2026 | Câblage corrigé et vérifié au multimètre, PPK2 coupé et TX du Pi débranché : Pi broche 6 ↔ J4 `GND`, Pi broche 10 ↔ `UARTTX`, fil de la broche 8 ↔ `UARTRX`, Pi broche 10 ↔ `UARTRX` | Continuité ×3, ouvert (conforme) |
| 9 novembre 2026 | Mise sous tension avec le TX du Pi débranché, écoute de 120 s sur `/dev/ttyAMA0` | Pas de chaîne de version au démarrage ; ligne TX du module tenue au niveau haut (vérifié avec un rappel vers le bas côté Pi), donc module actif |
| 9 novembre 2026 | TX du Pi rebranché ; 10 × `sys get ver` | Aucune réponse, aucune variation visible du courant (fond 4,3 mA) |
| 9 novembre 2026 | *Break* puis `0x55` (détection automatique de vitesse du RN2483), puis `sys get ver` et `sys reset` | `RN2483 1.0.6 RC3 May 18 2021 18:35:00` aux deux. Cause probable : entrée série du module flottante quand le TX du Pi est débranché, prise pour un *break*. Règles : resynchroniser après chaque mise sous tension, garder le TX du Pi branché |
| 9 novembre 2026 | Lecture de la configuration | HWEUI = DevEUI `0004A30B00FD7330` (mote de test), AppEUI `0000000000000000`, `sys get vdd` 3233 mV (PPK2 réglé à 3300 mV), DR 0, `pwridx` 1, ADR off, `rxdelay1` 1000 ms, RX2 DR0 869,525 MHz, `retx` 7, statut `00000000` (non joint, après `sys reset`) |

| 9 novembre 2026 | Première émission mesurée, depuis le Pi : `mac pause`, `radio set` mod lora, 868,1 MHz, SF7, BW 125 kHz, CR 4/5, préambule 8, CRC on, sync 34, `pwr 14`, puis `radio tx 0102030405` (5 octets) à 15:16:04.760 ; `radio_tx_ok` 42 ms après la commande. Acquisition PPK2 Source meter 3300 mV, 100 kS/s, démarrée vers 15:15:17 | Plateau d'émission sélectionné : 31,96 ms (temps d'émission théorique 30,98 ms), moyenne 43,02 mA, max 44,71 mA, charge 1,38 mC ; plateau vers 44,2 mA, soit environ 39,9 mA au-dessus du fond de 4,3 mA (fiche technique : 38,0 mA). Énergie de l'émission au-dessus du fond : (1,38 mC − 4,3 mA × 31,96 ms) × 3,3 V ≈ 4,10 mJ (fiche technique : 3,88 mJ) Fichier `2026-11-09_1515_7330_smu3300_radiotx-sf7-5o.ppk2` (début 15:15:18, 62,8 s). Recalculée au-dessus du fond module en sleep (1,38 mA, ligne suivante) : 4,41 mJ |
| 9 novembre 2026 | Fond de la carte, module en sleep : `sys sleep 20000` envoyé à 15:31:49.8, réveil (`ok`) à 15:32:09.8, puis resynchronisation (*break* + `0x55`) nécessaire. Fichier `2026-11-09_1531_7330_smu3300_fond-sleep20s.ppk2` (début 15:31:37, 46,9 s) | Sélection de 19,52 s dans le palier : moyenne 1,38 mA, max 4,25 mA, charge 26,85 mC. Chute nette de 4,3 à environ 1,35 mA à l'endormissement, sans transitoire. Neuf impulsions brèves vers 4,2 mA, environ toutes les 2 s, pendant le sommeil (réveils internes probables du module, à caractériser). Courant du module au repos déduit : 4,3 − 1,38 ≈ 2,9 mA (fiche technique : 2,8 mA). **Fond de référence pour l'énergie des événements : carte avec module en sleep, 1,38 mA** ; soustraire le fond « module au repos » (4,3 mA) effacerait les attentes avant RX1 et RX2 |
| 9 novembre 2026 | Premier message LoRaWAN complet, join ABP local (session factice : DevAddr `01ABCDEF`, clés factices, sans `mac save`), ADR off, DR5 (SF7), `pwridx` 1, `rxdelay1` 1000 ms, `rxdelay2` 2000 ms, RX2 DR0 869,525 MHz. `mac tx uncnf 1 0102030405AA` (6 octets) à 15:36:42.215, `ok` à .262, `mac_tx_ok` à 15:36:44.547 (2,33 s après la commande) ; puis `sys sleep 10000`. Fichier `2026-11-09_1536_7330_smu3300_abp-uncnf-sf7-6o.ppk2` (début 15:36:19, 129,6 s) | Émission : sélection de 57,98 ms (temps d'émission théorique 51,5 ms pour 19 octets), moyenne 39,83 mA, max 44,71 mA, charge 2,31 mC. RX1 (SF7) : 22,01 ms, moyenne 13,87 mA, charge 305,32 µC. RX2 (SF12) : 266,5 ms, moyenne 15,28 mA (plateau vers 15,3 mA), charge 4,07 mC. Estimation au-dessus du fond module en sleep (1,38 mA), à 3,3 V, sur environ 2,318 s : émission 7,4 mJ, RX1 0,9 mJ, RX2 12,2 mJ, attentes au repos (1,97 s à 2,92 mA) 19,0 mJ, **total ≈ 39,5 mJ**. Confirmé par une sélection directe du début de l'émission à la fin de RX2 : 2,304 s, moyenne 6,54 mA, charge 15,08 mC, soit (15,08 − 1,38 × 2,304) mC × 3,3 V = **39,3 mJ** (émission ≈ 19 %, attentes au repos ≈ 48 %, RX2 ≈ 31 %, RX1 ≈ 2 %). Mesure unique, sans répétition |
| 9 novembre 2026 | PPK2 déplacé en USB sur `pi-ppk2` ; l'ancienne alimentation du Pi ne tient pas l'appel de courant (Pi figé, hors ligne), remplacée | Après remplacement : 5,07 V, `throttled=0x0`. PPK2 vu en USB 12 Mbit/s (`1915:c00a`, n° `EB86C5E77852`), port de commande `/dev/serial/by-id/usb-Nordic_Semiconductor_PPK2_EB86C5E77852-if01`. `ppk2-api` 0.9.2 ajouté au projet (commit `467c8a3`) |
| 9 novembre 2026 | Pilotage du PPK2 par `ppk2-api` depuis le Pi | **Le PPK2 coupe sa sortie quand le programme qui le pilote ferme son port** : entre deux scripts, la mote n'est alimentée que par le TX du Pi (module muet, courant faussé à environ 2,4 mA). Parade : GPIO14 en entrée (`pinctrl set 14 ip pn`) tant que la mote n'est pas alimentée. PPK2 ouvert et sortie active : `sys get vdd` 3233 mV, repos 4,61 mA |
| 9 novembre 2026 | Débit du flux PPK2 sur le Pi : trois méthodes de lecture (pyserial avec pauses, pyserial bloquant, `os.read`), puis repère GPIO17 (Pi broche 11) → PPK2 D0, VCC logique sur le 3,3 V du Pi (broche 1), GND broche 9, basculé toutes les secondes | 81 000 à 84 000 éch./s au lieu de 100 000 ; entre deux repères espacés d'une seconde : 83 100 à 83 900 échantillons (une fois 91 290). **Environ 16 % des échantillons perdus sur le Pi** ; Power Profiler sous Windows reçoit bien 100 kS/s (durée du message conforme à la théorie). Acquisition par le Pi inutilisable en l'état ; les 12 repères sont tous vus sur D0 |
| 9 novembre 2026 | Même test de repères après changement de port USB du Pi, puis après redémarrage du Pi | Inchangé : 82 600 à 83 600 échantillons par seconde de repère (premier intervalle vers 91 000‒92 800). Les écarts vont par pas d'environ 500 échantillons (2 Ko) : des blocs USB entiers sont perdus. Décision : PPK2 rebranché sur le PC Windows, acquisition par `ppk2-api` en Python natif à valider avec ce même test ; le Pi garde le pilotage de la mote et les repères sur D0. Au démarrage du Pi, GPIO14 repasse en TXD0 (niveau haut) : TX à débrancher ou à remettre en entrée si la mote n'est pas alimentée |
| 9 novembre 2026 | PPK2 rebranché sur le PC Windows (ports COM7 pour les commandes, COM10) ; acquisition par `ppk2-api` 0.9.2 et pyserial 3.5 en Python 3.14 natif (`uv run --no-project`), repères du Pi sur D0 toutes les secondes (12 fronts), 18 s | **100 039 éch./s en moyenne ; 99 983 à 100 009 échantillons entre deux repères** (écart ≤ 0,02 %, de l'ordre de la gigue de `pinctrl`), 12 fronts sur 12 vus. Aucune perte : acquisition retenue sur le PC Windows, pilotage de la mote et repères par le Pi |
| 9 novembre 2026 | Fin de journée : PPK2 débranché du PC (sortie déjà coupée), fils de la broche 8 (TX) et de la broche 1 (3,3 V, VCC logique) du Pi débranchés ; reste du câblage en place (D0 ← GPIO17, GND, RX ← `UARTTX`, PPK2 VOUT/GND → J4) | Banc laissé monté au bureau |
| 10 novembre 2026 | Câblage rebranché (PPK2 sur le PC, Pi broches 1 et 8) ; GPIO14 resté en entrée. Premiers scripts du banc automatique : `ppk2_record.py` (Windows), `banc_pi.py` (Pi), `banc_ppk2.py` (WSL). Série de validation : 3 × `mac tx uncnf` SF7, 6 octets, ABP local, sommeil de 4 s avant chaque message. Fichiers `2026-11-10_1006_7330_smu3300_abp-uncnf-sf7-6o-x3-validation.*` | Intégrité : 99 985 éch./s d'horloge ; écart entre repères successifs 0 ou −1 échantillon ; durée entre repère haut et bas supérieure de 1,8 à 1,9 ms à l'horloge du Pi (latence de `pinctrl`, systématique). Tentatives 1 et 3 : 38,47 et 38,59 mJ, 2 284 ms, émission 51,5 ms, RX1 19,2 ms, RX2 264 ms, fond sleep 1,40 à 1,46 mA, repos 4,35 mA ; cohérent avec Power Profiler (39,3 mJ sur une sélection manuelle de 2 304 ms). **Tentative 2 : RX2 de 558 ms et 52,43 mJ** : la fenêtre RX2 est restée ouverte deux fois plus longtemps, probablement sur la détection d'un préambule (autre réseau émettant sur 869,525 MHz). Effet réel à garder et à quantifier sur les séries répétées |
| 10 novembre 2026 | Constat : `pi-ppk2` a redémarré à 10:11 (arrêt manuel pour changer son câble d'alimentation, aucun fil débranché), après la série de validation ; GPIO14 repassé en TXD0 au démarrage, fil TX branché, mote non alimentée | Mote alimentée par la ligne série du Pi pendant environ 3 h 45 (jusqu'à 13:57). GPIO14 remis en entrée ; service `ppk2-tx-input.service` ajouté pour le faire à chaque démarrage. État du module à vérifier au début de la série suivante |
| 10 novembre 2026 | `ppk2-tx-input.service` lié et activé sur `pi-ppk2` | `enabled`, exécution réussie, GPIO14 en entrée ; `throttled=0x0` |
| 10 novembre 2026 | **Série de référence** : 30 × `mac tx uncnf` par SF, SF7 à SF12, 6 octets, ABP local, `pwridx` 1, `rxdelay1` 1000 ms, RX2 SF12, sommeil avant chaque message au moins égal au repos du duty cycle ; de 14:01 à 16:29. Fichiers `2026-11-10_1401_7330_smu3300_abp-uncnf-sf7-sf8-sf9-sf10-sf11-sf12-6o-x30.*` (3,5 Go de courant) | Module sain au départ (version, 3233 mV). 180 tentatives, 180 `mac_tx_ok` du premier coup, aucun `no_free_ch`, aucun redémarrage ; 888 637 440 échantillons, 99 999 éch./s d'horloge. Analyse interrompue par un faux repère (D0 lu haut au début de l'enregistrement, avant que le Pi ne pilote GPIO17) ; journal détaillé du Pi perdu (non sauvegardé avant l'analyse). Corrigé dans `banc_ppk2.py` : niveau initial de D0 ignoré, journal du Pi enregistré au fil de l'eau (`.pi.jsonl`), option `--reanalyse`. Ré-analyse sans les instants du Pi : fenêtre de fond placée d'après la séquence de `banc_pi.py`, intégrité contrôlée par l'écart entre repères comparé à la médiane du même SF (au plus 56 échantillons). **Énergie par message au-dessus du fond sleep (moyenne ± écart-type, n = 30)** : SF7 38,77 ± 0,06 mJ ; SF8 45,97 ± 0,08 ; SF9 57,95 ± 0,13 ; SF10 80,15 ± 0,08 ; SF11 137,90 ± 0,25 ; SF12 220,41 ± 0,40. Émission 51,5 / 102,9 / 185,3 / 329,7 / 741,4 / 1 318,9 ms (identique au calcul théorique) ; RX1 19 / 28 / 47 / 117 / 165 / 264 ms ; RX2 263 à 264 ms ; durée du message 2 284 à 3 551 ms ; fond 1,377 à 1,379 mA, repos 4,29 mA. Aucune fenêtre RX2 allongée sur 180 messages (une sur trois lors de la validation du matin) |
| 10 novembre 2026 | Fin de journée : série `1401` ré-analysée avec le code commité (`181d90e`, résultats identiques) ; CSV et JSON des séries de validation et de référence versionnés dans [`banc-ppk2/`](banc-ppk2/README.md). Échantillons bruts (4,4 Go) sur le PC du banc, `C:\Users\<utilisateur>\banc-ppk2\data\`, à copier sur le Drive. Fils TX et VCC logique laissés en place : GPIO14 reste en entrée hors des séries (service au démarrage) | Reste à mesurer : sonde ratée (`mac tx cnf`, `retx` 0, SF7 à SF9), autres tailles de charge utile (20 et 51 octets), sonde réussie (OTAA, à l'IRIT) |
| 10 novembre 2026 | Copie des échantillons bruts et des résultats du dossier de données du PC vers le dossier partagé de l'équipe (Google Drive), sous-dossier `banc-automatique` (`robocopy`, 10 fichiers) | Tailles identiques à la source, environ 4,4 Go |
| 12 novembre 2026 | **Sonde ratée** : 30 × `mac tx cnf` (`retx` 0, ABP local, aucun ACK possible) par SF, SF7 à SF9, 6 octets, RX2 SF12. Fichiers `2026-11-12_1007_7330_smu3300_abp-cnf-sf7-sf8-sf9-6o-x30.*` | Module sain (3233 mV). 90 tentatives, toutes `mac_err`, aucun `no_free_ch`, aucun redémarrage ; 99 987 éch./s ; écart entre repères au plus 8 échantillons (instants du Pi enregistrés). **SF7 38,76 ± 0,06 mJ ; SF8 46,12 ± 0,02 ; SF9 58,12 ± 0,03** : identique à l'uplink non confirmé (0,0 à +0,3 %), mêmes fenêtres (RX1 20 / 28 / 47 ms, RX2 264 ms). Défaut de traçabilité : `git` et `sha256` du JSON relevés en fin de série, après modification des scripts en cours de série ; code réellement exécuté : commit `181d90e`. Corrigé (provenance relevée au lancement) |
| 12 novembre 2026 | **Levier RX2** : option `--rx2-dr` ajoutée (commit `c4e3b98`) ; 30 × `mac tx cnf` SF7 avec RX2 en SF9 (`mac set rx2 3 869525000`). Fichiers `2026-11-12_1030_7330_smu3300_abp-cnf-sf7-6o-x30-rx2dr3.*` | **28,99 ± 0,04 mJ** (contre 38,76 avec RX2 en SF12 : −9,8 mJ, −25 %) ; RX2 de 46 ms au lieu de 264 ms ; durée 2 094 ms ; toutes `mac_err`, aucun rejet |
| 12 novembre 2026 | **`rx1_delay` à 3 s** : 30 × `mac tx cnf` SF7 (sonde ratée), `--rxdelay1 3000` (RX2 à 4 s), RX2 SF12, 6 octets. Fichiers `2026-11-12_1049_7330_smu3300_abp-cnf-sf7-6o-x30-rxd3000.*` | **57,90 ± 0,13 mJ**, durée 4 284 ms (contre 38,76 mJ et 2 284 ms à 1 s) : **+19,1 mJ (+49 %)** pour 2 s d'attente au repos en plus, conforme à l'estimation. Une sonde SF7 coûterait alors autant qu'un uplink SF9 avec `rx1_delay` à 1 s. Toutes `mac_err`, aucun rejet |
| 12 novembre 2026 | **Sondes ratées en 20 et 51 octets** : 30 × `mac tx cnf` par SF, SF7 à SF9, RX2 SF12, `rx1_delay` 1 s. Fichiers `2026-11-12_1054_7330_smu3300_abp-cnf-sf7-sf8-sf9-20o-x30.*` et `2026-11-12_1122_7330_smu3300_abp-cnf-sf7-sf8-sf9-51o-x30.*` | Toutes `mac_err`, aucun rejet, écart entre repères au plus 16 échantillons. Moyennes : 20 octets 41,57 / 50,49 / 66,48 mJ ; 51 octets 47,85 / 61,46 / 87,60 mJ (SF7 / SF8 / SF9). Deux fenêtres RX2 allongées : tentative 43 (SF8, 20 octets) RX2 371 ms, 55,27 mJ ; tentative 83 (SF9, 51 octets) RX2 1 282 ms, 133,34 mJ. Avec la validation du 10 novembre : 3 messages sur 543 |
| 12 novembre 2026 | **Repli avec RX2 en SF9** : 30 × `mac tx uncnf` par SF, SF10 à SF12, 6 octets, `--rx2-dr 3`, de 12:40 à 14:50. Fichiers `2026-11-12_1240_7330_smu3300_abp-uncnf-sf10-sf11-sf12-6o-x30-rx2dr3.*` | 90 `mac_tx_ok`, aucun rejet, aucune fenêtre RX2 allongée ; écart entre repères au plus 114 échantillons. **SF10 70,51 ± 0,11 ; SF11 128,83 ± 0,32 ; SF12 211,46 ± 0,41 mJ**, soit −9,6 / −9,0 / −8,9 mJ par rapport à RX2 en SF12 (RX2 de 46 à 47 ms). Seuils mesurés avec la sonde SF7 à 28,99 mJ : p* = 0,41 / 0,22 / 0,14, conformes à l'estimation |
| 12 novembre 2026 | **Repli en 20 octets, premier fragment** : 30 × `mac tx uncnf` par SF, SF10 et SF11, RX2 SF12, de 14:53 à 16:15. SF12 en 20 octets et série de 51 octets à faire plus tard (série fragmentée par SF, faute de créneau de 3 h). Fichiers `2026-11-12_1453_7330_smu3300_abp-uncnf-sf10-sf11-20o-x30.*` | 60 `mac_tx_ok`, aucun rejet, écart entre repères au plus 42 échantillons. **SF10 97,42 ± 1,56 mJ (médiane 97,14) ; SF11 172,28 ± 0,28 mJ**, soit +17,0 et +34,4 mJ par rapport à 6 octets ; émission 452,6 et 987,1 ms. Une fenêtre RX2 allongée (tentative 15, SF10 : 449 ms, 105,65 mJ) : 4 sur 603 messages depuis le 10 novembre |
| 12 novembre 2026 | **Repli en 51 octets, premier fragment** : 30 × `mac tx uncnf`, SF10, RX2 SF12, de 16:18 à 16:55. Fichiers `2026-11-12_1618_7330_smu3300_abp-uncnf-sf10-51o-x30.*` | 30 `mac_tx_ok`, aucun rejet, aucune fenêtre RX2 allongée, écart entre repères au plus 36 échantillons. **SF10 130,65 ± 0,23 mJ** (+50,5 mJ par rapport à 6 octets), émission 698,4 ms. Restent : SF12 en 20 octets, SF11 et SF12 en 51 octets |
| 13 novembre 2026 | Idée : couper le duty cycle dans la chambre anéchoïque blindée du bureau (banc complet à l'intérieur, PC compris ; Pi joignable par Tailscale), les séries à SF élevé passant 97 % du temps à attendre. Option `--no-duty-cycle` ajoutée (commit `a6cff48`) ; `mac set dcycleps 1` refusé par le firmware 1.0.6 (`invalid_param`, premier essai `2026-11-13_1035_…`, aucune émission), retiré (commit `00a3697`) | Canaux 0 à 2 relus à 0 (100 %), `dcycleps` relu à 1 |
| 13 novembre 2026 | **Contrôle de méthode** dans la chambre, sans duty cycle : 30 × `mac tx uncnf` SF12, 6 octets, sommeil 6 s. Fichiers `2026-11-13_1036_7330_smu3300_abp-uncnf-sf12-6o-x30-nodc-controle.*` | Médiane 219,41 mJ contre 220,48 mJ en référence (−0,5 %) ; courant d'émission 42,44 mA contre 42,67 mA, sans dérive au fil de la série ; durées et fond identiques ; `sys get vdd` 3223 mV (3233 d'habitude). 1er message aberrant : 229,02 mJ, 44,76 mA en émission (effet de première émission après mise sous tension). **Décision** : séries de résultats au bureau, sous duty cycle, pour l'homogénéité ; méthode validée pour une campagne future (écart à annoncer) |
| 13 novembre 2026 | Option `--warmup` (message de chauffe exclu des statistiques, commit `1584753`). Premier lancement des trois fragments restants à 11:14 : plantage au message de chauffe (numéro de répétition négatif, `OverflowError`), aucune mesure ; processus orphelins (script du Pi, enregistreur Windows) arrêtés à la main ; corrigé (commit `a0d3584`), relancé à 11:23 | — |
| 13 novembre 2026 | **Repli SF12, 20 octets** : 30 × `mac tx uncnf` + 1 de chauffe, RX2 SF12, de 11:23 à 13:00. Fichiers `2026-11-13_1123_7330_smu3300_abp-uncnf-sf12-20o-x30.*` | **286,81 ± 0,28 mJ** (+66,4 mJ par rapport à 6 octets), émission 1 810 ms, aucune fenêtre RX2 allongée, écart entre repères au plus 120 échantillons. Chauffe : 286,51 mJ, **pas d'anomalie de premier message au bureau** (contrairement au contrôle en chambre). Courant d'émission stable du premier au dernier message |
| 13 novembre 2026 | **Repli SF11, 51 octets** : 30 × `mac tx uncnf` + 1 de chauffe, de 13:00 à 14:25. Fichiers `2026-11-13_1300_7330_smu3300_abp-uncnf-sf11-51o-x30.*` | 248,05 ± 2,58 mJ (médiane 248,72). **Saut de conditions** : courant d'émission de 42,6 mA pour les tentatives 1 à 28, puis 40,9 mA (−4 %) pour les tentatives 29 à 31 (vers 14:15), soit environ 240,6 mJ au lieu de 248 à 250 ; durées, fenêtres, fond et intégrité inchangés. Cause probable : objet métallique posé près de l'antenne vers 14:15 (souvenir incertain). Effet de l'environnement de l'antenne sur le courant de l'amplificateur, à quantifier par un test dédié. Les tentatives 29 à 31 sont mesurées dans une autre condition |
| 13 novembre 2026 | **Repli SF12, 51 octets, premier essai** (`2026-11-13_1425_…`), arrêté à la tentative 9 : courant d'émission de 40,9 mA (tentatives 1 à 7, objet probablement encore présent), puis 42,0 mA (tentatives 8 et 9). Conditions mélangées : échantillons bruts conservés, série non analysée et exclue des résultats. Environnement de l'antenne dégagé, fragment relancé | — |
| 13 novembre 2026 | Second essai SF12 en 51 octets (`2026-11-13_1516_…`) après avoir « dégagé l'environnement » : courant d'émission de 43,7 mA (+2,3 %) dès les premiers messages, l'antenne ayant été redressée (elle était à plat depuis le 10 novembre). Arrêté après 3 messages, exclu des résultats. Option `i_tx_ma` et `--i-tx-ref` ajoutées (commit `ea2874a`) | — |
| 13 novembre 2026 | **Test de sensibilité à l'environnement de l'antenne** : 11 conditions de 10 × `mac tx uncnf` SF7, 6 octets, + 1 de chauffe, de 15:41 à 16:37. Fichiers `2026-11-13_*_sensib-*` | Courant d'émission de 36,14 mA (mote debout adossée à la gourde, −13,9 %) à 45,01 mA (mote debout seule, +7,2 %) autour de 41,99 mA (à plat) ; antenne verticale +3,9 %, dévissée d'un demi-tour +1,8 %, gourde ou pince à côté ou au contact de l'antenne : 0 à 0,2 % ; retour à la référence à −0,3 %. Énergie SF7 de 37,55 à 39,10 mJ. Détail dans le README des résultats. Fragilité du montage (fils, soudures) signalée par l'utilisateur |
| 13 novembre 2026 | **Émission manquante** (condition 9, tentative 5) : `mac_tx_ok` et fenêtres RX1/RX2 normales, mais aucune émission (courant au repos, pointe de 2 ms) ; 1 cas sur 884 messages. Fenêtre RX2 allongée de 1 395 ms avec `mac_err` sur la chauffe de la condition 8 (5 cas sur 884) | Fragment SF12 en 51 octets à refaire un autre jour, montage à plat, `--i-tx-ref` au démarrage |
| 13 novembre 2026 | Information terrain : les antennes des motes déployées sont verticales, alors que toutes les mesures du banc sont faites mote et antenne à plat. Décision : pas de correction plat → vertical (la sensibilité mesurée dépend de la position précise de la mote, pas seulement de l'orientation de l'antenne), mais une incertitude liée à l'emplacement : environ −2,5 % / +1,2 % sur une sonde SF7, −11 % / +6 % sur un repli SF12, p* de 0,17 à 0,19 pour un repli en SF12. Mesures restantes dans la même position qu'avant (à plat), courant d'émission contrôlé au démarrage | — |
| 13 novembre 2026 | Profil Wi-Fi `eduroam` ajouté sur `pi-ppk2` en vue des mesures à l'IRIT, sans l'activer (pas d'eduroam au bureau, une seule interface Wi-Fi) : mêmes réglages que les Pi de terrain (PEAP/MSCHAPv2, certificat de l'INP Toulouse, contrôle du serveur `eduroam.inp-toulouse.fr`), connexion automatique | Certificat `CN=rootCA.eduroam.inpt`, empreinte SHA-256 conforme (`…4A:8B:56:4A`), valide jusqu'en 2034 ; mot de passe enregistré ; le Pi reste connecté au Wi-Fi du bureau |
