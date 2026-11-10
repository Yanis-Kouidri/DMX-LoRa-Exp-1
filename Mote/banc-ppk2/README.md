# Résultats du banc PPK2

Résultats des séries de mesure du [banc PPK2](../banc-ppk2.md) sur la mote de
test `0004A30B00FD7330`. Un fichier CSV par série (une ligne par tentative) et
un JSON de métadonnées, écrits par `src/banc_ppk2.py`.

Les échantillons bruts (`.cur.f32`, courant en µA ; `.dig.u8`, voies logiques ;
100 kS/s) ne sont pas versionnés : plusieurs gigaoctets par série. Ils sont sur
le PC du banc, dans `C:\Users\<utilisateur>\banc-ppk2\data\`, sous le même nom,
et doivent être copiés dans le dossier partagé de l'équipe (Google Drive).

## Séries

| Série | Contenu | Acquisition | Analyse |
|---|---|---|---|
| `2026-11-10_1006_…-x3-validation` | 3 × `mac tx uncnf` SF7, 6 octets | dépôt au commit `082bf32` (scripts non encore commités) | même exécution |
| `2026-11-10_1401_…-x30` | 30 × `mac tx uncnf` par SF, SF7 à SF12, 6 octets | dépôt au commit `71a2f38` | `--reanalyse` au commit `181d90e` |

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
