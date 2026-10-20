# Gateway MikroTik : état actuel

État au **12 octobre 2026**, vérifié de bout en bout : la mote a rejoint le
réseau en OTAA via la gateway, et ses uplinks arrivent dans ChirpStack et dans
le tableau de bord Grafana.

- Modèle : MikroTik wAP LR8 (`RBwAPR-2nD`, carte `wAP R`), RouterOS 7.24
- Gateway ID : `323531322A003300`
- Rôle : **gateway fixe** de l'expérience. Elle reste en intérieur, dans un
  bureau de l'IRIT (4e étage, près d'une fenêtre orientée nord-ouest), pendant
  toute l'expérience (pas d'installation sur un toit). Ne modifier ni sa
  position ni l'orientation de son antenne. Coordonnées :
  [`emplacements.md`](emplacements.md).
- Une deuxième wAP LR8, identique, sert de **gateway mobile** (vélo, 4G). Elle
  n'est pas encore documentée ici.

## Topologie réseau

```
Prise murale campus ──(DHCP)── ether1 [WAN]   wAP LR8   wlan1 [LAN] ── PC (admin)
                                                         Wi-Fi AP « wAP-LoRa-admin »
                                                         192.168.88.1/24
```

| Interface | Rôle | Adressage |
|---|---|---|
| `ether1` | WAN, accès à Internet par la prise murale du campus | Client DHCP (`defconf`), bail obtenu `192.168.1.143/24`, passerelle `192.168.1.1` |
| `wlan1` | LAN, point d'accès privé d'administration `wAP-LoRa-admin` (WPA2-PSK, profil `wap-admin`) | `192.168.88.1/24`, serveur DHCP `defconf` (plage `192.168.88.10-254`) |

- NAT masquerade sur la liste d'interfaces `WAN` : un PC connecté à
  `wAP-LoRa-admin` accède à Internet à travers la gateway.
- Pare-feu RouterOS par défaut : les connexions entrantes depuis `WAN` sont
  rejetées, la gateway n'est donc administrable **que depuis le Wi-Fi
  `wAP-LoRa-admin`**.
- Le mot de passe de `wAP-LoRa-admin` n'est pas stocké ici : il est dans
  `secrets.md` (modèle : [`secrets-example.md`](../secrets-example.md)).

Restes désactivés de l'ancien montage, où le PC était relié directement à la
gateway en Ethernet (conservés pour pouvoir revenir en arrière facilement) :

- adresse statique `192.168.1.60/24` sur `ether1` ;
- route par défaut statique via `192.168.1.99` (distance 10) ;
- client DHCP `client1` sur `wlan1`.

## Configuration LoRa

| Paramètre | Valeur |
|---|---|
| Serveur | `ChirpStack LNS` : `chirpstack.kouidri.fr`, port `3001`, Basics Station (LNS) sur TLS |
| Certificat client | `wap-gateway` (signé par `chirpstack-ca`, « LoRaWAN-Infra gateway CA ») |
| Plan de canaux | `eu-868`, réseau public |
| Antenne | interne, gain 0 dBi |

⚠️ Le certificat client `wap-gateway` **expire le 7 octobre 2027**. En générer
un nouveau dans ChirpStack (Gateway → TLS certificate) avant cette date (voir
[`LoRaWAN-Infra/README.md`](../LoRaWAN-Infra/README.md#connexion-des-gateways)).

Les autres entrées de `/lora servers` (TTN, TTS) sont les valeurs par défaut de
RouterOS et ne sont pas utilisées.

## Accès d'administration

1. Connecter le PC au Wi-Fi `wAP-LoRa-admin`.
2. WebFig : `http://192.168.88.1`, avec le compte `admin`.

### Accès de Claude Code

Claude administre la gateway en SSH avec un compte dédié. Cet accès est à
conserver.

```bash
ssh -i ~/.ssh/claude_wap claude@192.168.88.1
```

- Utilisateur RouterOS `claude` (groupe `full`), connexion par clé uniquement
  (clé ed25519 `claude-wap`).
- Clé privée sur le PC : `~/.ssh/claude_wap` (WSL 2 en réseau `mirrored`, donc
  la connexion Wi-Fi de Windows est visible depuis WSL).
- Pour le révoquer : `/user remove claude` sur la gateway, puis
  `rm ~/.ssh/claude_wap ~/.ssh/claude_wap.pub` sur le PC.

## Wi-Fi du campus : ne fonctionne pas (problème ouvert)

La connexion de la gateway en client Wi-Fi aux réseaux du campus a été essayée
sans succès :

- **eduroam** (compte INP, PEAP/MSCHAPv2) et **Poseidon** (réseau de l'IRIT) :
  l'authentification 802.1X réussit, mais les DHCP DISCOVER restent sans
  réponse. Le PC obtient un bail sur le même point d'accès, la même bande et le
  même compte, et la gateway obtient immédiatement un bail sur un partage de
  connexion de téléphone et sur la prise murale. La cause la plus probable est
  un filtrage des appareils par l'infrastructure Wi-Fi du campus ; seule la
  DSI (dsi-support.inp-toulouse.fr) peut le confirmer ou le lever.
- **Ne pas** contourner le problème en usurpant ou en clonant une adresse MAC :
  cela contourne le contrôle d'accès de l'université, et cloner l'adresse MAC
  du PC entre en conflit avec le PC.
- Les points d'accès 2,4 GHz du campus (`20:9E:F7:*`) utilisent un **chiffrement
  de groupe TKIP** : tout profil de sécurité RouterOS pour ces réseaux doit
  contenir `group-ciphers=tkip,aes-ccm`, sinon la gateway les ignore et se
  rabat sur des points d'accès éloignés.
- La CA eduroam de l'INP (`rootCA.eduroam.inpt`, profil issu de
  cat.eduroam.org) est toujours importée sur la gateway. Les profils de
  sécurité eduroam, Poseidon et partage de connexion ont été supprimés : aucun
  identifiant personnel n'est stocké sur la gateway.

Les Raspberry Pi, eux, se connectent sans problème à eduroam (voir
[`Mote/raspberry-pi.md`](../Mote/raspberry-pi.md#3-eduroam)).

## Pièges

- **Serveur DHCP d'usine lié à `wlan1`** : si `wlan1` repasse un jour en mode
  station (client), désactiver le serveur DHCP `defconf` et l'adresse
  `192.168.88.1/24` sur cette interface, et placer `wlan1` dans la liste
  d'interfaces `WAN`. Sinon, la gateway se comporte en serveur DHCP pirate sur
  le réseau amont et y expose son interface d'administration.
- **Pas d'horloge sauvegardée par pile** : l'heure est fausse après un
  redémarrage tant que NTP n'a pas synchronisé (client NTP activé avec
  `pool.ntp.org`). Le TLS vers ChirpStack et l'horodatage des uplinks en
  dépendent.

## Commandes utiles

```
/ip dhcp-client print detail where interface=ether1   # bail WAN
/ping 8.8.8.8 count=3                                 # accès à Internet
/lora print                                           # état LoRa et compteurs de paquets
/lora traffic print                                   # dernières trames (join, uplinks, downlinks)
/log print where topics~"lora"                        # journal de connexion à ChirpStack
/interface wireless registration-table print          # clients de wAP-LoRa-admin
```
