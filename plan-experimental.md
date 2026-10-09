# Plan expérimental — Gateway fixe et gateway mobile en LoRaWAN

> Document de travail, rédigé le 9 octobre 2026. Il récapitule le plan d'expérience défini à ce jour. Les valeurs marquées « à confirmer » dépendent des mesures de la phase 0.

## Sommaire

1. [Contexte et objectif](#1-contexte-et-objectif)
2. [Question de recherche et contribution](#2-question-de-recherche-et-contribution)
3. [État de l'art et positionnement](#3-état-de-lart-et-positionnement)
4. [Hypothèses](#4-hypothèses)
5. [Dispositif expérimental](#5-dispositif-expérimental)
6. [Le mécanisme de sonde](#6-le-mécanisme-de-sonde)
7. [Plan phase par phase](#7-plan-phase-par-phase)
8. [Méthode de test de H1](#8-méthode-de-test-de-h1)
9. [Modèle énergétique et banc PPK2](#9-modèle-énergétique-et-banc-ppk2)
10. [Indicateurs et statistiques](#10-indicateurs-et-statistiques)
11. [Dimensionnement : temps d'émission et duty cycle](#11-dimensionnement--temps-démission-et-duty-cycle)
12. [Risques et parades](#12-risques-et-parades)
13. [Points ouverts](#13-points-ouverts)
14. [Constats techniques en cours](#14-constats-techniques-en-cours)
15. [Références](#15-références)

---

## 1. Contexte et objectif

- **Cadre** : thèse CIFRE, première année. L'objectif est de produire des résultats expérimentaux pour un papier de **conférence principale** (pas un workshop). Les échéances visées sont janvier ou mars 2027. Mars 2027 est l'objectif réaliste pour la version complète.
- **Principe** : on ne précipite pas l'expérience. Si elle le justifie, la publication peut être retardée.
- **Expérience** : comparer une **gateway fixe** (toit de l'IRIT, au centre du campus) et une **gateway mobile** (à vélo ou à trottinette) dans un réseau LoRaWAN, avec 6 motes réparties dans 6 bâtiments du campus Paul Sabatier, à Toulouse.
- Le titre de la thèse (« dorsales éphémères ») n'est pas une contrainte : le sujet peut être adapté aux résultats.

## 2. Question de recherche et contribution

**Question**

> Dans un réseau LoRaWAN réel, peut-on exploiter une gateway mobile de passage pour réduire le coût radio des motes, sans perdre de données et avec une latence bornée, grâce à un mécanisme compatible LoRaWAN Class A ?

**Pourquoi ne pas se limiter à « fixe contre mobile »**

Montrer seulement que la gateway mobile, plus proche, obtient un meilleur RSSI ou PDR serait jugé trivial. L'intérêt scientifique est dans le **compromis** :

- la mobilité permet un SF plus bas, donc moins de temps d'émission et moins d'énergie ;
- en échange, il y a des fenêtres de contact limitées, de la latence, et des émissions perdues hors contact.

**Contribution visée (ambition « C »)**

> Première évaluation **en conditions réelles**, avec **LoRaWAN standard (Class A)** et du **matériel du commerce**, d'un mécanisme de détection opportuniste d'une gateway mobile. Elle repose sur une **comparaison appariée** fixe/mobile (les mêmes paquets reçus par les deux gateways) avec **plusieurs SF**, et quantifie le compromis **énergie, latence et taux de livraison**.

La plus-value principale est l'**expérimentation réelle** : la grande majorité des travaux existants sont des simulations.

## 3. État de l'art et positionnement

### Papiers lus en détail (dossier `papers/`)

| | Florita et al. 2020 | MLoRaDrone, Chen et al. 2023 | Tang et al. 2025 |
|---|---|---|---|
| Revue | Computer Communications 154 | Computer Networks 237 | Scientific Data 12:1464 |
| Réel ou simulé | Réel minimal (**2 motes**, 1 à 2 voitures, 18 tournées) et passage à l'échelle simulé (ns-3) | **100 % simulé** | Réel : 28 motes, 3 gateways au sol et 1 drone |
| Gateway mobile | Oui, en voiture à 30 km/h | Drones simulés, vol stationnaire en des points prévus | **Non** : le drone reste en vol stationnaire |
| Protocole | **LoRa brut, MAC propriétaire**, pas LoRaWAN | LoRa, MAC propriétaire | LoRaWAN standard |
| SF | **SF7 uniquement** | Optimisé en simulation | **Un seul SF** (11 ou 12, le papier se contredit) |
| Détection de la gateway | Balise envoyée selon la **position GPS des motes, connue à l'avance**. La mote **écoute en permanence** | CAD à des **heures de passage convenues à l'avance** | Aucune |
| Énergie | **Non mesurée** (les motes ne dorment jamais, ce que les auteurs reconnaissent) | Modèle de propagation, jamais mesurée | Non traitée |
| Bande | 915 MHz, sans duty cycle | — | 470 MHz (Chine) |

**Les failles qu'on peut exploiter**

- **Florita** : c'est le travail le plus proche de notre idée. Mais son mécanisme sort du standard, les motes écoutent en permanence (aucune économie d'énergie), les gateways doivent connaître la position des motes, et la comparaison avec un comportement Class A n'existe qu'en simulation.
- **MLoRaDrone** : tout est simulé. Leurs travaux futurs citent explicitement « *real-world experiments* ».
- **Tang et al.** : pas de vraie mobilité, un seul SF, aucun mécanisme. Résultat utile : en intérieur, l'altitude la plus haute n'est pas la meilleure, ce qui montre que la géométrie compte plus que la seule proximité.

### Autres travaux repérés (lus en résumé seulement)

- Panga & Borkotoky (ConTEL 2023) : wake-up radio pour un drone-gateway, avec matériel supplémentaire, en simulation, comparée aux balises Class B.
- Uplinks déclenchés par balise Class B pour l'IoT par satellite (arXiv 2409.20408) : même logique que la nôtre, mais en simulation.
- ADR et mobilité (traces d'Anvers, WCNC 2023) : l'ADR se dégrade quand la mobilité augmente, mais ces études portent sur des **motes** mobiles, pas sur une gateway mobile.
- Peu de travaux avec une **gateway au sol mobile** qui collecte des motes fixes en intérieur : la littérature est dominée par les drones.

### Positionnement

| | Expérimentation | LoRaWAN standard | Plusieurs SF | Énergie mesurée |
|---|---|---|---|---|
| Florita et al. 2020 | Réelle (2 motes) | Non | Non (SF7) | Non |
| MLoRaDrone 2023 | Simulation | Non | Oui | Non (modèle) |
| Tang et al. 2025 | Réelle (drone immobile) | Oui | Non (1 SF) | Non |
| **Notre travail** | **Réelle (6 motes, 2 gateways)** | **Oui** | **Oui (SF7 → SF12)** | **Oui (PPK2)** |

> À faire : compléter l'état de l'art sur Google Scholar et IEEE Xplore (*mobile gateway LoRaWAN*, *data mule LoRa*, *gateway discovery LPWAN*, *opportunistic uplink LoRa*), et regarder qui cite Florita 2020.

## 4. Hypothèses

- **H1 (caractérisation)** : pendant un passage, le SF minimal fiable vers la gateway mobile est **au moins deux crans plus bas** que vers la gateway fixe, pour une partie des motes. Testée en phase 1.
- **H2 (coût de l'aveuglement)** : une mote qui émet périodiquement en SF bas sans savoir si la gateway mobile est là gaspille une part de ses émissions à peu près égale à la part du temps passée hors contact. Testée en phase 1, puis en phase 2.
- **H3 (le mécanisme)** : la stratégie de sonde consomme moins d'énergie par donnée livrée que la stratégie « fixe seule », avec un taux de livraison au moins égal et une latence bornée grâce au repli. Testée sur traces, puis en phase 2.

**Pourquoi deux crans** : chaque cran de SF double à peu près le temps d'émission. Passer de SF9 (185 ms) à SF7 (51 ms) divise le temps d'émission par **3,6**. Un gain d'un seul cran risquerait d'être absorbé par le coût des sondes.

## 5. Dispositif expérimental

| Élément | Configuration |
|---|---|
| Motes | 6 × Microchip RN2483 dans 6 bâtiments (bureaux de collègues, pas de sous-sol), chacune pilotée en USB par un **Raspberry Pi** accessible en SSH |
| Gateway fixe | Toit de l'IRIT, rattachée au même ChirpStack. **Modèle à identifier.** On suppose le même modèle que la gateway mobile |
| Gateway mobile | MikroTik wAP LR8 (RouterOS 7.24) à vélo ou à trottinette, reliée en **4G** par carte SIM. Alimentation à trouver |
| GPS | Téléphone avec une appli d'enregistrement GPX, horloges synchronisées (NTP d'un côté, GPS de l'autre) |
| Serveur | ChirpStack v4, avec le collecteur qui enregistre **une ligne par gateway réceptrice** dans PostgreSQL, puis Grafana |
| Radio | EU868, BW 125 kHz, CR 4/5, **ADR désactivé**, **puissance d'émission fixe**, **mêmes 8 canaux** sur les deux gateways |
| Parcours | Boucle d'environ **2 km** passant près des 6 bâtiments : environ 8 min à vélo, soit environ 15 boucles par tournée de 2 h. Ne pas la raccourcir |

**Avantage de deux gateways identiques** : les écarts mesurés viennent de la position et de la mobilité, pas du matériel.

**Principe clé : la comparaison appariée.** Chaque paquet porte son SF et un numéro de séquence. Comme les deux gateways écoutent en même temps, on sait pour chaque paquet s'il a été reçu par l'IRIT, par la gateway mobile ou par les deux, avec RSSI, SNR et position GPS. C'est le même signal, au même instant, dans les mêmes conditions.

## 6. Le mécanisme de sonde

### Le problème
La mote ne sait pas quand la gateway mobile passe. Les deux choix naïfs :

- émettre en SF élevé vers la gateway fixe : fiable mais coûteux ;
- émettre en SF7 à l'aveugle : la plupart des paquets partent dans le vide.

### Le principe : la sonde transporte les données
La **sonde** n'est pas un petit message de test suivi d'un envoi : c'est **directement le message de données**. Toutes les T_p, la mote envoie un **uplink confirmé en SF7 contenant tout son tampon**, c'est-à-dire toutes les données accumulées depuis la dernière livraison réussie.

```
Période D (exemple : D = 10 min, T_p = 2 min)

0 ──── T_p ──── 2 T_p ──── 3 T_p ──── 4 T_p ──── D ──►  temps

Mote 1 (gateway mobile rencontrée)
        SF7 ✗   SF7 ✗      SF7 ✓ ACK  → tampon vidé, nouveau cycle

Mote 2 (gateway mobile jamais rencontrée)
        SF7 ✗   SF7 ✗      SF7 ✗      SF7 ✗      Repli au SF fixe vers l'IRIT
```

**La règle**

1. Toutes les T_p, la mote envoie ses données dans un message confirmé en SF7.
2. ACK reçu : données livrées, tampon vidé, un nouveau cycle commence.
3. Pas d'ACK : les données restent dans le tampon, nouvel essai à la T_p suivante.
4. D atteint sans ACK : envoi au SF fixe (par exemple SF12) vers la gateway de l'IRIT. Le délai est borné par D.

**Propriétés**

- **LoRaWAN Class A strictement standard** : la mote ne reçoit que juste après avoir émis, et c'est l'émission de la sonde qui ouvre les fenêtres RX1 et RX2. Il n'y a pas d'écoute permanente, contrairement à Florita, et **l'ACK LoRaWAN standard suffit** : si une gateway, quelle qu'elle soit, reçoit le message en SF7, les données sont livrées. Comme les motes sont choisies là où le SF7 passe mal vers l'IRIT, un ACK signifie en pratique que la gateway mobile est passée. Le filtrage côté serveur (ne répondre que si la gateway mobile a reçu) n'est plus nécessaire dans ce cadrage.
- **Une sonde réussie ne coûte rien de plus qu'un envoi normal** : il n'y a pas de second message.
- **Repli** : la latence reste bornée par D et le taux de livraison est au moins celui de la gateway fixe seule. LoRaWAN ne garantit pas la livraison ; on vise « au moins aussi bien que la gateway fixe ».

### Le budget de sondes et le seuil de rentabilité
- **Même une sonde réussie coûte quelque chose.** La sonde n'est rentable que si, sur une période D, le coût des sondes reste inférieur au coût d'un message au SF de repli.
- Avec les temps d'émission (6 octets de données), un message coûte, en équivalents SF7 : SF12 ≈ 26, SF11 ≈ 14, SF10 ≈ 6,4, SF9 ≈ 3,6, SF8 ≈ 2. Avec 5 sondes par période, la sonde est largement rentable si le repli est en SF12, tout juste en SF10, et perdante en SF9 ou SF8.
- On fixe donc un **budget k de sondes par période D**, **propre à chaque mote** selon son SF de repli. Exemple : D = 10 min, T_p = 2 min, k = 4.
  - **Meilleur cas** (gateway mobile présente) : une sonde SF7 de 51 ms au lieu d'un SF12 de 1,32 s.
  - **Pire cas** (gateway jamais rencontrée) : k sondes ratées (≈ 0,21 s) **en plus** du repli. Le surcoût est **borné**.
- **Le risque n'est pas que la gateway passe trop souvent, mais trop rarement.** Le papier doit tracer le **gain d'énergie en fonction de la probabilité de croiser la gateway mobile pendant D**, pour chaque SF de repli, avec le seuil de rentabilité.
- Avec un budget k, on peut aussi échanger de la fraîcheur des données (AoI) contre de l'énergie : ne sonder que lorsque le tampon est assez plein, ou attendre après un vidage réussi. Seul le délai maximal D est imposé.

**Le calcul**, pour une même quantité de données livrées :

- E_B1 = n_données × E(SF fixe)
- E_P = n_ratées × E_ratée + n_réussies × E_réussie + E_replis

Le banc PPK2 donne les coûts unitaires E ; le terrain (phase 1, puis phase 2) donne les nombres n.

### Contenu et taille des messages
- **Limites de charge utile en EU868** : 222 octets en SF7 et SF8, 115 octets en SF9, **51 octets de SF10 à SF12**. Le repli en SF élevé est donc le facteur limitant : au-delà de 51 octets accumulés pendant D, il faudrait plusieurs messages de repli, chacun suivi d'environ 2 minutes d'attente (duty cycle). Il faut dimensionner ensemble la taille d'une mesure, sa période et D. Exemple : 6 octets toutes les 2 min avec D = 10 min, soit 30 octets.
- **Le coût d'une sonde augmente quand le tampon se remplit** :

  | Données | SF7 | SF12 |
  |---|---|---|
  | 6 octets | 51 ms | 1,32 s |
  | 20 octets | 72 ms | 1,81 s |
  | 51 octets | 118 ms | 2,79 s |

  Le banc PPK2 mesure donc la sonde à plusieurs tailles. Variante à évaluer : une sonde minimale tant qu'aucun ACK n'est reçu, puis l'envoi des données (moins cher par sonde ratée, mais un second message en cas de succès).
- **Doublons** : un ACK perdu ne signifie pas que les données sont perdues. La charge utile contient donc **un identifiant par mesure** (numéro de séquence ou horodatage), et le serveur élimine les doublons.

### Les stratégies comparées en phase 2

| Stratégie | Rôle | Comportement | Ce qu'elle mesure |
|---|---|---|---|
| **B1 — Fixe** | Référence | Un message toutes les D, au SF minimal fiable vers l'IRIT, avec toutes les données de la période | Le coût de référence |
| **B2 — Mobile aveugle** | Témoin | Toutes les T_p, un message SF7 sans ACK, sans repli | Le gaspillage d'une émission à l'aveugle (H2) |
| **P — Sonde** | Notre mécanisme | Toutes les T_p, un message SF7 confirmé avec tout le tampon ; repli à D vers l'IRIT | Le gain d'énergie avec un délai borné (H3) |

Les trois stratégies transmettent **le même flux de données** : la comparaison d'énergie n'est valable qu'à volume égal.

### Cadrage retenu
La gateway de l'IRIT est **conservée comme référence** (stratégie B1) et comme **cible du repli**. La gateway mobile est exploitée **en plus** de la gateway fixe.

## 7. Plan phase par phase

### Vue d'ensemble

| Phase | Dates | Objectif |
|---|---|---|
| **0** | 8 → 25 oct. 2026 | Tout préparer et valider avant le déploiement |
| **1** | 26 oct. → 22 nov. 2026 | Caractériser les liens fixe et mobile |
| **Intermédiaire** | 23 nov. → 20 déc. 2026 | Concevoir et régler la sonde à partir des traces |
| **2** | 4 → 31 janv. 2027 | Évaluer le mécanisme en réel |
| **3** | févr. → mi-mars 2027 | Analyser et rédiger, puis **soumettre en mars 2027** |

### Phase 0 — Préparation (8 → 25 oct. 2026)

**0a. Balade de repérage de la couverture de l'IRIT**

- **Objectif** : choisir des emplacements où le lien SF7 vers l'IRIT est **faible ou peu fiable**. Ce n'est pas une preuve, c'est un choix d'emplacements.
- **Procédure** :
  - une mote et un ordinateur portable, à l'intérieur des bâtiments, aux types d'emplacements visés ;
  - mote posée sur un support, pas tenue à la main ;
  - 20 paquets SF7 par point, en respectant le duty cycle (un paquet toutes les 6 s au moins) ;
  - si le résultat est mauvais, recommencer en SF8, puis en SF9 ;
  - noter l'heure, le bâtiment, l'étage et le côté du bâtiment ;
  - mesurer aussi deux ou trois emplacements difficiles, pour avoir des options de repli.
- **Lecture des résultats** : PDR et SNR dans la base, filtrés sur la gateway de l'IRIT, et non `mac_tx_ok` (qui signifie seulement que la mote a émis).

| SF7 vers l'IRIT | Interprétation |
|---|---|
| PDR ≥ 90 % et SNR > −2 dB | Couverture confortable, peu d'intérêt pour la gateway mobile |
| PDR ≥ 90 % mais SNR entre −2 et −7,5 dB | Marge faible, lien fragile sur plusieurs semaines |
| PDR < 90 % | **Emplacement cible** |

- **Bonus** : une carte de couverture SF7 du campus, utilisable comme figure de contexte.
- **Si tout passe en SF7** : déployer plus loin (des options existent) ou dans des emplacements plus difficiles.

**0b. Banc de mesure d'énergie (PPK2)** : voir la [section 9](#9-modèle-énergétique-et-banc-ppk2).

**0c. Vérifications de l'infrastructure**

- Les deux gateways écoutent **les mêmes 8 canaux EU868** dans ChirpStack.
- Le **downlink via la 4G** arrive dans la fenêtre RX1. Sinon, il faut allonger `rx1_delay` (voir la [section 14](#14-constats-techniques-en-cours)).
- L'**ACK arrive dans la fenêtre RX1** pour les deux gateways (voir le `mac_err` de la [section 14](#14-constats-techniques-en-cours)).
- La trace GPS s'enregistre, avec des horloges synchronisées.

**0d. Déploiement et tournée pilote**

- Installation des 6 motes et de leurs Raspberry Pi.
- Tournée pilote : 2 ou 3 boucles, motes en balayage SF7 → SF9.
- **Question à trancher** : quelle part de chaque boucle chaque mote passe-t-elle à portée SF7 de la gateway mobile ? Si le contact est presque permanent, la gateway mobile se comporte comme une gateway plus proche et la sonde perd son intérêt. Il faudra alors ajuster les emplacements ou baisser la puissance d'émission.

**Livrables de la phase 0** : emplacements validés, modèle d'énergie, infrastructure vérifiée, durée des contacts.

### Phase 1 — Caractérisation (26 oct. → 22 nov. 2026, 4 semaines)

Les deux gateways sont actives, l'ADR est désactivé et la puissance d'émission est fixe. Les Raspberry Pi basculent automatiquement entre deux régimes selon les plages horaires des tournées.

| | Régime 1a | Régime 1b |
|---|---|---|
| Quand | En continu, 24 h/24 | Pendant les tournées à vélo |
| SF | Balayage **entrelacé** SF7 → SF12 | Balayage SF7 → SF9 |
| Mode | Sans ACK | **Avec ACK, sans retransmission** (`mac set retx 0`) |
| Cadence | Un cycle toutes les 4 min 30 environ | Un cycle toutes les 34 s environ (17 s si on répartit sur deux sous-bandes) |
| Volume | ≈ 9 000 cycles par mote | ≈ 150 passages par mote |
| Sert à | **SF minimal fiable vers la gateway fixe**, donc le coût du repli | SF mobile, comparaison appariée, durée des contacts, fiabilité des sondes, traces pour le simulateur |

- **Tournées** : 2 à 3 par semaine, soit environ 10 tournées de 2 h et environ 15 boucles chacune.
- **SF10 à SF12 ne sont pas utilisés en 1b** : tout l'intérêt de la gateway mobile est de permettre un SF bas, et ils épuiseraient le duty cycle.
- **SF7 à SF9 sont confirmés en 1b** pour mesurer la fiabilité réelle des accusés, qui serviront de réponse aux sondes. SF10 à SF12 restent non confirmés pour ne pas épuiser le duty cycle des gateways.
- **Pourquoi entrelacer** : avec des blocs (une heure par SF), chaque SF voit des conditions différentes (heure, trafic, météo). Avec l'entrelacement, tous les SF voient les mêmes conditions. `sf_test_campaign.py` procède aujourd'hui par blocs et devra être adapté.
- **Pourquoi sans ADR** : l'ADR de ChirpStack décide à partir du meilleur SNR sur une vingtaine d'uplinks, toutes gateways confondues. Avec une gateway mobile, le canal change plus vite que cette fenêtre : l'ADR serait une variable parasite.
- **Atout majeur** : le balayage permet de **rejouer hors ligne** n'importe quelle stratégie (SF fixe, oracle, ADR simulé, sonde). Des données collectées avec l'ADR ou un SF fixe ne pourraient pas être réanalysées.

**Les objectifs du régime 1b**

Le régime 1a répond à « combien coûte la gateway fixe pour chaque mote ? ». Le régime 1b répond à « que vaut réellement la gateway mobile, pendant combien de temps, et avec quelle fiabilité ? » :

1. **SF minimal fiable vers la gateway mobile** au cœur du passage (deuxième moitié de H1), et courbes de PDR selon la distance.
2. **Comparaison appariée** : pour chaque paquet, reçu par l'IRIT, par la gateway mobile ou par les deux (McNemar, ΔSNR).
3. **Durée des fenêtres de contact** en SF7, passage par passage. C'est l'objectif le plus important pour la suite : elle fixe T_p (si un contact dure 90 s et qu'on sonde toutes les 2 min, on rate des passages).
4. **Fiabilité réelle de la sonde** : chaque paquet confirmé sans retransmission se comporte comme une sonde. On mesure la probabilité que l'uplink arrive **et** que l'ACK revienne à temps (via la 4G pour la gateway mobile), et la part d'ACK perdus (doublons).
5. **Traces pour le simulateur** : avec un essai SF7 toutes les 34 s environ, on sait à chaque instant si une sonde aurait réussi.

Le régime 1b **ne fait pas tourner le mécanisme** : c'est une mesure de caractérisation. Le mécanisme complet est évalué en phase 2.

**Résultats attendus**

- SF minimal fiable par mote et par gateway ;
- courbes de PDR selon la distance, par SF (gateway mobile) ;
- durée des fenêtres de contact ;
- fiabilité des accusés de réception ;
- carte de couverture du campus ;
- ADR simulé sur les traces. Résultat bonus possible : l'ADR est inadapté à une gateway mobile.

### Phase intermédiaire — Conception de la sonde (23 nov. → 20 déc. 2026)

- **Simulateur sur traces** : rejouer B1, B2 et P (sonde porteuse des données, budget k par SF de repli) et l'ADR sur les traces de la phase 1.
- **Simuler des passages plus rares** en ne gardant qu'une boucle sur *k*. Avec un passage toutes les 8 min, la latence serait artificiellement bonne. On obtient la **courbe du gain selon la fréquence de passage**, avec le seuil de rentabilité.
- **Fixer les paramètres** :
  - **T_p** : inférieure à la durée d'un contact mesurée en 1b ;
  - **k** : pour chaque mote, d'après son SF de repli (1a) et le coût d'une sonde ratée (PPK2) ;
  - **D** : compatible avec le volume de données (limite de 51 octets au repli) ;
  - **le format des données**, avec un identifiant par mesure ;
  - **le flux de données**, identique pour toutes les stratégies (par exemple 6 octets toutes les 2 min).
- **Implémenter** la stratégie P sur les Raspberry Pi et la tester au labo.

### Phase 2 — Évaluation du mécanisme (4 → 31 janv. 2027)

**Objectif** : vérifier en réel que la sonde est rentable (H2 et H3) : moins d'énergie par donnée livrée que la gateway fixe seule, avec un délai borné par D et aucune donnée perdue. La phase 2 sert aussi à **valider le simulateur**.

- **Stratégies** : B1, B2 et P (voir la [section 6](#6-le-mécanisme-de-sonde)).
- **Protocole** : environ **12 tournées**, soit **4 par stratégie**, avec une **rotation contrebalancée**. Pendant une tournée, toutes les motes appliquent la même stratégie : répartir les motes entre stratégies mélangerait l'effet de la stratégie et celui de l'emplacement.
- Les deux gateways sont actives. L'IRIT sert de **référence** et de **cible du repli**.
- **Enregistrement** : journaux des Raspberry Pi (chaque envoi, son SF, ACK reçu ou non, contenu du tampon), réceptions dans la base, trace GPS.
- **Indicateurs** :
  - **l'énergie radio par donnée livrée** (journaux × coûts PPK2), indicateur principal ;
  - le taux de livraison des données ;
  - la latence de chaque donnée, qui doit rester inférieure à D ;
  - le temps d'antenne par donnée livrée ;
  - la réussite des sondes et la part de doublons.
- **Lien avec le simulateur** : les tournées (un passage toutes les 8 min) représentent le cas des passages fréquents. Si le simulateur prédit correctement les mesures réelles, il peut extrapoler de façon crédible aux passages rares.
- **Figures attendues** : énergie par donnée livrée par stratégie et par mote selon le SF de repli ; distribution des latences avec la borne D ; courbe du gain selon la fréquence de passage, simulée et confirmée par les points réels.
- **Point à trancher** : mesurer uniquement pendant les tournées (simple, mais seulement le cas des passages fréquents), ou faire tourner chaque stratégie sur une journée complète contenant une tournée (plus réaliste : on mesure aussi les replis pendant les heures sans passage). Préférence : la journée complète, avec une rotation des stratégies par jour. À décider après la phase 1.
- **Les stratégies se comparent uniquement à l'intérieur de la phase 2**, à cause du biais saisonnier (chute des feuilles entre novembre et janvier).

### Phase 3 — Analyse et rédaction (févr. → mi-mars 2027)

- Statistiques regroupées par tournée.
- Soumission en conférence en **mars 2027**. Janvier n'est pas réaliste pour la version complète avec le mécanisme.

## 8. Méthode de test de H1

**SF minimal fiable** : le plus petit SF dont le PDR atteint au moins **90 %**. Qu'un paquet SF7 passe une fois ne prouve rien.

1. **Vers la gateway fixe** (régime 1a) : PDR de chaque SF vers l'IRIT sur environ 9 000 cycles par mote. C'est une valeur stable.
2. **Vers la gateway mobile** (régime 1b) : on ne garde que les paquets émis **au cœur du passage** grâce au GPS, par exemple quand la gateway est à moins de 100 m. Le seuil sera fixé après la tournée pilote. On obtient aussi des courbes de PDR selon la distance.
3. **Comparaison appariée** sur les mêmes paquets SF7, pour chaque mote :

   | | IRIT : reçu | IRIT : non reçu |
   |---|---|---|
   | **Mobile : reçu** | les deux | **mobile seule** |
   | **Mobile : non reçu** | **IRIT seule** | aucune |

   Si la case « mobile seule » est nettement plus remplie que « IRIT seule », la gateway mobile fait mieux. Un **test de McNemar** dit si l'écart est significatif.

4. **Écart de SNR** : pour les paquets reçus par les deux gateways, ΔSNR = SNR mobile − SNR IRIT. Un cran de SF correspond à environ **2,5 dB** de sensibilité :

   | SF | 7 | 8 | 9 | 10 | 11 | 12 |
   |---|---|---|---|---|---|---|
   | Seuil de SNR (dB) | −7,5 | −10 | −12,5 | −15 | −17,5 | −20 |

   Un ΔSNR moyen de +5 dB correspond donc à environ deux crans gagnés. Limite : les gateways plafonnent la valeur du SNR quand le signal est très fort. Le RSSI servira alors de complément.

**Ce que H1 ne prouve pas** : que la gateway mobile vaille le coup globalement, puisqu'elle est absente la plupart du temps. C'est le rôle de H2 et H3. Il est normal que H1 soit fausse pour certaines motes : le papier dira **pour lesquelles** la gateway mobile est utile.

## 9. Modèle énergétique et banc PPK2

### Principe : mesurer une fois, compter ensuite
On ne mesure pas les motes sur le terrain : il faudrait un PPK2 par mote pendant des semaines.

1. **Banc** : mesurer une fois le coût de chaque action, en **millijoules par événement** (et non en watts).
2. **Terrain** : les Raspberry Pi enregistrent combien de fois chaque action a eu lieu.
3. **Analyse** : énergie = Σ (nombre d'actions × coût unitaire).

La fiche technique de la RN2483 ne suffit pas : elle donne quelques courants, mais pas le coût réel d'une séquence complète (réveil, émission, fenêtres RX1 et RX2, retour en veille).

### Montage
- PPK2 **en série** sur l'alimentation de la mote, entre le Raspberry Pi et la mote.
- Échantillonnage d'au moins **10 kHz**, pour voir les fenêtres de réception de quelques millisecondes.
- Idéalement, mesurer le **module RN2483 seul**. Sinon, mesurer la carte entière (PIC, écran, capteurs) au repos et soustraire. Il faut regarder le schéma de la carte.
- **Même puissance d'émission** que sur le terrain. Une seule valeur suffit, sauf si on décide de la baisser.
- Le **Raspberry Pi est exclu** du bilan énergétique. Il faudra le dire explicitement dans le papier.

### Événements à mesurer (30 à 50 répétitions chacun)

| Événement | SF | Pourquoi |
|---|---|---|
| Uplink sans ACK, séquence complète (émission + RX1 + RX2) | SF7 → SF12 | Coût d'un envoi de B1, de B2 et du repli |
| Sonde avec ACK reçu en RX1 | SF7 → SF9 | Coût d'une sonde **réussie** |
| Sonde sans ACK (RX1 et RX2 expirent) | SF7 → SF9 | Coût d'une sonde **ratée** : le paramètre clé |
| Veille (`sys sleep`) et repos | — | Coût de fond |

Comme la sonde transporte les données, les sondes et les envois au SF de repli sont mesurés **à plusieurs tailles de charge utile** (par exemple 6, 20 et 51 octets).

### La question clé : combien coûte une sonde ratée ?
Hors contact, la plupart des sondes échouent. En EU868, la fenêtre RX2 est par défaut en **SF12** (`rx2_dr=0` dans `region_eu868.toml`). Une sonde ratée pourrait donc coûter plus cher que l'émission SF7 elle-même. Si c'est le cas, P peut perdre contre B1. Le banc répond à cette question **dès octobre**. Si nécessaire, on réglera le débit de RX2 de façon cohérente entre ChirpStack et la mote (`mac set rx2`) et on espacera les sondes.

Bonus : une figure de courbe de courant annotée par type d'événement, pour le papier.

## 10. Indicateurs et statistiques

**Phase 1 (caractérisation)** : PDR, RSSI et SNR par mote, par SF et par gateway ; durée des contacts ; fiabilité des accusés.

**Phase 2 (mécanisme)**
- taux de livraison des **données**, après passage par le tampon ;
- latence entre la génération de la donnée et sa réception par le serveur ;
- **énergie radio par donnée livrée** (journaux du terrain combinés au modèle de la section 9) ;
- temps d'antenne par donnée livrée.

**Statistiques**
- L'**unité statistique est le passage** de la gateway devant une mote.
- Les passages d'une même tournée sont corrélés (même jour, même météo). On regroupe donc par tournée, avec un **bootstrap par tournée** ou un **modèle à effets mixtes**, pour ne pas surestimer la précision.

## 11. Dimensionnement : temps d'émission et duty cycle

Hypothèses : EU868, BW 125 kHz, CR 4/5, préambule de 8 symboles, CRC activé, 6 octets de données plus 13 octets d'en-tête LoRaWAN (19 octets PHY), optimisation bas débit à partir de SF11.

| SF | Temps d'émission | Intervalle minimal à 1 % |
|---|---|---|
| SF7 | 51,5 ms | 5,1 s |
| SF8 | 102,9 ms | 10,3 s |
| SF9 | 185,3 ms | 18,5 s |
| SF10 | 329,7 ms | 33,0 s |
| SF11 | 741,4 ms | 74,1 s |
| SF12 | 1 318,9 ms | 131,9 s |
| **Cycle SF7 → SF12** | **2,73 s** | **un cycle toutes les 273 s (≈ 4 min 30)** |
| **Cycle SF7 → SF9** | **0,34 s** | **un cycle toutes les 34 s** |

- Le duty cycle de **1 % est une obligation réglementaire** en EU868, pas un choix. Il se compte par sous-bande : répartir les émissions sur deux sous-bandes (868,0–868,6 MHz et 865–868 MHz) double le budget.
- `sf_burst_test.py` désactive le duty cycle. C'est acceptable en environnement fermé, **pas sur le campus**.
- Exemple de configuration hors limite : un paquet par SF toutes les 5 s (cycle de 30 s), soit environ 9 % d'occupation.

## 12. Risques et parades

| Risque | Gravité | Détecté par | Parade |
|---|---|---|---|
| Toutes les motes passent en SF7 vers l'IRIT | Élevée | Balade (0a) | Déployer plus loin ou à des endroits plus difficiles ; cadrage « zones sans infrastructure fixe » |
| La gateway mobile est à portée en permanence | Élevée | Tournée pilote (0d) | Ajuster les emplacements ou baisser la puissance d'émission (facteur secondaire, à justifier par le bilan de liaison) |
| Une sonde ratée coûte trop cher (RX2 en SF12) | Moyenne | Banc PPK2 (0b) | Régler RX2, espacer les sondes |
| Le downlink arrive trop tard pour RX1 (4G) | Moyenne | Vérifications (0c) | Allonger `rx1_delay` |
| Biais saisonnier (chute des feuilles) | Faible | — | Comparer les stratégies uniquement au sein de la phase 2 |
| Passages d'une même tournée corrélés | Faible | — | Statistiques regroupées par tournée |
| Reconfiguration de la gateway de l'IRIT par un tiers | À évaluer | — | Vérifier son statut et qui l'administre |

## 13. Points ouverts

- **Conférence visée** pour une soumission en mars 2027.
- **Gateway de l'IRIT** : modèle, gain et hauteur de l'antenne, longueur du câble, statut (partagée ou non).
- **Alimentation** de la MikroTik à vélo.
- **Accès aux bureaux** des collègues pour le déploiement et la maintenance.
- **Seuil de distance** définissant « le cœur du passage », à fixer après la tournée pilote.
- **Flux de données, T_p, k et D** pour la phase 2, à fixer pendant la phase intermédiaire.
- **Phase 2 : mesure pendant les tournées seulement, ou sur des journées complètes**, à décider après la phase 1.
- **Variante de sonde** (sonde minimale puis données, ou sonde porteuse des données), à trancher avec le banc PPK2.

## 14. Constats techniques en cours

### Accusé de réception non reçu (`mac_err`) lors des premiers tests

- **Symptôme** : `mac tx cnf 1 01` répond `ok` puis `mac_err`, alors que le message apparaît bien dans Grafana. L'uplink arrive, mais l'accusé ne revient pas à temps.
- **Indice** : le join OTAA réussit. L'acceptation du join utilise une fenêtre à **5 s**, alors que l'accusé d'un message utilise RX1 à **1 s** (`rx1_delay=1` dans `LoRaWAN-Infra/configuration/chirpstack/region_eu868.toml`). Avec environ 200 ms de déduplication dans ChirpStack et le délai réseau, l'accusé arrive probablement trop tard.
- **Diagnostic** : dans ChirpStack, onglet *Events* du device, regarder le statut de l'événement `txack` (`TOO_LATE`, `OK`…), ou l'onglet *LoRaWAN frames* de la gateway.
- **Si `TOO_LATE`** : passer `rx1_delay` à 3, redémarrer ChirpStack, **refaire `mac join otaa`** (le délai est transmis dans l'acceptation du join), puis vérifier avec `mac get rxdelay1` (attendu : `3000`).
- **Si `OK`** : la mote est peut-être trop près de la gateway, ce qui sature son récepteur. L'éloigner de quelques mètres.
- Ce réglage sera de toute façon nécessaire pour la gateway mobile en 4G.

### Rappels sur les commandes RN2483

| DR | 5 | 4 | 3 | 2 | 1 | 0 |
|---|---|---|---|---|---|---|
| SF | SF7 | SF8 | SF9 | SF10 | SF11 | SF12 |

- `mac set dr 6` renvoie `invalid_param` : DR6 (SF7 en 250 kHz) n'est pas activé sur les canaux. C'est normal.
- Message confirmé : `mac tx cnf <port> <hex>`. Réponses : `mac_tx_ok` (accusé reçu), `mac_rx <port> <données>` (accusé et downlink), `mac_err` (pas d'accusé).
- `mac set retx 0` : pas de retransmission automatique des messages confirmés.

## 15. Références

**Lues en détail**

- N. J. B. Florita, A. N. M. Senatin, A. M. A. Zabala, W. M. Tan, « Opportunistic LoRa-based gateways for delay-tolerant sensor data collection in urban settings », *Computer Communications*, vol. 154, pp. 410–432, 2020. DOI : 10.1016/j.comcom.2020.02.066
- C. Chen, J. Luo, Z. Xu, R. Xiong, D. Shen, Z. Yin, « Enabling large-scale low-power LoRa data transmission via multiple mobile LoRa gateways », *Computer Networks*, vol. 237, 110083, 2023. DOI : 10.1016/j.comnet.2023.110083
- W. Tang, H. Zhao et al., « Measurement of LoRa signal propagation in urban areas utilizing aerial gateway and ground gateway », *Scientific Data*, vol. 12, 1464, 2025. DOI : 10.1038/s41597-025-05802-2. Jeu de données : 10.6084/m9.figshare.28681874

**Repérées (résumés seulement)**

- S. M. S. Panga, S. S. Borkotoky, « Leveraging Wake-Up Radios in UAV-Aided LoRa Networks: Some Preliminary Results on a Random-Access Scheme », ConTEL 2023. https://arxiv.org/abs/2305.13810
- « Beacon based uplink transmission for LoRaWAN direct to satellite IoT », arXiv 2409.20408. https://arxiv.org/abs/2409.20408
- « Contact-Aware Opportunistic Data Forwarding in Disconnected LoRaWAN Mobile Networks », arXiv 2004.06614. https://arxiv.org/abs/2004.06614
- Évaluation de l'ADR en mobilité (traces d'Anvers) : https://medialibrary.uantwerpen.be/oldcontent/personalpage52076/files/lora.pdf
- ADR et mobilité, WCNC 2023 : https://sancy.iut.uca.fr/~durand/docs/WCNC23.pdf
- Spécification LoRaWAN L2 1.0.4 (LinkCheckReq, fenêtres de réception) : https://lora-alliance.org/wp-content/uploads/2021/11/LoRaWAN-Link-Layer-Specification-v1.0.4.pdf

**Support de présentation** (phases 0 et 1, pour les directeurs de thèse) : https://claude.ai/artifact/CDKfivjox7gLvguU3JwqEL
