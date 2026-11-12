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
| 1 | `pi-mote-1` | 2026-11-10, 18:03 | **Mote témoin**, à quelques mètres de la gateway fixe (voir ci-dessous). Déjà jointe (session de l'essai au banc du 6 novembre) |

**Mote témoin (`pi-mote-1`, depuis le 10 novembre 2026 à 18:03).** Décidée
avec les directeurs de thèse le 10 novembre : la mote 1 (DevEUI
`0004a30b0023f200`) tourne le régime 1a à l'identique (14 dBm, même cycle),
à quelques mètres de l'antenne de la gateway, dans le bureau de la gateway.
Avec un lien excellent, son PDR devrait être proche de 100 % à tous les SF :
toute perte de la témoin est une perte de la chaîne (gateway, backhaul,
ChirpStack, base), pas du canal. Elle sert de sentinelle des pannes
silencieuses, valide la règle d'exclusion et sert de contrôle temporel (par
exemple pendant l'effondrement de l'après-midi au 4R1).

- **Premier cycle** : 8 émissions sur 8 reçues de 18:03 à 18:09, RSSI de
  −39 à −32 dBm, SNR de +8,75 à +12 dB.
- **Limites** : elle ne mesure pas les collisions, car un signal aussi fort
  les gagne presque toujours (effet de capture). Surtout, à −35 dBm, elle
  peut masquer un paquet faible d'une autre mote reçu au même moment sur le
  même canal, quel que soit son SF, voire sur un canal voisin. Sa présence
  modifie donc le dispositif à partir du 10 novembre à 18:03 : sa gêne sera
  **mesurée** en comparant les paquets des autres motes qui chevauchent une
  émission de la témoin à ceux qui ne la chevauchent pas (heures exactes
  dans les journaux). Si elle est mesurable, l'éloigner ou réduire sa
  puissance, et traiter les chevauchements à part.
- La mote 1 était prévue pour l'emplacement ADM : celui-ci prendra un autre
  Pi (`pi-mote-3` ou `pi-mote-6`) et une autre mote.

`pi-mote-4` a joint le 3 novembre à 18:08, au 15ᵉ essai. De 17:18 à 17:58,
cinq essais ont été bloqués par la mote elle-même (`no_free_ch`) : le firmware
du RN2483 limite aussi le temps d'émission des joins.

**Incidents et interventions** (heure de Paris) :

| Date, heure | Pi | Événement |
|---|---|---|
| 2026-11-05 10:43 → 2026-11-06 11:04 | `pi-mote-5` | **Mote muette** : le RN2483 ne répond plus sur la liaison série (dernière réponse coupée, `mac_t`), alors qu'il reste visible en USB. Aucune émission pendant cette période, le journal ne contient que des erreurs : rien à exclure, mais environ 24 h de mesures perdues sur ce site (voir [`Mote/mote.md`](../Mote/mote.md)) |
| 2026-11-06 10:53 | `pi-mote-5` | Redémarrage du service, puis resynchronisation série : sans effet |
| 2026-11-06 11:04:24 | `pi-mote-5` | Coupure USB de 5 s (`uhubctl`) : la mote répond à 11:04:36, service relancé à 11:04:44, join accepté à 11:04:53 |
| 2026-11-06 11:16:48–52 | 2, 4, 5 | Redémarrage des services : reprise automatique d'une mote muette (commit `b0dc816`) |
| 2026-11-06 11:25:30–31 | `pi-mote-2` | Service arrêté 1 s pour lire `mac get pwridx` (valeur 1) |
| 2026-11-06 11:41:39–43 | 2, 4, 5 | Redémarrage des services : puissance relue et remise à `pwridx 1` avant chaque émission (`9734f59`) |
| 2026-11-06 11:52:31 | serveur | Redémarrage de ChirpStack : ADR désactivé dans la région (`819a3ea`), voir ci-dessous |
| 2026-11-06 11:52:52–57 | 2, 4, 5 | Redémarrage des services : ADR relu et remis à `off` avant chaque émission (`7a078bf`) |
| 2026-11-07 22:11:29 → 22:11:53 | `pi-mote-5` | Mote muette (`mac tx` sans réponse) : reprise automatique, resynchronisation sans effet, coupure USB, join accepté au premier essai (24 s) |
| 2026-11-08 10:55:57 → 10:56:21 | `pi-mote-5` | Idem (`mac get adr` sans réponse) : reprise automatique en 24 s |
| 2026-11-10 15:03:21 → 15:04:52 | `pi-mote-5` | Idem (`mac set dr` sans réponse) : coupure USB à 15:03:36, join refusé puis accepté au 2e essai (1 min 31 s) |
| 2026-11-10 18:03:05 | `pi-mote-1` | Démarrage du régime 1a sur la mote témoin, près de la gateway (Pi mis à jour à `8dba4ef`) |
| 2026-11-11, vers 16:08:44 | serveur | Redémarrage de tous les conteneurs de la pile LoRaWAN (ChirpStack, base, broker) par le propriétaire, après des mises à jour du serveur. Aucun trou de plus de 75 s dans les statistiques de la gateway, mais des uplinks ont pu être perdus pendant le redémarrage : exclu (E4) de 16:07:30 à 16:09:30, l'heure d'arrêt n'étant pas connue |
| 2026-11-11 14:23:22 → 14:24:54 | `pi-mote-1` | **Mote témoin muette** (`mac set dr` sans réponse) : reprise automatique, coupure USB à 14:23:38, join refusé puis accepté au 2e essai (1 min 32 s) |
| 2026-11-12 06:50:22 → 06:51:54 | `pi-mote-5` | Mote muette (`mac set dr` sans réponse) : reprise automatique, coupure USB à 06:50:38, join refusé puis accepté au 2e essai (1 min 32 s) |
| 2026-11-12 | serveur | Tailscale installé sur l'instance EC2 (`tag:server`), pour la collecte automatique des journaux (voir [`LoRaWAN-Infra/README.md`](../LoRaWAN-Infra/README.md#accès-tailscale-du-serveur)). Sans effet sur la chaîne de mesure |

