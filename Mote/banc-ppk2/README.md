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
SF7). Avec `rx1_delay` à 3 s (RX2 à 4 s), une sonde SF7 ratée coûte
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

**Fenêtres RX2 allongées** (le module détecte un préambule et reste en
réception) : 3 messages sur 543 mesurés du 10 au 12 novembre (validation SF7 :
558 ms, 52,4 mJ ; SF8 20 octets : 371 ms, 55,3 mJ ; SF9 51 octets : 1 282 ms,
133,3 mJ). Elles sont gardées dans les statistiques : la moyenne est la valeur
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
