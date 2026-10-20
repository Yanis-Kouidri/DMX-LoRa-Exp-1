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
