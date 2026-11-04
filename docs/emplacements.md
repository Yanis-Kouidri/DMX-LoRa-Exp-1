# Emplacements de déploiement

Emplacements prévus pour la gateway fixe et les motes, sur le campus Paul
Sabatier. Les données sont aussi dans [`emplacements.csv`](emplacements.csv),
pour les croiser avec les traces GPX et faire la carte.

- Coordonnées relevées sur Google Maps à l'emplacement supposé de chaque
  mote, à affiner si besoin après l'installation. Affinées le 4 novembre 2026
  pour les motes installées (2, 4 et 5), une fois les bureaux connus : les
  distances changent de 3 à 14 m et les azimuts de 1 à 7°, sans changer le
  côté. Valeurs arrondies à 6 décimales ; la précision réelle,
  celle du pointage sur la carte, est de quelques mètres.
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
| 2 | `pi-mote-2` | Forum Louis Lareng | 43.560857 | 1.464050 | 1 (au sol) | 316 m | 253° (O) | côté | non sur place (2026-11-03, gateway dégradée) ; joint par le régime 1a à 17:05 |
| 3 | `pi-mote-3` | Bâtiment U3 Pierre-Paul Riquet | 43.562104 | 1.469976 | à définir | 181 m | 76° (E) | côté | oui, provisoire (2026-10-26, au sol) |
| 4 | `pi-mote-4` | Centre de biologie intégrative | 43.559482 | 1.470894 | 4 | 351 m | 135° (SE) | derrière | non sur place (2026-11-03), gardé : voir les pré-tests |
| 5 | `pi-mote-5` | Bâtiment 4R1 | 43.558449 | 1.469104 | 3 | 377 m | 164° (S) | derrière | oui (2026-11-03, sur place) |

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
| 2 | Forum Louis Lareng | 2026-11-03, vers 16:30–16:55 | 1er étage, mote posée au sol d'un bureau côté route (le signal traverse le bâtiment) ; essai aussi depuis un bureau côté campus | 0 | — | — | — |
| 4 | Centre de biologie intégrative | 2026-11-03, vers 15:37 | 4ᵉ étage, laboratoire, près d'une fenêtre donnant sur l'IRIT | 1, accept émis mais non reçu par la mote | −18 dB | — | — |
| 5 | Bâtiment 4R1 | 2026-11-03, 14:37–14:43 | 3ᵉ étage, près d'une fenêtre exposée nord-est | 3, toutes acceptées | −14,25 ; −17,5 ; −18 dB | 2 (2 envoyés) | −17,5 dB (×2) |

- **Forum** : aucun join accepté, ni depuis le bureau côté route, ni depuis
  la fenêtre d'un bureau côté campus, et aucune join request reçue. Le test a
  eu lieu pendant que la réception de la gateway était dégradée (voir les
  fenêtres d'exclusion ci-dessous) : il ne dit rien du lien. La mote a joint
  à 17:05, juste après le déplacement de la gateway.

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
| 2 | `pi-mote-2` | 2026-11-03, 17:01 | Non joint ; join accepté à 17:05 (3ᵉ essai) |

`pi-mote-4` a joint le 3 novembre à 18:08, au 15ᵉ essai. De 17:18 à 17:58,
cinq essais ont été bloqués par la mote elle-même (`no_free_ch`) : le firmware
du RN2483 limite aussi le temps d'émission des joins.

**Fenêtres d'exclusion** (gateway fixe hors service ou dégradée, voir [`gateway.md`](gateway.md)) :

| Début | Fin | Cause |
|---|---|---|
| 2026-11-03 13:15 | 2026-11-03 14:10 | Réception dégradée (RSSI médian des trames étrangères −120 dBm au lieu de −107, trafic divisé par 4) ; cause non établie. Avant le régime 1a |
| 2026-11-03 15:58:15 | 2026-11-03 16:21:04 | LoRa restée désactivée après une micro-coupure du backhaul (relance du netwatch en échec) |
| 2026-11-03 16:21:04 | 2026-11-03, vers 17:00 | Réception dégradée, même signature qu'à 13:15 ; fin au déplacement de la gateway (heure exacte non relevée, première trame d'une mote à 17:04:59) |
| 2026-11-03 16:22:59 | 2026-11-03 16:23:25 | Relance de la LoRa à l'installation du nouveau netwatch |
| 2026-11-04 08:53:06 | 2026-11-04, vers 08:53:32 | Relance de la LoRa par le netwatch après une micro-coupure du backhaul (9 s), sans intervention sur la gateway |
| 2026-11-04 09:01:47 | 2026-11-04, vers 09:02:13 | Idem (micro-coupure de 9 s) |

