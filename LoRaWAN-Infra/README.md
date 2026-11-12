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
  (avec le statut d'acquittement de la gateway).

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
