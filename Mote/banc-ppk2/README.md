# Résultats du banc PPK2

Résultats des séries de mesure du [banc PPK2](../banc-ppk2.md) sur la mote de
test `0004A30B00FD7330`. Un fichier CSV par série (une ligne par tentative) et
un JSON de métadonnées, écrits par `src/banc_ppk2.py`.

Les échantillons bruts (`.cur.f32`, courant en µA ; `.dig.u8`, voies logiques ;
100 kS/s) ne sont pas versionnés : plusieurs gigaoctets par série. Ils sont sur
le PC du banc, dans `C:\Users\<utilisateur>\banc-ppk2\data\`, et copiés sous le
même nom dans le dossier partagé de l'équipe (Google Drive), sous-dossier
`banc-automatique`. La série `2026-11-10_1005_…-validation` n'y a que ses
échantillons bruts : son analyse s'était arrêtée sur une erreur, la série a été
refaite à 10:06.

## Tableau de bord Grafana

Depuis le 13 novembre 2026, les résultats sont aussi affichés sur
https://grafana.chirpstack.kouidri.fr/d/banc-ppk2 (énergie selon le SF et la
taille, durées, effets de RX2 et de `rx1_delay`, seuil de rentabilité p*,
répétabilité, tableau des séries). Les fichiers de ce dossier font foi : la
base du serveur n'en est qu'une copie, sans les échantillons bruts, et les
figures du papier ne viendront pas de Grafana.

Une série n'apparaît qu'après avoir été commitée, poussée, puis chargée sur le
serveur (`ssh chirpstack-aws`, dans `~/DMX-LoRa-Exp-1/LoRaWAN-Infra`) :

```sh
git pull --ff-only
docker compose --profile jobs run --rm banc-ppk2-chargement
```

Le chargement classe hors résultats les séries lancées avec `--no-duty-cycle`
ou dont le libellé contient `validation` ; elles ne figurent que dans le
tableau des séries. Les tentatives marquées `valid` dans le CSV sont toutes
comptées : pour en écarter, il faut le faire dans l'analyse, pas dans Grafana.
Détail des tables et des panneaux dans
[`LoRaWAN-Infra/README.md`](../../LoRaWAN-Infra/README.md#résultats-du-banc-ppk2).

## Séries

| Série | Contenu | Acquisition | Analyse |
|---|---|---|---|
| `2026-11-10_1006_…-x3-validation` | 3 × `mac tx uncnf` SF7, 6 octets | dépôt au commit `082bf32` (scripts non encore commités) | même exécution |
| `2026-11-10_1401_…-x30` | 30 × `mac tx uncnf` par SF, SF7 à SF12, 6 octets | dépôt au commit `71a2f38` | `--reanalyse` au commit `181d90e` |
| `2026-11-12_1007_…-cnf-sf7-sf8-sf9-6o-x30` | 30 sondes ratées par SF (`mac tx cnf`, `retx` 0, aucun ACK), SF7 à SF9, 6 octets | code du commit `181d90e` (`banc_pi.py` : empreinte `89470225f7ed8ef4`) | même exécution, code du commit `181d90e` |
| `2026-11-12_1030_…-cnf-sf7-6o-x30-rx2dr3` | 30 sondes ratées SF7, RX2 en SF9 (DR3) | commit `c4e3b98` | même exécution |
| `2026-11-12_1049_…-cnf-sf7-6o-x30-rxd3000` | 30 sondes ratées SF7, `rx1_delay` 3 s | commit `a3ed546` (champ `acquisition`) | même exécution |
| `2026-11-12_1054_…-cnf-sf7-sf8-sf9-20o-x30` | 30 sondes ratées par SF, SF7 à SF9, 20 octets | commit `a3ed546` | même exécution |
| `2026-11-12_1122_…-cnf-sf7-sf8-sf9-51o-x30` | 30 sondes ratées par SF, SF7 à SF9, 51 octets | commit `a3ed546` | même exécution |
| `2026-11-12_1240_…-uncnf-sf10-sf11-sf12-6o-x30-rx2dr3` | 30 × `mac tx uncnf` par SF, SF10 à SF12, 6 octets, RX2 en SF9 | commit `7d1cb9e` | même exécution |
| `2026-11-12_1453_…-uncnf-sf10-sf11-20o-x30` | 30 × `mac tx uncnf` par SF, SF10 et SF11, 20 octets (premier fragment de la série de repli en 20 octets) | commit `5e7d8fb` | même exécution |
| `2026-11-12_1618_…-uncnf-sf10-51o-x30` | 30 × `mac tx uncnf`, SF10, 51 octets (premier fragment de la série de repli en 51 octets) | commit `5210933` | même exécution |
| `2026-11-13_1123_…-uncnf-sf12-20o-x30` | 30 × `mac tx uncnf` SF12, 20 octets, + 1 message de chauffe exclu | commit `a0d3584` | même exécution |
| `2026-11-13_1300_…-uncnf-sf11-51o-x30` | 30 × `mac tx uncnf` SF11, 51 octets, + 1 de chauffe ; tentatives 29 à 31 dans une autre condition (voir plus bas) | commit `a0d3584` | même exécution |
| `2026-11-13_15xx/16xx_…-sf7-6o-x10-sensib-*` | Test de sensibilité à l'environnement de l'antenne : 11 conditions × (10 × `mac tx uncnf` SF7, 6 octets, + 1 de chauffe) | code du commit `ea2874a` (`Mote/src` inchangé ensuite) | même exécution |
| `2026-11-13_1036_…-uncnf-sf12-6o-x30-nodc-controle` | **Contrôle de méthode**, hors résultats : 30 × `mac tx uncnf` SF12, 6 octets, chambre anéchoïque blindée, duty cycle coupé (`--no-duty-cycle`), 6 s de sommeil entre messages | commit `00a3697` | même exécution |

Pour la série `2026-11-12_1007`, les champs `git` et `sha256` du JSON sont
faux : ils ont été relevés à la fin de la série, alors que les scripts avaient
été modifiés pendant qu'elle tournait (ajout de `--rx2-dr`). Le code exécuté
est celui du commit `181d90e`, seul à donner l'empreinte de `banc_pi.py`
ci-dessus. Depuis le commit suivant, le JSON distingue le code de
l'acquisition (`acquisition`, relevé au lancement) de celui de l'analyse
(`analysis`). Pour la série `1030`, `git` affiche `e262f09` (commit d'une autre
session, survenu pendant la série, sans modification de `Mote/src`) ; ses
empreintes sont celles du commit `c4e3b98`.

Pour la série `1401`, le journal détaillé du Pi a été perdu (voir le journal
du banc, 10 novembre 2026) : la fenêtre de fond est placée d'après la séquence
de `banc_pi.py` et l'intégrité est contrôlée par l'écart entre repères comparé
à la médiane du même SF (`pi_times: false` dans le JSON).

## Énergie par message, série de référence

Message LoRaWAN non confirmé de 6 octets, session ABP locale (aucun
downlink), `pwridx` 1 (14 dBm), `rxdelay1` 1000 ms, RX2 en SF12. Énergie du
début de l'émission à la fin de RX2, au-dessus du fond de la carte module en
sommeil, à 3,3 V. n = 30 par SF, aucune tentative écartée.

| SF | Énergie (mJ) | Émission (ms) | RX1 (ms) | RX2 (ms) | Durée (ms) |
|---|---|---|---|---|---|
| 7 | 38,77 ± 0,06 | 51,5 | 19 | 264 | 2 284 |
| 8 | 45,97 ± 0,08 | 102,9 | 28 | 264 | 2 335 |
| 9 | 57,95 ± 0,13 | 185,3 | 47 | 264 | 2 418 |
| 10 | 80,15 ± 0,08 | 329,7 | 117 | 263 | 2 562 |
| 11 | 137,90 ± 0,25 | 741,4 | 165 | 263 | 2 974 |
| 12 | 220,41 ± 0,40 | 1 318,9 | 264 | 264 | 3 551 |

Moyenne ± écart-type. Fond de la carte (module en sommeil) : 1,38 mA ; repos
du module : 4,29 mA au total.

## Sonde ratée et débit de RX2 (12 novembre 2026)

Message confirmé sans ACK ni retransmission (`mac tx cnf`, `retx` 0) : la
réponse est `mac_err` après RX2. Mêmes réglages que ci-dessus, n = 30.

| SF | RX2 | Énergie (mJ) | RX1 (ms) | RX2 (ms) | Durée (ms) |
|---|---|---|---|---|---|
| 7 | SF12 | 38,76 ± 0,06 | 20 | 264 | 2 284 |
| 8 | SF12 | 46,12 ± 0,02 | 28 | 264 | 2 335 |
| 9 | SF12 | 58,12 ± 0,03 | 47 | 264 | 2 418 |
| 7 | **SF9** | **28,99 ± 0,04** | 20 | 46 | 2 094 |

Une sonde ratée coûte autant qu'un uplink non confirmé au même SF (écart de
0,0 à 0,3 %). Passer RX2 de SF12 à SF9 économise 9,8 mJ par message (−25 % en
SF7). Au SF de repli, avec RX2 en SF9 (uplink non confirmé, 6 octets) :
SF10 70,51 ± 0,11 mJ, SF11 128,83 ± 0,32 mJ, SF12 211,46 ± 0,41 mJ, soit
−9,6 / −9,0 / −8,9 mJ par rapport à RX2 en SF12 (RX2 de 46 à 47 ms). Avec
`rx1_delay` à 3 s (RX2 à 4 s), une sonde SF7 ratée coûte
57,90 ± 0,13 mJ (+19,1 mJ, +49 %), pour une durée de 4 284 ms.

## Sonde ratée selon la taille de la charge utile

RX2 en SF12, `rx1_delay` 1 s, n = 30 par case. Médiane (moyenne ± écart-type
quand une fenêtre RX2 allongée la décale).

| SF | 6 octets | 20 octets | 51 octets |
|---|---|---|---|
| 7 | 38,76 | 41,59 (41,57 ± 0,06) | 47,85 (47,85 ± 0,03) |
| 8 | 46,12 | 50,33 (50,49 ± 0,90) | 61,47 (61,46 ± 0,04) |
| 9 | 58,12 | 66,46 (66,48 ± 0,10) | 86,02 (87,60 ± 8,64) |

Temps d'émission en 20 octets : 71,9 / 133,6 / 246,8 ms ; en 51 octets :
118,0 / 215,6 / 390,1 ms (SF7 / SF8 / SF9).

## Repli selon la taille de la charge utile

Uplink non confirmé, RX2 en SF12, `rx1_delay` 1 s, n = 30 par case. Moyenne ±
écart-type.

| SF | 6 octets | 20 octets | 51 octets |
|---|---|---|---|
| 10 | 80,15 ± 0,08 | 97,42 ± 1,56 (médiane 97,14) | 130,65 ± 0,23 |
| 11 | 137,90 ± 0,25 | 172,28 ± 0,28 | 248,05 ± 2,58 (médiane 248,72) |
| 12 | 220,41 ± 0,40 | 286,81 ± 0,28 | à mesurer |

Repli SF11 en 51 octets : tentatives 1 à 28 entre 247 et 250 mJ (courant
d'émission 42,6 mA), tentatives 29 à 31 à 240,6 mJ (40,9 mA) après une
modification du montage vers 14:15, voir la section sur la sensibilité.

Temps d'émission en 20 octets : 452,6 ms (SF10), 987,1 ms (SF11), 1 810,4 ms
(SF12) ; en 51 octets : 698,4 ms (SF10), 1 560,6 ms (SF11).

## Sensibilité à l'environnement de l'antenne (13 novembre 2026)

Le courant d'émission (`i_tx_ma`, moyenne au-dessus de 30 mA) ne dépend que de
la puissance émise et de ce que « voit » l'antenne. Il valait 42,5 à 42,9 mA
d'une série à l'autre du 10 au 13 novembre, puis a sauté de −4 % pendant la
série SF11 en 51 octets. Test dédié : 11 conditions, 10 messages SF7 de
6 octets chacune, dans l'ordre.

| # | Condition | Courant d'émission (mA) | Écart | Énergie SF7 (mJ) |
|---|---|---|---|---|
| 1 | Mote à plat, antenne à plat (référence du jour) | 41,99 | — | 38,60 |
| 2 | Antenne verticale | 43,62 | +3,9 % | 38,86 |
| 3 | Gourde métallique remplie d'eau à 5 cm de l'antenne | 42,06 | +0,2 % | 38,59 |
| 4 | Gourde en contact avec l'antenne | 41,97 | 0,0 % | 38,56 |
| 5 | Gourde posée sur le bout de l'antenne | 42,50 | +1,2 % | 38,65 |
| 6 | Antenne dévissée d'un demi-tour | 42,74 | +1,8 % | 38,68 |
| 7 | Retour à la référence | 41,87 | −0,3 % | 38,52 |
| 8 | Pince à sertir en face de l'antenne | 41,97 | 0,0 % | 38,55 |
| 9 | Mote tournée sur le bureau | 44,44 | +5,8 % | 38,31 (38,98 sans la tentative 5) |
| 10 | Mote debout, adossée à la gourde | 36,14 | −13,9 % | 37,55 |
| 11 | Mote debout, sans la gourde | 45,01 | +7,2 % | 39,10 |

- Plage observée : **−14 % à +7 %** sur le courant d'émission. Un objet
  métallique à côté de l'antenne n'a pas d'effet ; la position de la carte et
  de l'antenne, et un objet contre la carte, en ont un.
- Effet sur l'énergie d'un message proportionnel à la part de l'émission :
  −2,7 % à +1,3 % en SF7 ; jusqu'à environ −12 % / +6 % en SF12.
- Reproductibilité : 0,3 % dans une même session (conditions 1 et 7), 0,75 à
  2 % d'un jour à l'autre.
- Aucun facteur de correction n'est transposable d'une position à une autre
  (la condition 2 vaut pour cette position de la mote seulement). Toutes les
  séries de résultats sont faites mote et antenne à plat ; sur le terrain, les
  antennes sont verticales, dans des environnements propres à chaque mote. La
  dépendance à l'emplacement est donc une incertitude sur l'énergie
  d'émission, pas une correction.
- Le montage est fragile (fils sur barrettes, soudures à la main) : un
  mouvement de la carte peut aussi modifier le plan de masse et le trajet du
  courant, sans qu'on puisse séparer cet effet de celui de l'antenne. Règle :
  ne pas toucher au montage pendant une série, contrôler le courant d'émission
  au démarrage (`--i-tx-ref`).

**Émission manquante** : dans la condition 9, la tentative 5 a reçu
`mac_tx_ok` et ouvert RX1 et RX2, mais le courant est resté au niveau du repos
pendant l'émission (pointe de 2 ms au lieu de 51 ms à 44 mA). Seul cas sur les
884 messages mesurés du 10 au 13 novembre. Sur le terrain, un tel message
serait compté comme émis puis perdu. Cause inconnue (faux contact du montage
manipulé juste avant, défaut du module) ; énergie apparente de 32,0 mJ, gardée
dans la moyenne de la condition 9.

## Contrôle de la méthode sans duty cycle (13 novembre 2026)

Pour accélérer les séries à SF élevé (97 % du temps est l'attente du duty
cycle), le banc a été placé dans une chambre anéchoïque blindée et le duty
cycle coupé. La série de contrôle répète la référence SF12 en 6 octets :

| | Référence (bureau, duty cycle, 10 nov.) | Contrôle (chambre, sans duty cycle) |
|---|---|---|
| Énergie médiane | 220,48 mJ | 219,41 mJ (−0,5 %) |
| Moyenne ± écart-type | 220,41 ± 0,40 mJ | 219,69 ± 1,78 mJ ; 219,37 sans le 1er message |
| Courant d'émission moyen | 42,67 mA | 42,44 mA sans le 1er message |
| Émission, RX1, RX2 | 1 318,9 / 264 / 264 ms | identiques |
| Fond (module en sommeil) | 1,378 mA | 1,380 mA |

- Écart systématique de −0,5 %, stable du 2e au 30e message : aucune dérive
  avec des émissions rapprochées (6 s de sommeil au lieu de 133 s). La cause
  (environnement de l'antenne dans la chambre, température) n'est pas isolée.
- Le 1er message de la série coûte 229,02 mJ : courant d'émission de
  44,76 mA au lieu de 42,4 mA, durées normales. Effet probable de la première
  émission après mise sous tension. Les séries précédentes commençaient en SF7,
  où l'effet est noyé.
- **Décision** : les séries de résultats restent faites au bureau, sous duty
  cycle réglementaire, pour garder des conditions homogènes. Le contrôle valide
  la méthode pour une campagne future plus lourde (écart à annoncer) ; aucun
  résultat publié n'en dépend.

**Fenêtres RX2 allongées** (le module détecte un préambule et reste en
réception) : 5 messages sur 884 mesurés du 10 au 13 novembre (validation SF7 :
558 ms, 52,4 mJ ; sonde SF8 20 octets : 371 ms, 55,3 mJ ; sonde SF9 51 octets :
1 282 ms, 133,3 mJ ; repli SF10 20 octets : 449 ms, 105,7 mJ ; chauffe SF7 de
la condition 8 : 1 395 ms, 91,0 mJ, avec `mac_err` sur un uplink non confirmé,
ce qui confirme la réception d'une trame étrangère rejetée). Elles sont gardées dans les statistiques : la moyenne est la valeur
à retenir pour le modèle d'énergie.

## Colonnes du CSV

| Colonne | Sens |
|---|---|
| `attempt`, `rep`, `sf`, `mode`, `payload_bytes` | Tentative, répétition dans le SF, réglages |
| `upctr` | Compteur de trames montantes avant l'envoi (vide si journal du Pi perdu) |
| `immediate`, `final` | Réponses du module à `mac tx` (immédiate, puis après RX2) |
| `reset_seen` | Chaîne de version reçue sans l'avoir demandée (redémarrage du module) |
| `rise`, `fall` | Indices des échantillons des fronts du repère sur D0 |
| `marker_ms`, `marker_samples_error` | Durée du repère à l'horloge du Pi, écart en échantillons (séries avec journal du Pi) |
| `i_sleep_ma`, `i_idle_ma` | Fond (module en sommeil) et repos avant le message, en mA |
| `tx_start_ms` | Début de l'émission après le repère haut |
| `duration_ms`, `charge_mc` | Durée et charge du début de l'émission à la fin de RX2 |
| `tx_ms` | Temps au-dessus de 30 mA (émission) |
| `energy_mj` | Énergie au-dessus du fond, à la tension de la source |
| `rx_windows_ms` | Durées des fenêtres de réception détectées (entre 8 et 30 mA) |
| `gap_samples_error` | Écart d'échantillons entre deux repères hauts, par rapport à l'attendu |
| `valid` | Tentative retenue dans les statistiques |
