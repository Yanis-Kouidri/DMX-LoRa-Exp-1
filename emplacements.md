# Emplacements de déploiement

Emplacements prévus pour la gateway fixe et les motes, sur le campus Paul
Sabatier. Les données sont aussi dans [`emplacements.csv`](emplacements.csv),
pour les croiser avec les traces GPX et faire la carte.

- Coordonnées relevées sur Google Maps à l'emplacement supposé de chaque
  mote, à affiner si besoin après l'installation.
- Pas de nom de collègue ici : le dépôt est public.

## Gateway fixe

| Nom | Latitude | Longitude | Étage | Remarque |
|---|---|---|---|---|
| IRIT, bureau | 43.561705 | 1.467795 | 4 | Près d'une fenêtre orientée nord-ouest (azimut 315°) |

## Motes

Distance et azimut sont calculés depuis la gateway fixe (distance du grand
cercle, azimut compté depuis le nord dans le sens horaire). Le côté indique la
position par rapport à la fenêtre de la gateway :

- **face** : à moins de 45° de l'axe de la fenêtre (nord-ouest) ;
- **côté** : entre 45° et 135° ;
- **derrière** : à plus de 135°, le signal traverse le bâtiment de l'IRIT.

| # | Pi | Nom | Latitude | Longitude | Étage | Distance | Azimut | Côté | Join SF12 vers la gateway fixe |
|---|---|---|---|---|---|---|---|---|---|
| 1 | `pi-mote-1` | Bâtiment ADM | 43.563038 | 1.466038 | à définir | 205 m | 316° (NO) | face | à vérifier |
| 2 | `pi-mote-2` | Forum Louis Lareng | 43.561218 | 1.463896 | à définir | 319 m | 260° (O) | côté | à vérifier |
| 3 | `pi-mote-3` | Bâtiment U3 Pierre-Paul Riquet | 43.562104 | 1.469976 | à définir | 181 m | 76° (E) | côté | à vérifier |
| 4 | `pi-mote-4` | Centre de biologie intégrative | 43.559245 | 1.470801 | à définir | 365 m | 139° (SE) | derrière | à vérifier |
| 5 | `pi-mote-5` | Bâtiment 4R1 | 43.558444 | 1.469205 | à définir | 380 m | 163° (S) | derrière | à vérifier |

La mote N est pilotée par le Raspberry Pi `pi-mote-N`.

Dernière colonne : un join OTAA en SF12 (`mac set dr 0` puis `mac join otaa`)
depuis l'emplacement réel est-il accepté via la gateway fixe ? Valeurs : « à
vérifier », « oui (date) » ou « non (date) ». SF12 est obligatoire : un « non »
exclut l'emplacement.

## Lecture attendue (hypothèse, à vérifier par la balade 0a)

Critère visé (voir le plan, section 5) : SF minimal fiable vers la gateway
fixe entre SF10 et SF12, et SF12 obligatoire.

Estimation grossière de la portée SF12, mote et gateway en intérieur : environ
0,9 à 1,5 km face à la fenêtre, environ 0,3 à 0,6 km derrière le bâtiment.
Tous les emplacements sont à moins de 400 m :

- **SF12** devrait passer partout.
- **ADM** (face à la fenêtre, 205 m) risque fort de passer en SF7 : trop bien
  couvert pour le critère.
- **Forum** et **U3** (côtés, 180 à 320 m) : incertains, plutôt SF7 à SF9.
- **CBI** et **4R1** (derrière, 365 à 380 m) : meilleurs candidats pour SF10 à
  SF12.

L'effet des bâtiments varie de ±8 dB d'un endroit à l'autre, soit environ
deux crans de SF : seule la mesure tranche.

## À faire

- [ ] Relever l'étage de chaque mote.
- [ ] Trouver le sixième emplacement (`pi-mote-6`), plutôt au-delà de 500 m ou
      derrière l'IRIT.
- [ ] Prévoir des emplacements de repli, si la balade 0a montre une couverture
      trop bonne (SF7 à SF9).
- [ ] Gateway fixe : noter la hauteur et l'orientation de l'antenne, la distance
      à la fenêtre, et prendre une photo de référence.
