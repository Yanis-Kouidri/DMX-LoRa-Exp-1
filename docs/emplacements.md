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
| 1 | `pi-mote-1` | Bâtiment ADM | 43.563038 | 1.466038 | à définir | 205 m | 316° (NO) | face | oui, provisoire (2026-10-26, au sol) |
| 2 | `pi-mote-2` | Forum Louis Lareng | 43.561218 | 1.463896 | à définir | 319 m | 260° (O) | côté | oui, provisoire (2026-10-26, au sol) |
| 3 | `pi-mote-3` | Bâtiment U3 Pierre-Paul Riquet | 43.562104 | 1.469976 | à définir | 181 m | 76° (E) | côté | oui, provisoire (2026-10-26, au sol) |
| 4 | `pi-mote-4` | Centre de biologie intégrative | 43.559245 | 1.470801 | à définir | 365 m | 139° (SE) | derrière | oui, provisoire (2026-10-26, au sol) |
| 5 | `pi-mote-5` | Bâtiment 4R1 | 43.558444 | 1.469205 | à définir | 380 m | 163° (S) | derrière | oui, provisoire (2026-10-26, au sol) |

La mote N est pilotée par le Raspberry Pi `pi-mote-N`.

Dernière colonne : un join OTAA en SF12 (`mac set dr 0` puis `mac join otaa`)
depuis l'emplacement réel est-il accepté via la gateway fixe ? Valeurs : « à
vérifier », « oui (date) » ou « non (date) ». « Provisoire, au sol » : test fait
à proximité du bâtiment, pas à l'emplacement exact. SF12 est obligatoire : un « non »
exclut l'emplacement.

## Résultats préliminaires du join SF12 (campagne 0, 26 octobre 2026)

Fiche de terrain : [`campagne-test-0.md`](campagne-test-0.md). Mesures faites
**au sol, à proximité immédiate de chaque bâtiment**, et non dans le bureau où
la mote sera installée. Le « oui » du tableau ci-dessus reste donc provisoire.
Il faudra refaire le test à l'emplacement réel.

Une seule mote (`pi-mote-1`, DevEUI `0004a30b0023f200`) a servi pour tous les
points. RSSI et SNR sont ceux des join requests reçues par la gateway fixe
(table `gateway_events`). La gateway est restée connectée pendant toute la
campagne : aucune déconnexion Basic Station entre 14:10 et 15:10 UTC.

| # | Nom | Heure (UTC) | Joins acceptés (mote) | Join requests reçues | SNR médian [min ; max] | RSSI | SF estimé par le SNR |
|---|---|---|---|---|---|---|---|
| 1 | Bâtiment ADM | 14:19–14:21 | 8/10 | 9 | −6,8 dB [−15,5 ; −1,0] | −105 à −101 dBm | SF7 à SF8 |
| 2 | Forum Louis Lareng | 14:26–14:27 | 3/3 | 3 | −3,3 dB [−4,8 ; −3,3] | −105 à −101 dBm | SF7 |
| 3 | Bâtiment U3 Pierre-Paul Riquet | 14:42–14:44 | 7/10 | 7 | −13,8 dB [−17,8 ; −11,0] | −105 à −102 dBm | SF10 |
| 4 | Centre de biologie intégrative | 14:49–14:51 | 6/10 | 6 | −14,9 dB [−17,0 ; −11,3] | −107 à −102 dBm | SF10 à SF11 |
| 5 | Bâtiment 4R1 | 14:57–15:00 | 9/10 | 10 | −14,6 dB [−17,3 ; −12,5] | −107 à −103 dBm | SF10 à SF11 |

**Lecture**

- **SF12 passe aux 5 emplacements**, avec au moins 3 dB de marge sur le seuil
  de démodulation SF12 (−20 dB) pour toutes les join requests reçues.
- **SF estimé** : plus petit SF dont le seuil de démodulation (SX127x : SF7
  −7,5 dB, SF8 −10, SF9 −12,5, SF10 −15, SF11 −17,5, SF12 −20) est sous le
  SNR médian. C'est une indication, pas une mesure : seul le balayage de la
  phase 1 donnera le SF minimal fiable.
- **ADM et Forum** semblent trop bien couverts pour le critère (SF10 à SF12),
  comme prévu dans la lecture attendue ci-dessous. **U3, CBI et 4R1** sont
  dans la cible.
- **Les échecs viennent surtout de la montée** : à U3 et au CBI, chaque join
  refusé correspond à une join request jamais reçue par la gateway. À ADM, une
  join request est perdue et un join accept n'a pas de confirmation d'émission
  de la gateway. À 4R1, les 10 join requests ont été reçues et les 10 accepts
  émis, mais la mote n'en a accepté que 9 : un downlink a été perdu.
- **Biais** : les join requests perdues n'ont pas de SNR. Les SNR ci-dessus
  sont donc ceux des paquets reçus, et surestiment le lien moyen, surtout à
  U3 et au CBI.
- **Position de la mote non contrôlée** : à U3, la mote a été surélevée après
  les 2 premiers joins ; au CBI, elle a été tenue en hauteur à la main après
  les premiers refus. À Forum, seulement 3 essais (duty cycle réactivé sur la
  mote).

## Lecture attendue (hypothèse, à vérifier par la balade 0a)

Critère visé (voir le [plan](plan-experimental.md#5-dispositif-expérimental), section 5) : SF minimal fiable vers la gateway
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