Les fins « vers » sont estimées avec la durée habituelle d'une relance
(26 s), le journal de la gateway ne gardant pas toujours la ligne
`forwarder is ready`.

Heures de Paris. Les émissions faites dans ces fenêtres ne comptent pas dans
le PDR.

## Résultats préliminaires du régime 1a (première nuit, 3–4 novembre 2026)

⚠️ **Une seule nuit de mesures.** Ces chiffres donnent une tendance, pas un
SF minimal fiable : le régime 1a doit tourner plusieurs jours, et l'effet de
l'heure (voir le 4R1) impose de couvrir plusieurs journées complètes. La
gateway a été surélevée de 30 cm et rapprochée de la fenêtre de 10 cm le
3 novembre vers 17:00 (voir [`gateway.md`](gateway.md)). Ce petit
déplacement a suffi à relever d'environ 4 dB le RSSI médian des trames
étrangères (−107 → −103 dBm) et à doubler leur nombre : ces résultats ne
sont pas directement comparables à la campagne 0 ni aux pré-tests, faits
depuis l'ancienne position.

- **Période** : 2026-11-03 17:05 → 2026-11-04 08:50 (heure de Paris), sans
  fenêtre d'exclusion ; `pi-mote-4` n'émet qu'à partir de son join (18:08).
- **Méthode** : chaque émission du journal CSV de la mote (`event=tx`,
  réponse immédiate `ok`, y compris les `mac_err`) est cherchée dans la table
  `uplinks` par sa charge utile (numéro de cycle, DR, marqueur `0x1A`), unique
  par mote. PDR = paquets reçus / paquets émis. Environ 175 à 189 émissions
  par SF et par mote. Calcul :
  `python Mote/src/bilan_regime_1a.py <dossier> --debut 2026-11-03T17:05 --fin 2026-11-04T08:50`
  (données copiées le 4 novembre vers 10:05).

| # | Nom | SF7 | SF8 | SF9 | SF10 | SF11 | SF12 | SNR médian SF12 (reçus) |
|---|---|---|---|---|---|---|---|---|
| 2 | Forum Louis Lareng | 0 % | 7 % | 29 % | 70 % | 84 % | 87 % | −12 dB |
| 4 | Centre de biologie intégrative | 0 % | 0 % | 0 % | 0 % | 1 % | 15 % | −17,75 dB |
| 5 | Bâtiment 4R1 | 1 % | 1 % | 6 % | 26 % | 42 % | 64 % | −16 dB |

**Lecture**

- **Aucune mote n'atteint 90 % de PDR**, quel que soit le SF : selon la
  définition du [plan](plan-experimental.md) (section 8), aucune n'a encore
  de SF minimal fiable. Le seuil de 90 % sera peut-être adapté une fois
  plusieurs jours de mesures disponibles.
- **Forum** : SF7 ne passe jamais, SF9 à 29 %. Contrairement à la lecture
  attendue ci-dessous (campagne 0, au sol), l'emplacement est dans la cible.
- **4R1 : fort effet de l'heure.** En SF12, 2 paquets reçus sur 46 de 17h à
  21h, puis 119 sur 143 (83 %) de 21h à 8h50. Cause non établie (activité
  dans le bâtiment, brouillage en journée).
- **CBI** : SF12 à 15 %, SNR toujours proche du seuil de démodulation
  (−20 dB).
- **Pertes sans lien avec le SNR** : le Forum perd 13 % de ses paquets SF12
  avec environ 8 dB de marge médiane, à raison d'environ une perte par heure,
  sans regroupement dans le temps. Hypothèse principale : collisions avec les
  autres réseaux LoRa du campus. La gateway reçoit 60 à 90 trames étrangères
  par heure depuis son déplacement, et un paquet SF12 dure environ 1,2 s.
  Autre piste : les émissions de la gateway, pendant lesquelles elle ne
  reçoit pas.

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
