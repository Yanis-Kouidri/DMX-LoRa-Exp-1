# DMX-LoRa-Exp-1

Expérience LoRaWAN en conditions réelles sur le campus Paul Sabatier
(Toulouse) : comparaison d'une **gateway fixe** et d'une **gateway mobile**
(à vélo, reliée en 4G) qui collectent les données de 6 motes installées en
intérieur.

## Cadre

Expérience menée dans le cadre d'une thèse de doctorat (CIFRE) avec l'IRIT,
sur la collecte de données dans les réseaux de capteurs. Les résultats visent
une publication en conférence principale (soumission visée au printemps 2027).

## Objectif

Au-delà de la comparaison fixe/mobile (PDR, RSSI, SNR), l'expérience cherche
à savoir si une gateway mobile de passage permet de **réduire le coût radio
des motes** : émettre avec un SF plus bas, donc moins longtemps, sans perdre
de données et avec une latence bornée. Le mécanisme étudié reste compatible
avec LoRaWAN Class A.

- **Phase 1, caractérisation** : SF minimal fiable vers chaque gateway,
  comparaison appariée des mêmes paquets reçus par les deux gateways, durée
  des fenêtres de contact. ADR désactivé, puissance d'émission fixe.
- **Phase 2, mécanisme de sonde** : la mote envoie ses données en SF7
  confirmé et se replie vers la gateway fixe si aucun accusé n'arrive dans le
  délai D. Indicateur principal : énergie radio par donnée livrée, mesurée sur
  banc (PPK2).

Hypothèses, calendrier, protocole et risques :
[`docs/plan-experimental.md`](docs/plan-experimental.md).

## Dispositif

```
Mote RN2483 ──USB── Raspberry Pi            (× 6, un par bâtiment)
     │ LoRa EU868
     ├──► Gateway fixe  (wAP LR8, IRIT, Pi + eduroam) ──┐
     └──► Gateway mobile (wAP LR8, vélo, 4G) ───────────┤ Basics Station (TLS)
                                                        ▼
               ChirpStack ─► collecteur ─► PostgreSQL ─► Grafana   (AWS EC2)
```

| Élément | Matériel | Documentation |
|---|---|---|
| Motes | 6 × Microchip RN2483 Mote, firmware 1.0.6 RC4 (LoRaWAN 1.0.2) | [`Mote/README.md`](Mote/README.md), [`Mote/mote.md`](Mote/mote.md) |
| Pilotage des motes | 6 × Raspberry Pi 4, sur eduroam et Tailscale | [`Mote/raspberry-pi.md`](Mote/raspberry-pi.md) |
| Gateway fixe | MikroTik wAP LR8, RouterOS 7.24 | [`docs/gateway.md`](docs/gateway.md) |
| Gateway mobile | MikroTik wAP LR8 identique, en 4G | à documenter |
| Serveur | ChirpStack v4, PostgreSQL, Grafana (Docker Compose) | [`LoRaWAN-Infra/README.md`](LoRaWAN-Infra/README.md) |

## Documentation

| Document | Contenu |
|---|---|
| [`docs/plan-experimental.md`](docs/plan-experimental.md) | Plan d'expérience : question de recherche, état de l'art, hypothèses, phases, statistiques |
| [`docs/emplacements.md`](docs/emplacements.md) | Emplacements de la gateway fixe et des motes (données dans [`emplacements.csv`](docs/emplacements.csv)) |
| [`docs/gateway.md`](docs/gateway.md) | Gateway fixe : réseau, configuration LoRa, accès d'administration, pièges |
| [`Mote/README.md`](Mote/README.md) | Firmware des motes, installation, connexion sous WSL, scripts |
| [`Mote/config.md`](Mote/config.md) | Commandes RN2483 : configuration ChirpStack, join, duty cycle |
| [`Mote/mote.md`](Mote/mote.md) | Inventaire des motes, mote défectueuse retirée |
| [`Mote/raspberry-pi.md`](Mote/raspberry-pi.md) | Installation des Raspberry Pi |
| [`LoRaWAN-Infra/README.md`](LoRaWAN-Infra/README.md) | Stack serveur : services, installation, certificats, base de données, sauvegardes |

## Structure du dépôt

- `docs/` : documentation de l'expérience.
- `Mote/` : projet Python (uv, Python 3.14) de pilotage des motes par liaison
  série, et script d'installation des Raspberry Pi.
- `LoRaWAN-Infra/` : stack Docker Compose du serveur LoRaWAN.
- `secrets-example.md` : modèle du fichier `secrets.md`, qui contient les
  secrets et n'est pas versionné.
- `AGENTS.md` : consignes pour les agents de code (en anglais).

Le dépôt est public : ni secret ni nom de collègue dans les fichiers versionnés.
