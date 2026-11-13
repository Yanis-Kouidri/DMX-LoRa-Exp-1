# LoRaWAN-Infra

Stack Docker Compose du réseau LoRaWAN de l'expérience : serveur réseau
[ChirpStack](https://www.chirpstack.io) v4, collecte des trames dans
PostgreSQL et tableaux de bord Grafana. Elle tourne sur une instance AWS EC2
(région eu-west-1) et sert la région **EU868**.

## Services

| Service | Rôle | Port exposé |
|---|---|---|
| `chirpstack` | Serveur réseau LoRaWAN et interface web | `127.0.0.1:8080` (public via Caddy) |
| `chirpstack-gateway-bridge-basicstation` | Pont LoRa Basics Station (LNS), gateways authentifiées par certificat client | `3001` (public) |
| `chirpstack-rest-api` | API REST de ChirpStack | `127.0.0.1:8090` |
| `postgres` | Bases `chirpstack` (ChirpStack) et `lorawan_experiments` (expériences) | aucun |
| `redis` | Cache et sessions de ChirpStack | aucun |
| `mosquitto` | Broker MQTT entre le pont, ChirpStack et le collecteur | `127.0.0.1:1883` |
| `uplink-collector` | Enregistre dans `lorawan_experiments` les uplinks, les événements des devices et tout le trafic des gateways | aucun |
| `grafana` | Tableaux de bord | aucun (public via Caddy) |
| `caddy` | Reverse proxy HTTPS, certificats Let's Encrypt automatiques | `80`, `443` (public) |

Les versions des images sont fixées dans `docker-compose.yml`. Les services
non publics ne sont joignables que depuis l'instance (tunnel SSH si besoin).

Le pont Semtech UDP Packet Forwarder (port 1700) n'est pas déployé : ce
protocole ne permet pas d'authentifier les gateways.

## Accès

| Interface | Adresse |
|---|---|
| ChirpStack | https://chirpstack.kouidri.fr |
| Grafana | https://grafana.chirpstack.kouidri.fr |
| Gateways (Basics Station) | `wss://chirpstack.kouidri.fr:3001` |
| API REST | http://localhost:8090, depuis l'instance |

L'API gRPC de ChirpStack est à préférer à l'API REST.

## Arborescence

- `docker-compose.yml` : définition des services et des volumes.
- `Makefile` : commandes `make gateway-certs` et `make import-device-profiles`.
- `Caddyfile` : noms de domaine du reverse proxy.
- `.env.example` : variables d'environnement à renseigner dans `.env`.
- `scripts/gateway-certs.sh` : génération de la CA privée et du certificat
  serveur du pont Basics Station.
- `configuration/chirpstack/` : configuration de ChirpStack et des régions.
- `configuration/chirpstack-gateway-bridge/` : configuration du pont, une par
  région (seule `chirpstack-gateway-bridge-basicstation-eu868.toml` est
  utilisée).
- `configuration/mosquitto/` : configuration du broker MQTT.
- `configuration/postgresql/initdb/` : schéma complet, appliqué à la création
  du volume PostgreSQL.
- `configuration/postgresql/migrations/` : migrations à appliquer à la main sur
  une base existante.
- `configuration/grafana/` : source de données et tableaux de bord provisionnés.
- `configuration/certs/` : CA et certificats TLS (générés, non versionnés).
- `uplink-collector/` : collecteur MQTT vers PostgreSQL (Python).
- `regime1a/` : collecte automatique des journaux du régime 1a (script, liste
  des Pi, clé publique, unités systemd ; voir
  [Collecte automatique des journaux du régime 1a](#collecte-automatique-des-journaux-du-régime-1a)).
- `banc-ppk2/` : chargement des résultats du banc PPK2 dans la base (voir
  [Résultats du banc PPK2](#résultats-du-banc-ppk2)).
- `tailscale-policy.hujson` : copie versionnée de la politique d'accès du
  réseau Tailscale (voir [Accès Tailscale du serveur](#accès-tailscale-du-serveur)).

## Accès Tailscale du serveur

Depuis le 12 novembre 2026, l'instance EC2 fait partie du réseau Tailscale
des Pi. Objectif : que le serveur aille chercher lui-même les journaux du
régime 1a sur les Pi des motes (collecte par `rsync`, en lecture seule),
pour calculer le PDR en continu et l'afficher dans Grafana. Les Pi n'ont
aucun accès au serveur.

**Ce qui a été fait (12 novembre 2026)**

1. Politique d'accès réécrite dans la console Tailscale (Access controls),
   copie versionnée dans [`tailscale-policy.hujson`](tailscale-policy.hujson).
   Avant : une seule règle « tout autoriser » (`"src": ["*"], "dst": ["*"]`).
   Après :
   - les appareils du propriétaire entre eux : accès complet, comme avant ;
   - `tag:server` → **port 2222 des six Pi des motes uniquement** (désignés
     par leur adresse Tailscale dans la section `hosts`). D'abord le port 22,
     remplacé le jour même : voir la collecte ci-dessous ;
   - règle Tailscale SSH inchangée ;
   - des `tests` qui empêchent d'enregistrer une politique qui ouvrirait au
     serveur autre chose que le SSH des Pi des motes.
2. Tailscale 1.104.6 installé sur l'instance (script officiel
   `https://tailscale.com/install.sh`), puis :

   ```bash
   sudo tailscale up --advertise-tags=tag:server --accept-dns=false --hostname=chirpstack
   ```

   Connexion validée par le propriétaire du réseau via le lien affiché (pas
   de clé d'authentification, donc aucun secret échangé). `--accept-dns=false` :
   Tailscale ne touche pas à la résolution de noms du serveur, pour ne pas
   perturber les conteneurs (`/etc/resolv.conf` toujours sur `127.0.0.53`).
3. Résultat : appareil `chirpstack`, adresse **100.113.26.94**, tag
   `tag:server`, expiration de clé désactivée (défaut pour un appareil
   tagué). Tailscale SSH n'est pas activé sur le serveur : volontaire, on y
   entre par `ssh chirpstack-aws` comme avant.

**Vérifications (12 novembre 2026)**

| Depuis | Vers | Attendu | Résultat |
|---|---|---|---|
| serveur | port 22 de `pi-mote-1` à `pi-mote-6` (première version de la règle) | autorisé | 6 sur 6 joignables |
| serveur | port 80 de `pi-mote-1` | refusé | refusé |
| serveur | port 22 de `pi-gateway`, du PC et de `pi-ppk2` | refusé | refusé |
| `pi-mote-1` | port 22 du serveur | refusé | refusé |
| PC du propriétaire | `ssh pi@pi-mote-1` | inchangé | fonctionne |

Les 9 conteneurs n'ont pas été redémarrés.

**À savoir**

- Si un Pi est réenregistré dans Tailscale (réinstallation), son adresse peut
  changer : mettre à jour `hosts` dans `tailscale-policy.hujson`, puis
  recopier le fichier dans la console.
- Retour en arrière : historique des versions de la page Access controls, et
  `sudo tailscale down` sur le serveur.
- Un nouveau noyau Linux est installé sur l'instance depuis la mise à jour du
  11 novembre, mais pas encore actif : redémarrer le serveur à un moment
  choisi, puis consigner la coupure dans les interventions (E4) de
  [`docs/emplacements.md`](../docs/emplacements.md).

## Collecte automatique des journaux du régime 1a

Depuis le 12 novembre 2026, le serveur copie toutes les 10 minutes les
journaux du régime 1a (`~/lora-logs` de chaque Pi des motes) dans
`/srv/regime1a/journaux/<pi>/`. C'est l'étape 2 du suivi automatique du
régime 1a (calcul du PDR en continu et tableau de bord Grafana, étapes
suivantes à venir).

**Fonctionnement**

- `regime1a/collecte-journaux.sh` lit `regime1a/pis.conf` (nom et adresse
  Tailscale de chaque Pi) et lance un `rsync` par Pi. Les journaux ne font
  que grossir : seuls les ajouts sont transférés. Un Pi injoignable n'arrête
  pas les autres.
- Chaque passage est noté dans `/srv/regime1a/etat-collecte.csv`
  (`utc,host,ip,statut,code_rsync,octets`) : on sait quand chaque Pi a été
  collecté pour la dernière fois.
- `regime1a/systemd/regime1a-collecte.timer` lance le service toutes les
  10 minutes (`OnCalendar=*:0/10`, `Persistent=true`), sous l'utilisateur
  `ubuntu`. Suivi : `systemctl list-timers regime1a-collecte.timer` et
  `journalctl -u regime1a-collecte.service`.

**Sécurité : une clé en lecture seule**

- Clé dédiée sur le serveur : `~/.ssh/regime1a_collecte` (ed25519, sans
  phrase de passe, non versionnée). Clé publique versionnée :
  `regime1a/collecte.pub`.
- Sur chaque Pi, dans `~/.ssh/authorized_keys` :
  `command="/usr/bin/rrsync -ro /home/pi/lora-logs/",restrict <clé publique>`.
  La clé ne peut que **lire** `~/lora-logs` : ni shell, ni commande, ni
  écriture, ni redirection de port.
- **Port 2222.** Les Pi ont Tailscale SSH activé : sur leur adresse
  Tailscale, Tailscale intercepte le port 22 et applique sa propre politique,
  sans tenir compte de `authorized_keys`, donc sans la restriction ci-dessus.
  Autoriser `tag:server` dans Tailscale SSH lui aurait donné un shell complet
  sur les Pi. Le serveur SSH des Pi écoute donc aussi sur le port 2222
  (`/etc/ssh/sshd_config.d/60-regime1a-collecte.conf` : `Port 22` et
  `Port 2222`), seul port ouvert au serveur par la politique Tailscale.
  L'accès habituel (Tailscale SSH sur le port 22) est inchangé.
- Clés d'hôte des Pi : `/srv/regime1a/known_hosts`, enregistrées au premier
  passage.

**Mise en place (12 novembre 2026)**

1. Serveur : dossiers `/srv/regime1a` et `/srv/regime1a/journaux`
   (`ubuntu:ubuntu`, `0750`) et clé `~/.ssh/regime1a_collecte`.
2. Les six Pi : ligne ci-dessus ajoutée à `~/.ssh/authorized_keys` (copie de
   sauvegarde `authorized_keys.bak-2026-11-12`) et `~/lora-logs` créé s'il
   manquait. Le service `regime-1a` n'a pas été touché.
3. Premier essai sur le port 22 : refusé par Tailscale SSH
   (« tailnet policy does not permit you to SSH to this node »), rien copié.
4. Par le propriétaire : port 2222 ajouté au serveur SSH des six Pi, puis
   règle Tailscale du serveur passée de `tcp:22` à `tcp:2222`, avec un test
   qui interdit le port 22 au serveur.
5. Collecte réussie sur les six Pi (journaux des Pi 1, 2, 4 et 5 ; aucun
   encore sur les Pi 3 et 6).
6. Tentatives de détournement de la clé, toutes refusées : commande
   arbitraire, shell, écriture d'un fichier, lecture de `../.ssh/` et de
   `/etc/`, redirection de port (« administratively prohibited »), port 22.
7. Timer installé et activé sur le serveur.

`Mote/scripts/setup-pi.sh` configure le port 2222 et la clé de collecte sur
les nouveaux Pi. Ajouter un Pi : une ligne dans `pis.conf` et son adresse
dans `tailscale-policy.hujson`.

## Traitement automatique du régime 1a

Depuis le 12 novembre 2026, `regime1a-collecte.service` enchaîne la collecte
des journaux et leur traitement, toutes les 10 minutes. Le traitement
(`regime1a/traitement.py`) tourne dans le conteneur `regime1a-traitement`
de la pile (profil `jobs` : jamais lancé par `docker compose up`) :

1. il charge les nouvelles lignes des journaux dans `regime_1a_tx` et
   `regime_1a_events`, et l'état des collectes dans `regime_1a_collection` ;
2. il recalcule, du 6 novembre 2026 à 11:53 (début de la période de
   référence, variable `REGIME1A_DEBUT`) jusqu'à l'heure en cours, les
   fenêtres d'exclusion E1 à E4 et les comptes horaires par mote et par SF,
   remplacés d'un bloc dans `regime_1a_exclusions` et `regime_1a_hourly`.
   Les émissions qui chevauchent une autre mote de l'expérience (E5, depuis le
   12 novembre 2026) sont comptées dans les exclues, sans fenêtre propre.

**Même code que le bilan.** Le traitement importe les fonctions de
`Mote/src/bilan_regime_1a.py` (règle d'exclusion, classement des émissions,
comptes horaires) : le tableau de bord et les chiffres publiés sortent du même
code. Le code est lu dans le dépôt monté en lecture seule (`..:/repo:ro`) :
après un `git pull` sur le serveur, le passage suivant utilise la nouvelle
version, sans reconstruire l'image. L'image ne contient que Python 3.12 et
`psycopg`.

**Différence connue avec le bilan.** Le journal du netwatch de la gateway
n'est pas accessible depuis le serveur : E1 n'est pas élargie à l'alerte
« down » et E2 vient des connexions de la gateway au serveur. Le bilan lancé
avec `netwatch.log` peut exclure quelques secondes de plus.

**Accès à la base.** Le conteneur se connecte avec `regime1a_writer`, dont le
mot de passe est dans `.env` (`REGIME1A_DB_PASSWORD`, généré par
`openssl rand -hex 32`, non versionné).

**Mise en service (12 novembre 2026)**

1. Migration `005` : `regime_1a_events` identifiée par `(host, line_no)`, car
   deux lignes d'un journal peuvent partager l'heure et le type (deux `error`
   de `pi-mote-5` à la même milliseconde le 7 novembre). Appliquée table vide.
2. Mot de passe de `regime1a_writer` créé et ajouté à `.env` (copie de
   l'ancien : `.env.bak-2026-11-12`), image construite
   (`docker compose --profile jobs build regime1a-traitement`). Les conteneurs
   de production n'ont pas été redémarrés.
3. Premier passage manuel en 7 s : 46 270 émissions et 1 853 événements
   chargés, 8 fenêtres d'exclusion, 2 837 lignes horaires.
4. **Test de cohérence** : du 6 novembre 11:53 au 12 novembre 10:00 (heure de
   Paris), émis et reçus de `regime_1a_hourly` identiques à ceux du bilan en
   ligne de commande, pour les 4 motes et les 6 SF (24 lignes sur 24).
5. `systemctl daemon-reload` : premier passage automatique à 10:30, réussi.

Refaire le test de cohérence : copier les journaux de
`/srv/regime1a/journaux/` et les exports de la base dans un dossier, lancer le
bilan sur une période qui finit à une heure pile, puis comparer à :

```sql
SELECT host, sf, sum(sent), sum(received) FROM regime_1a_hourly
WHERE hour >= '<début>' AND hour < '<fin>' GROUP BY 1, 2 ORDER BY 1, 2;
```

Suivi : `journalctl -u regime1a-collecte.service` (une ligne de bilan par
passage). Lancer à la main :
`docker compose --profile jobs run --rm regime1a-traitement`.

## Installation

Prérequis : Docker avec le plugin Compose, `make`, les enregistrements DNS
`chirpstack.kouidri.fr` et `grafana.chirpstack.kouidri.fr` pointant vers
l'instance, et un groupe de sécurité ouvrant les ports TCP 80, 443 et 3001.

1. Créer le fichier `.env` à partir de `.env.example` et renseigner les mots
   de passe et le secret (commandes de génération indiquées dans le fichier) :

   ```bash
   cp .env.example .env
   ```

2. Générer la CA privée et le certificat serveur du pont Basics Station
   (voir [Connexion des gateways](#connexion-des-gateways)) :

   ```bash
   make gateway-certs
   ```

3. Démarrer la stack :

   ```bash
   docker compose up -d
   ```

4. Donner au rôle PostgreSQL `grafana_reader` le mot de passe
   `GRAFANA_DB_PASSWORD` du fichier `.env`. Le script d'initialisation crée ce
   rôle sans mot de passe : sans cette étape, Grafana ne peut pas lire la base.

   ```bash
   docker compose exec postgres psql -U chirpstack -c "ALTER ROLE grafana_reader WITH PASSWORD '<GRAFANA_DB_PASSWORD>';"
   ```

5. Vérifier l'état des services :

   ```bash
   docker compose ps
   ```

Les services redémarrent automatiquement avec l'instance
(`restart: unless-stopped`).

### Import des profils d'appareils (facultatif)

Importe le dépôt
[chirpstack-device-profiles](https://github.com/chirpstack/chirpstack-device-profiles)
dans ChirpStack :

```bash
make import-device-profiles
```

## Connexion des gateways

Les gateways se connectent en LoRa Basics Station (LNS) sur
`wss://chirpstack.kouidri.fr:3001`, avec une authentification TLS mutuelle.

- `make gateway-certs` crée dans `configuration/certs/` une CA privée (valable
  10 ans) et le certificat serveur du pont (valable 825 jours). ChirpStack
  signe les certificats clients des gateways avec cette même CA.
- **Ne jamais régénérer la CA** une fois des gateways provisionnées : leurs
  certificats deviendraient invalides. Le script refuse d'écraser une CA
  existante.
- Chaque gateway reçoit un certificat client depuis l'interface ChirpStack
  (Gateway → TLS certificate → Generate certificate), valable 12 mois
  (`client_cert_lifetime` dans `chirpstack.toml`). Le pont refuse toute
  connexion sans certificat signé par la CA.

⚠️ Deux échéances à surveiller :

- le certificat client de chaque gateway, à renouveler dans ChirpStack avant
  12 mois (date d'expiration de la gateway fixe :
  [`docs/gateway.md`](../docs/gateway.md)) ;
- le certificat serveur, à renouveler avant 825 jours. `make gateway-certs` ne
  le fait pas (il s'arrête dès que la CA existe) : il faut le signer à la main
  avec la CA existante.

Le pont est configuré pour EU868 : il publie sur les topics MQTT préfixés par
`eu868`. Les autres régions activées dans `chirpstack.toml` (configuration par
défaut de ChirpStack) ne sont pas utilisées.

Configuration côté gateway : voir [`docs/gateway.md`](../docs/gateway.md).

## Base de données des expériences

Le collecteur `uplink-collector` s'abonne aux topics MQTT des devices
(`application/+/device/+/event/+`) et des gateways (`+/gateway/+/+/+`), et
écrit dans la base `lorawan_experiments` :

| Table | Contenu |
|---|---|
| `uplinks` | Une ligne par uplink **et par gateway réceptrice** (RSSI, SNR, SF, fréquence, charge utile), unique sur `(deduplication_id, gateway_id)` |
| `device_events` | Tous les événements d'intégration ChirpStack : `up`, `join`, `ack`, `txack`, `status`, `log`… |
| `gateway_events` | Tous les messages MQTT entre les gateways et ChirpStack : uplinks bruts, downlinks, acks, statistiques, état de connexion |

L'événement brut est conservé dans la colonne `raw_event` (JSONB) de chaque
table.

Le suivi automatique du régime 1a (migration `004`, 12 novembre 2026) ajoute
cinq tables, remplies par le traitement de `regime1a/` (voir
[Traitement automatique du régime 1a](#traitement-automatique-du-régime-1a)) :

| Table | Contenu |
|---|---|
| `regime_1a_tx` | Une ligne par émission journalisée par une mote (`event=tx`), unique sur `(dev_eui, payload_hex)` : la charge utile (cycle, DR, marqueur `0x1A`) relie l'émission à sa réception dans `uplinks` |
| `regime_1a_events` | Les autres lignes des journaux (`config`, `join`, `skip`, `error`, `recover`, `pwridx`, `adr`, `stop`…), pour la traçabilité, unique sur `(host, line_no)` (migration `005`) |
| `regime_1a_exclusions` | Fenêtres d'exclusion E1 à E4 de la règle du plan (section 10), avec leur motif |
| `regime_1a_hourly` | Par heure, par mote et par SF : émis, reçus, exclus, avec et sans E3. PDR d'une période = somme des reçus / somme des émis |
| `regime_1a_collection` | Une ligne par Pi et par collecte des journaux (copie de `/srv/regime1a/etat-collecte.csv`) |

Comptes : `grafana_reader` lit ces tables (privilèges par défaut de la
migration `003`). `regime1a_writer`, créé par la migration `004` sans mot de
passe, écrit uniquement dans ces cinq tables et lit `uplinks` et
`gateway_events`. Les interventions E4 et les déplacements de la gateway
viennent de fichiers versionnés : [`docs/exclusions-e4.csv`](../docs/exclusions-e4.csv)
et [`docs/deplacements-gateway.csv`](../docs/deplacements-gateway.csv) (heures
avec leur fuseau, par exemple `+01:00`).

Migration `004` appliquée le 12 novembre 2026 sur l'instance, en ne créant
que de nouveaux objets (aucune table existante modifiée). Vérifié :
`grafana_reader` lit les cinq tables et ne peut pas y écrire ;
`regime1a_writer` a `SELECT, INSERT, UPDATE, DELETE` sur ces tables et
seulement `SELECT` sur `uplinks` et `gateway_events`.

### Résultats du banc PPK2

La migration `006` ajoute les résultats du [banc PPK2](../Mote/banc-ppk2.md)
(énergie par message), pour le tableau de bord Grafana :

| Objet | Contenu |
|---|---|
| `ppk2_series` | Une ligne par série de `Mote/banc-ppk2/` : réglages (mode, taille, `rx1_delay`, SF de RX2, duty cycle), mote, commit d'acquisition, et `in_results` (faux pour les contrôles de méthode : validation, chambre blindée sans duty cycle) |
| `ppk2_messages` | Une ligne par tentative (une ligne du CSV de la série), avec les mêmes colonnes ; `rx1_ms` et `rx2_ms` séparent les deux fenêtres de `rx_windows_ms` |
| `ppk2_results` (vue) | Messages retenus (`valid`) des séries de résultats, avec les réglages de leur série : seule source des panneaux de résultats |

Les fichiers versionnés de `Mote/banc-ppk2/` font foi. La base n'en est qu'une
copie pour l'affichage : `banc-ppk2/chargement.py` la remplace d'un bloc à
chaque passage, et les échantillons bruts (plusieurs gigaoctets par série) n'y
vont pas. Le tri entre résultats et contrôles suit le README de
`Mote/banc-ppk2/` ; la provenance du code de chaque série y est aussi.

Après avoir commité une nouvelle série, sur le serveur :

```sh
git pull --ff-only
docker compose --profile jobs run --rm banc-ppk2-chargement
```

Le conteneur réutilise l'image du traitement du régime 1a et se connecte avec
`banc_ppk2_writer` (mot de passe `BANC_PPK2_DB_PASSWORD` dans `.env`), qui
n'écrit que dans ces deux tables. Sans base, `python3
banc-ppk2/chargement.py --verifier` liste les séries lues et leur classement.

### Migrations

`configuration/postgresql/initdb/` ne s'exécute qu'à la création du volume
PostgreSQL. Sur une base existante, appliquer les migrations de
`configuration/postgresql/migrations/` dans l'ordre, une seule fois chacune :

```bash
docker compose exec -T postgres psql -v ON_ERROR_STOP=1 -U chirpstack -d lorawan_experiments < configuration/postgresql/migrations/<fichier>.sql
```

Toute modification du schéma se fait aux deux endroits : nouvelle migration et
mise à jour de `initdb/`.

## Tableaux de bord Grafana

La source de données PostgreSQL (rôle en lecture seule `grafana_reader`, base
`lorawan_experiments`) et les tableaux de bord sont provisionnés au démarrage
depuis `configuration/grafana/` :

- **LoRaWAN — Uplinks** : répartition des SF, SNR et RSSI par device, uplinks
  reçus ;
- **LoRaWAN — Debug** : derniers uplinks, requêtes de join OTAA et downlinks
  (avec le statut d'acquittement de la gateway) ;
- **LoRaWAN — Régime 1a** (`regime-1a.json`, depuis le 12 novembre 2026,
  https://grafana.chirpstack.kouidri.fr/d/regime-1a) : suivi du régime 1a à
  partir des tables `regime_1a_*`, voir ci-dessous.

- **LoRaWAN — Banc PPK2** (`banc-ppk2.json`,
  https://grafana.chirpstack.kouidri.fr/d/banc-ppk2) : énergie par message
  mesurée au banc, à partir des tables `ppk2_*`, voir plus bas.

**Tableau de bord du régime 1a.** Période par défaut : 7 derniers jours,
actualisation toutes les 10 min, heures de Paris. Les PDR sont des sommes de
comptes horaires (`sum(received) / sum(sent)`), donc à l'heure près.

| Panneau | Contenu |
|---|---|
| PDR par mote et par SF | Une ligne par mote, une colonne par SF, case colorée de blanc (0 %) à bleu foncé (100 %), émissions comptées et exclues |
| PDR en SF`$sf` par mote | Courbe par mote, agrégée par 1 h, 3 h, 6 h ou 1 jour (sélecteurs « SF du graphique » et « Agrégation ») |
| État des motes et de la collecte | Minutes depuis la dernière réception, la dernière émission journalisée et la dernière collecte réussie (orange puis rouge au-delà de 60 et 120 min pour la réception, 25 et 60 min pour le reste), reprises automatiques |
| Fenêtres d'exclusion | Motif, début, fin et durée des fenêtres E1 à E4 de la période |
| Gateway fixe | Statistiques reçues par heure (120 attendues), en rouge sous 115 |

Le sélecteur « Heures E3 » donne le PDR avec la règle complète ou en gardant
les heures E3, comme le demande la règle. Seuil de 60 min pour la réception :
au CBI, l'écart entre deux réceptions dépasse parfois une heure (99e centile
d'environ 70 min du 6 au 12 novembre).

Vérifié le 12 novembre 2026 par l'API de Grafana : tableau chargé, les six
panneaux renvoient des données, avec les deux valeurs du sélecteur E3 et
plusieurs SF et agrégations.

**Tableau de bord du banc PPK2.** Résultats de banc et non séries
temporelles : pas de période à choisir. Il sert à lire et à montrer les
résultats ; les figures du papier viendront d'un script versionné.

| Panneau | Contenu |
|---|---|
| Chiffres clés | Séries et messages retenus, énergie d'un message de 6 octets en SF7 et en SF12, rapport des deux |
| Énergie selon le SF et la taille | Moyenne par SF pour 6, 20 et 51 octets (`rx1_delay` 1 s, RX2 en SF12) ; barre absente : cas non mesuré |
| Durée d'un message | Émission, attentes au repos, RX1 et RX2 par SF, en 6 octets |
| Sonde ratée ou uplink non confirmé | Les deux coûts côte à côte, SF7 à SF9 |
| Effet du débit de RX2, effet de `rx1_delay` | Mêmes messages avec RX2 en SF9, ou `rx1_delay` à 3 s |
| Seuil de rentabilité p* | p* = E_sonde ratée / E_repli par SF de repli et SF de sonde (plan, section 9), selon les sélecteurs « Charge utile » et « RX2 » |
| Gain selon la probabilité de réussite | Droites gain = p − p* par SF de repli, pour la sonde du sélecteur « Sonde » : un calcul à partir des énergies mesurées, pas une mesure de terrain |
| Répétabilité | Écart de chaque message à la médiane de son SF, pour la série du sélecteur « Série » |
| Séries mesurées | Par série et par SF : effectif, moyenne, écart-type, CV, extrêmes, fenêtres RX2 allongées, rôle (résultats ou contrôle de méthode) |

Les moyennes gardent les messages à fenêtre RX2 allongée, comme dans
`Mote/banc-ppk2/README.md`. Le panneau « Gain » utilise le type `trend`, encore
en bêta dans Grafana 11.6.

Les tableaux de bord sont modifiables dans l'interface, mais les fichiers JSON
de `configuration/grafana/dashboards/` font foi. Pour garder une modification,
exporter le tableau de bord (Share → Export → Save to file, sans cocher
« Export for sharing externally ») dans ce dossier et le commiter. Sinon, la
modification est perdue à la prochaine mise à jour du fichier ou réinstallation
de Grafana.

L'identifiant (`uid`) de la source de données est référencé par tous les
tableaux de bord : ne pas le modifier.

## Données persistantes

Les données de PostgreSQL, Redis, Mosquitto, Grafana et Caddy sont dans des
volumes Docker (section `volumes` de `docker-compose.yml`). Le volume
`postgresqldata17` contient les données migrées de PostgreSQL 14 vers 17
(`pg_dumpall`, le 7 octobre 2026).

## Sauvegarde et restauration

L'instance EC2 entière est sauvegardée par une politique Amazon Data Lifecycle
Manager, configurée dans la console AWS (pas dans ce dépôt) :

- **Politique** : politique personnalisée d'AMI adossée à EBS, qui cible les
  instances portant le tag `Backup` = `daily`.
- **Planification** : une AMI toutes les 24 heures à partir de 03:00 UTC ; les
  14 plus récentes sont conservées, les plus anciennes et leurs snapshots sont
  supprimés automatiquement.
- **Sans redémarrage** : les AMI sont prises pendant que la stack tourne
  (cohérence de type coupure de courant) ; PostgreSQL s'en remet comme après
  une panne d'alimentation.
- **Périmètre** : l'unique volume EBS contient tout : système, volumes Docker,
  secrets du fichier `.env` et CA des gateways dans `configuration/certs/`.

Pour restaurer :

1. EC2 → Images → AMIs → sélectionner l'AMI → **Launch instance from AMI**,
   avec le même type d'instance et le même groupe de sécurité (TCP 80, 443 et
   3001).
2. Faire pointer `chirpstack.kouidri.fr` et `grafana.chirpstack.kouidri.fr`
   vers la nouvelle instance (ou réassocier l'Elastic IP). La gateway se
   reconnecte d'elle-même dès que le nom résout vers la nouvelle instance.
3. La stack démarre automatiquement ; vérifier avec `docker compose ps`.

Ces AMI sont dans le même compte et la même région AWS : elles ne protègent pas
contre la perte du compte.