Les redémarrages de service n'ont pas provoqué de nouveau join : chacun coûte
au plus le reste du cycle en cours, sans émission à exclure.

**ADR réactivé par les motes.** Malgré `mac set adr off`, le RN2483 réactive
son ADR dès qu'il reçoit un downlink dont le bit ADR est levé, ce que
ChirpStack faisait tant que l'ADR n'était pas désactivé dans la région (voir
le [plan](plan-experimental.md#14-constats-techniques-en-cours), section 14).
Le bit ADR des uplinks reçus permet de dater ces périodes :

| # | Début (premier uplink avec le bit ADR) | Fin |
|---|---|---|
| 4 | 2026-11-03 19:36 | 2026-11-06 11:52 |
| 5 | 2026-11-04 15:33 | 2026-11-05 10:43 (mote muette) |
| 2 | 2026-11-05 17:08 | 2026-11-06 11:16 |

Pendant ces périodes, le SF de chaque émission est bien celui prévu (vérifié
sur les 3 525 uplinks reçus du 3 au 6 novembre : le régime 1a fixe le DR
avant chaque émission). La **puissance d'émission n'est pas garantie** : une
mote en ADR peut l'augmenter d'elle-même faute de downlink, et la mote 2 a
acquitté des `LinkADRReq` (`tx_power_index=0`) à partir du 5 novembre à
17:43. Un essai au banc n'a pas permis de savoir comment le RN2483 applique
cette commande. Ces périodes sont à signaler, voire à traiter à part, dans
l'analyse. **Période de référence propre : depuis le 6 novembre 2026 à
11:53** (ADR désactivé des deux côtés, puissance relue avant chaque
émission, plus de downlinks en boucle).

**Fenêtres d'exclusion** (gateway fixe hors service ou dégradée, voir [`gateway.md`](gateway.md)) :

| Début | Fin | Cause |
|---|---|---|
| 2026-11-03 13:15 | 2026-11-03 14:10 | Réception dégradée (RSSI médian des trames étrangères −120 dBm au lieu de −107, trafic divisé par 4) ; cause non établie. Avant le régime 1a |
| 2026-11-03 15:58:15 | 2026-11-03 16:21:04 | LoRa restée désactivée après une micro-coupure du backhaul (relance du netwatch en échec) |
| 2026-11-03 16:21:04 | 2026-11-03, vers 17:00 | Réception dégradée, même signature qu'à 13:15 ; fin au déplacement de la gateway (heure exacte non relevée, première trame d'une mote à 17:04:59) |
| 2026-11-03 16:22:59 | 2026-11-03 16:23:25 | Relance de la LoRa à l'installation du nouveau netwatch |
| 2026-11-04 08:53:06 | 2026-11-04, vers 08:53:32 | Relance de la LoRa par le netwatch après une micro-coupure du backhaul (9 s), sans intervention sur la gateway |
| 2026-11-04 09:01:47 | 2026-11-04, vers 09:02:13 | Idem (micro-coupure de 9 s) |
| 2026-11-04 13:23:40 | 2026-11-04 13:25:53 | Coupure du backhaul (79 s, plus de statistiques reçues de 13:24:29 à 13:25:53), puis relance de la LoRa |
| 2026-11-04 17:43:53 | 2026-11-04 17:46:35 | Coupure du backhaul (2 min), puis relance de la LoRa |
| 2026-11-04 18:41:46 | 2026-11-04, vers 18:42:21 | Micro-coupure de 9 s, puis relance de la LoRa |
| 2026-11-06 10:53:02 | 2026-11-06, vers 10:54:27 | Coupure du backhaul (1 min), puis relance de la LoRa. Avant la période de référence |
| 2026-11-06 11:28 | 2026-11-06 11:41 | Essai au banc avec la mote 1 à côté de la gateway : 80 paquets SF7 et SF8 reçus à −35 dBm environ, qui ont pu masquer des paquets faibles des motes installées |
| 2026-11-06 11:52:31 | 2026-11-06, vers 11:52:40 | Redémarrage de ChirpStack (désactivation de l'ADR) |
| 2026-11-09 22:29:45 | 2026-11-09 22:33:27 | Coupure du backhaul (3 min, plus de statistiques reçues de 22:30:44 à 22:33:27), puis relance de la LoRa à 22:32:45 |
| 2026-11-10 11:35:34 | 2026-11-10, vers 11:36:09 | Micro-coupure du backhaul (9 s), puis relance de la LoRa à 11:35:43 |
| 2026-11-11 16:07:30 | 2026-11-11 16:09:30 | Redémarrage des conteneurs de la pile LoRaWAN par le propriétaire (démarrage à 16:08:44, heure d'arrêt inconnue : ± 1 min) |

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
- ⚠️ Constaté après coup : cette nuit tombe en partie dans les périodes où
  l'ADR des motes 4 et 5 était réactivé (voir la section Régime 1a). La
  gateway émettait aussi des downlinks de commandes MAC en boucle.

## Bilan après 2,7 jours (3–6 novembre 2026)

⚠️ Toujours préliminaire. Ces données incluent les périodes où l'ADR était
réactivé (puissance non garantie) et 130 à 275 downlinks par jour de
commandes MAC, pendant lesquels la gateway n'écoutait pas. Elles servent à
dégrossir, pas à conclure : la période de référence commence le 6 novembre à
11:53.

- **Période** : 2026-11-03 17:05 → 2026-11-06 10:40 (heure de Paris), avec
  les fenêtres d'exclusion du 4 novembre. Mote 5 : jusqu'au 5 novembre à
  10:43 (mote muette ensuite). Données copiées le 6 novembre vers 10:46.
- **Calcul** : `python Mote/src/bilan_regime_1a.py <dossier> --debut 2026-11-03T17:05 --fin 2026-11-06T10:40`,
  avec une option `--exclure DÉBUT/FIN` par fenêtre du 4 novembre.

| # | Nom | SF7 | SF8 | SF9 | SF10 | SF11 | SF12 | Émissions par SF |
|---|---|---|---|---|---|---|---|---|
| 2 | Forum Louis Lareng | 6 % | 18 % | 48 % | 75 % | 86 % | 87 % | environ 785 |
| 4 | Centre de biologie intégrative | 0 % | 0 % | 0 % | 0,4 % | 12 % | 22 % | environ 772 |
| 5 | Bâtiment 4R1 | 0,2 % | 1 % | 9 % | 31 % | 48 % | 59 % | environ 497 |

Jour (8h–20h) et nuit (20h–8h), PDR en SF12 (SF11 entre parenthèses) :

| # | Nom | Jour | Nuit |
|---|---|---|---|
| 2 | Forum Louis Lareng | 87 % (85 %) | 87 % (87 %) |
| 4 | Centre de biologie intégrative | 27 % (15 %) | 18 % (10 %) |
| 5 | Bâtiment 4R1 | 41 % (36 %) | 73 % (57 %) |

**Lecture**

- **Toujours aucune mote à 90 %.** Le Forum plafonne à 85–89 % en SF12 selon
  les jours, malgré environ 8 dB de marge : les pertes ne viennent pas du
  SNR. La période de référence (sans downlinks) dira quelle part venait des
  émissions de la gateway et quelle part des collisions avec les autres
  réseaux LoRa du campus.
- **4R1 : l'effet de l'heure se confirme** sur plusieurs jours, avec un lien
  nettement meilleur la nuit.
- **CBI** : stable mais très bas (22 % en SF12). Son maintien dans
  l'expérience est à discuter.

## Période de référence (6–9 novembre 2026)

Premiers résultats sans biais connu : ADR désactivé côté serveur et côté
mote, puissance relue avant chaque émission, plus de downlinks en boucle.

- **Période** : 2026-11-06 11:53 → 2026-11-09 14:10 (heure de Paris), soit
  environ 3,1 jours, dont un week-end complet. Aucune fenêtre d'exclusion :
  pas de trou dans les statistiques de la gateway, aucune reconnexion,
  aucune relance de la LoRa. Données copiées le 9 novembre vers 14:18.
- **Calcul** : `python Mote/src/bilan_regime_1a.py <dossier> --debut 2026-11-06T11:53 --fin 2026-11-09T14:10`.
- **Contrôles** : aucune ligne `adr` ni `pwridx` dans les journaux (ADR et
  puissance jamais modifiés) ; 37, 75, 3 puis 1 downlinks par jour du 6 au
  9 novembre (les derniers `NewChannelReq` en attente pour la mote 4, puis
  quasiment plus rien) ; 15 001 trames étrangères reçues, RSSI médian
  −103 dBm. La mote 5 s'est bloquée deux fois, relancée chaque fois en 24 s
  par la reprise automatique (voir la section Régime 1a).

| # | Nom | SF7 | SF8 | SF9 | SF10 | SF11 | SF12 | SNR médian SF12 (reçus) |
|---|---|---|---|---|---|---|---|---|
| 2 | Forum Louis Lareng | 2 % | 31 % | 62 % | 81 % | 87 % | 84 % | −10 dB |
| 4 | Centre de biologie intégrative | 0 % | 0 % | 0 % | 0,2 % | 8 % | 19 % | −17 dB |
| 5 | Bâtiment 4R1 | 0 % | 0,5 % | 18 % | 45 % | 61 % | 70 % | −14 dB |

Environ 890 émissions par SF et par mote.

PDR en SF12 selon le moment (SF11 entre parenthèses) :

| # | Nom | Semaine, jour (8h–20h) | Semaine, nuit | Week-end, jour | Week-end, nuit |
|---|---|---|---|---|---|
| 2 | Forum Louis Lareng | 88 % (90 %) | 78 % (87 %) | 83 % (87 %) | 85 % (84 %) |
| 4 | Centre de biologie intégrative | 19 % (7 %) | 12 % (8 %) | 24 % (11 %) | 18 % (6 %) |
| 5 | Bâtiment 4R1 | **22 %** (9 %) | 73 % (51 %) | **84 %** (83 %) | 83 % (76 %) |

Environ 145 à 290 émissions par case et par SF. « Semaine » : le vendredi
6 novembre de 11:53 à minuit et le lundi 9 novembre de minuit à 14:10.
« Week-end » : samedi et dimanche, de minuit à minuit.

**Lecture**

- **Toujours aucune mote à 90 %** : aucun SF minimal fiable au sens de la
  définition actuelle. Le Forum plafonne à 84–88 % selon les jours.
- **4R1 : effet des jours ouvrés.** En SF12, 22 % le jour en semaine contre
  84 % le jour le week-end, et 73 à 83 % la nuit. Le lundi 9 novembre au
  matin, de nouveau 42 %. Le lien s'effondre pendant les heures de travail :
  activité humaine dans le bâtiment (équipements du service électronique,
  brouillage, personnes, portes) plutôt que propagation. À confirmer sur
  plusieurs semaines ; cela impose au moins une semaine complète par
  configuration.
- **Forum : SF12 passe moins bien que SF11** (84 % contre 87 %), chaque
  jour, alors que SF12 a plus de marge de SNR. Un paquet SF12 dure deux fois
  plus longtemps (environ 1,2 s contre 0,6 s) et s'expose donc davantage aux
  collisions : cela renforce l'hypothèse des collisions avec les autres
  réseaux LoRa du campus.
- **Le correctif ADR n'a pas amélioré le SF12 du Forum** (87 % sur la
  période précédente, 84 % ici) : les downlinks n'étaient pas la cause
  principale de ses pertes. SF9 et SF10 progressent (48 → 62 %, 75 → 81 %),
  sans qu'on puisse séparer l'effet du correctif de celui du week-end.
- **CBI** : stable mais très bas, de 15 à 22 % en SF12 selon les jours.
- **Mote 5** : 3 blocages en 5 jours (5, 7 et 8 novembre ; un 4e le
  10 novembre à 15:03, voir [`Mote/mote.md`](../Mote/mote.md)), contre aucun pour
  les motes 2 et 4. Sans la reprise automatique, le week-end aurait été
  perdu sur ce site.

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
