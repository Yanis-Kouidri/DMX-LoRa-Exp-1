# Banc de mesure d'énergie (PPK2)

Montage du Nordic Power Profiler Kit II (PPK2) sur la
[mote de test](mote.md#mote-de-test-0004a30b00fd7330) `0004A30B00FD7330`,
pour mesurer le coût énergétique de chaque événement LoRaWAN (principe et
événements à mesurer : [section 9 du plan](../docs/plan-experimental.md#9-modèle-énergétique-et-banc-ppk2)).

> Procédure définie le 29 octobre 2026 à partir du schéma de la carte. La
> modification de la mote n'est pas encore faite : le
> [journal](#journal-des-modifications) est à compléter au fur et à mesure.

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

Le port logique du PPK2 enregistre la liaison série sur la même échelle de
temps que le courant, ce qui permet de découper les traces par événement :

| PPK2 (port logique) | Mote (J4) |
|---|---|
| D0 | `UARTRX` (commandes vers le RN2483) |
| D1 | `UARTTX` (réponses du RN2483) |
| VCC | `+3.3V` (référence de niveau) |
| GND | `GND` |

## Journal des modifications

| Date | Opération | Relevé |
|---|---|---|
| 29 octobre 2026 | Tension du rail avant modification (étape 1), mote en USB, multimètre sur `+3.3V` / `GND` de J4 | 3,31 V |
| 29 octobre 2026 | R4 identifiée sur la carte (marquage `000`, entre C4 et U2) ; pastille gauche (vers C4) présumée côté rail, à confirmer à l'étape 3 | — |
| 29 octobre 2026 | Première tentative de dessoudage de R4 : échec, matériel inadapté. R4 toujours en place | Nouvelle tentative le 2 novembre 2026 avec du meilleur matériel |
| | R4 dessoudée, fils soudés | |
| | Contrôles de l'étape 5 | |
| | Premier essai PPK2 (étape 7) | |
