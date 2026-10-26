# Campagne de test 0 — Join OTAA en SF12

**Objectif** : vérifier que, depuis chaque emplacement prévu, une mote réussit un join OTAA en SF12 (`mac set dr 0` puis `mac join otaa`) via la gateway fixe de l'IRIT, condition indispensable pour garder l'emplacement.

Date : 26 octobre 2026 (heures locales, UTC+1)
Mote utilisée (DevEUI) : `pi-mote-1`, `0004a30b0023f200`

**Conditions** : mesures faites au sol, près de chaque bâtiment, et non à l'emplacement exact de la mote. Un résultat positif reste à confirmer à l'emplacement réel.

## 1. Bâtiment ADM

- Heure de début : 15h20
- Heure de fin : 15h21
- OTAA acceptés (sur 10) : 8/10
- Remarque : Bonne marge sur le SF12

## 2. Forum Louis Lareng

- Heure de début : 15h25
- Heure de fin : 15h28
- OTAA acceptés (sur 10) : 3/3 accepté
- Remarque : j'en ai fait que 3 car le dutycycle s'est réactivé

## 3. Bâtiment U3 Pierre-Paul Riquet

- Heure de début : 15h41
- Heure de fin : 15h44
- OTAA acceptés (sur 10) : 7/10
- Remarque : J'ai un peu surélevé la mote après les 2 premier join

## 4. Centre de biologie intégrative

- Heure de début : 15h49
- Heure de fin : 15h51
- OTAA acceptés (sur 10) : 6/10
- Remarque : suite aux premiers denied j'ai surélévé la mote à la mainss

## 5. Bâtiment 4R1

- Heure de début :15h57
- Heure de fin :15h59
- OTAA acceptés (sur 10) : 9/10
- Remarque : J'étais assis sur un caillou

## Dépouillement

RSSI, SNR et confrontation avec les logs ChirpStack : voir [`emplacements.md`](emplacements.md#résultats-préliminaires-du-join-sf12-campagne-0-26-octobre-2026).
