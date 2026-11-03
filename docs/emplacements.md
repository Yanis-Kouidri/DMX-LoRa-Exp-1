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
| 2 | `pi-mote-2` | Forum Louis Lareng | 43.561218 | 1.463896 | 1 | 319 m | 260° (O) | côté | oui, provisoire (2026-10-26, au sol) |
| 3 | `pi-mote-3` | Bâtiment U3 Pierre-Paul Riquet | 43.562104 | 1.469976 | à définir | 181 m | 76° (E) | côté | oui, provisoire (2026-10-26, au sol) |
| 4 | `pi-mote-4` | Centre de biologie intégrative | 43.559245 | 1.470801 | 4 | 365 m | 139° (SE) | derrière | non sur place (2026-11-03), gardé : voir les pré-tests |
| 5 | `pi-mote-5` | Bâtiment 4R1 | 43.558444 | 1.469205 | 3 | 380 m | 163° (S) | derrière | oui (2026-11-03, sur place) |

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

## Pré-tests sur place (installation des motes)

Test rapide à l'emplacement définitif, juste avant de laisser la mote en
place : join OTAA en SF12, puis quelques `mac tx uncnf` en SF11, ADR coupé.
Ce n'est pas une mesure du SF minimal : le régime 1a la donnera. RSSI et SNR
sont ceux reçus par la gateway fixe (tables `gateway_events` et `uplinks`).

| # | Nom | Date, heure (locale) | Position | Join requests SF12 reçues | SNR des joins | Uplinks SF11 reçus | SNR SF11 |
|---|---|---|---|---|---|---|---|
| 4 | Centre de biologie intégrative | 2026-11-03, vers 15:37 | 4ᵉ étage, laboratoire, près d'une fenêtre donnant sur l'IRIT | 1, accept émis mais non reçu par la mote | −18 dB | — | — |
| 5 | Bâtiment 4R1 | 2026-11-03, 14:37–14:43 | 3ᵉ étage, près d'une fenêtre exposée nord-est | 3, toutes acceptées | −14,25 ; −17,5 ; −18 dB | 2 (2 envoyés) | −17,5 dB (×2) |

- **CBI** : aucun join accepté côté mote. Une seule join request est arrivée
  (RSSI −107 dBm, SNR −18 dB, soit 2 dB au-dessus du seuil SF12). ChirpStack
  a répondu en RX1 (868,3 MHz, SF12, 16 dBm) et la gateway a confirmé
  l'émission (`txack` OK), mais la mote ne l'a pas reçue : les pertes sont à
  la montée et à la descente. Le laboratoire voit le bâtiment de l'IRIT, mais
  la gateway est sur la façade opposée (fenêtre nord-ouest) : le signal
  traverse le bâtiment. Selon la règle ci-dessus, ce « non » devrait exclure
  l'emplacement ; il est **gardé** car c'est le seul possible dans ce
  bâtiment. Le régime 1a refait un join SF12 toutes les 10 min jusqu'au
  succès : les tentatives (journal CSV de la mote et `gateway_events`)
  mesurent le lien en attendant. Ces joins répétés respectent le duty cycle
  de 1 %, mais pas le join backoff de LoRaWAN (8,7 s d'émission par 24 h après
  les 11 premières heures) : écart accepté, sur notre propre réseau.

- **4R1** : la marge est faible, environ 2 dB au-dessus du seuil SF12
  (−20 dB) pour les deux derniers joins, et 0 dB au-dessus du seuil SF11
  (−17,5 dB). C'est environ 3 dB de moins que le SNR médian mesuré au sol le
  26 octobre (−14,6 dB). La fenêtre est exposée nord-est alors que la gateway
  est au nord-nord-ouest (azimut 343° depuis la mote) : le signal ne passe pas
  directement par la fenêtre. Des pertes en SF12 sont possibles pendant le
  régime 1a ; à surveiller les premières heures.

## Régime 1a

Service `regime-1a` (voir [`Mote/README.md`](../Mote/README.md#régime-1a-en-service)),
journal `~/lora-logs/regime_1a_<hôte>.csv` sur chaque Pi.

| # | Pi | Démarrage (heure locale) | État au démarrage |
|---|---|---|---|
| 4 | `pi-mote-4` | 2026-11-03, 16:09 | Non joint : joins SF12 répétés (60 s, 120 s, 300 s, puis toutes les 10 min) |
| 5 | `pi-mote-5` | 2026-11-03, 16:09 | Joint (session du pré-test), balayage SF7 → SF12 dès le cycle 0 |

**Fenêtres d'exclusion** (gateway fixe hors service, voir [`gateway.md`](gateway.md)) :

| Début | Fin | Cause |
|---|---|---|
| 2026-11-03 15:58:15 | 2026-11-03 16:21:04 | LoRa restée désactivée après une micro-coupure du backhaul (relance du netwatch en échec) |
| 2026-11-03 16:22:59 | 2026-11-03 16:23:25 | Relance de la LoRa à l'installation du nouveau netwatch |

Heures de Paris. Les émissions faites dans ces fenêtres ne comptent pas dans
le PDR.

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
