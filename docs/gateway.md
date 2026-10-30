# Gateway MikroTik : état actuel

État au **30 octobre 2026**. La gateway accède à Internet par un Raspberry Pi
(`pi-gateway`) connecté à eduroam (voir
[Historique de la liaison Internet](#historique-de-la-liaison-internet)). Des
joins OTAA en SF12 ont été acceptés depuis les 5 emplacements de motes, au sol
(résultats provisoires : [`emplacements.md`](emplacements.md)).

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
eduroam ))) wlan0  pi-gateway  eth0 ──(DHCP)── ether1 [WAN]   wAP LR8   wlan1 [LAN] ── PC (admin)
               (Raspberry Pi 4, NAT)                                     Wi-Fi AP « wAP-LoRa-admin »
                                    10.42.0.1/24                         192.168.88.1/24
```

| Interface | Rôle | Adressage |
|---|---|---|
| `ether1` | WAN, accès à Internet par `pi-gateway` | Client DHCP (`defconf`), bail réservé `10.42.0.33/24`, passerelle `10.42.0.1` ; script qui journalise la perte et la reprise du bail |
| `wlan1` | LAN, point d'accès privé d'administration `wAP-LoRa-admin` (WPA2-PSK, profil `wap-admin`) | `192.168.88.1/24`, serveur DHCP `defconf` (plage `192.168.88.10-254`) |

- NAT masquerade sur la liste d'interfaces `WAN` : un PC connecté à
  `wAP-LoRa-admin` accède à Internet à travers la gateway.
- Pare-feu RouterOS par défaut : les connexions entrantes depuis `WAN` sont
  rejetées, avec une seule exception ajoutée le 30 octobre : la règle
  `SSH admin from pi-gateway only` (chaîne `input`, placée avant
  `defconf: drop all not coming from LAN`) accepte le port TCP 22 sur `ether1`
  **uniquement depuis `10.42.0.1`** (`pi-gateway`). WebFig (80) et Winbox
  (8291) restent fermés côté `WAN` (vérifié depuis le Pi). Voir
  [Accès à distance](#accès-à-distance-par-pi-gateway).
- Le mot de passe de `wAP-LoRa-admin` n'est pas stocké ici : il est dans
  `secrets.md` (modèle : [`secrets-example.md`](../secrets-example.md)).

Restes désactivés de l'ancien montage, où le PC était relié directement à la
gateway en Ethernet (conservés pour pouvoir revenir en arrière facilement) :

- adresse statique `192.168.1.60/24` sur `ether1` ;
- route par défaut statique via `192.168.1.99` (distance 10) ;
- client DHCP `client1` sur `wlan1`.

## Raspberry Pi `pi-gateway`

Raspberry Pi 4 (Debian 13 trixie) qui sert de routeur à la gateway : il est
connecté à eduroam en Wi-Fi et partage cette connexion sur son port Ethernet,
relié à `ether1`.

- Installation de base (eduroam, Tailscale, mise à l'heure) : même script que
  pour les Pi des motes,
  [`Mote/scripts/setup-pi.sh`](../Mote/scripts/setup-pi.sh).
- Partage de connexion : profil NetworkManager `gw-share` sur `eth0`
  (`ipv4.method shared`, IPv6 désactivé). NetworkManager y lance un serveur
  DHCP (`10.42.0.0/24`) et un NAT vers `wlan0`.
- L'ancien profil client DHCP `Wired connection 1` est conservé, mais sa
  connexion automatique est désactivée pour qu'il n'entre pas en concurrence
  avec `gw-share`.
- Économie d'énergie du Wi-Fi désactivée dans le profil `eduroam`
  (`802-11-wireless.powersave 2`) : ses micro-coupures cassent la connexion
  vers ChirpStack.
- Accès SSH par Tailscale : `ssh pi@pi-gateway`.
- Adresses figées (30 octobre), car la règle de pare-feu de la gateway et
  l'accès à distance en dépendent : `gw-share` a l'adresse fixe
  `10.42.0.1/24` (sans elle, NetworkManager peut choisir un autre sous-réseau
  `10.42.x.0/24`), et le fichier
  `/etc/NetworkManager/dnsmasq-shared.d/wap-gateway.conf` réserve
  `10.42.0.33` à l'adresse MAC d'`ether1` (`C4:AD:34:B2:0E:3A`). Vérifié
  après un redémarrage du Pi le 30 octobre.
- Après une coupure de courant, tout repart seul (vérifié le 26 octobre) :
  eduroam, `gw-share`, Tailscale, NTP, puis le bail et la connexion de la
  gateway.

Création du partage, à refaire sur un Pi neuf :

```bash
sudo nmcli connection add type ethernet ifname eth0 con-name gw-share \
  ipv4.method shared ipv6.method disabled \
  connection.autoconnect yes connection.autoconnect-priority 10
sudo nmcli connection modify gw-share ipv4.addresses 10.42.0.1/24
sudo nmcli connection modify "Wired connection 1" connection.autoconnect no
sudo nmcli connection modify eduroam 802-11-wireless.powersave 2
sudo mkdir -p /etc/NetworkManager/dnsmasq-shared.d
echo "dhcp-host=C4:AD:34:B2:0E:3A,10.42.0.33" | \
  sudo tee /etc/NetworkManager/dnsmasq-shared.d/wap-gateway.conf
```

Point ouvert : le Pi se connecte à eduroam avec un compte personnel. Pour
l'expérience, un accès dédié aux objets connectés est à demander à la DSI (voir
[Wi-Fi du campus](#wi-fi-du-campus--ne-fonctionne-pas-problème-ouvert)).

## Historique de la liaison Internet

| Période | Liaison | Coupures de la connexion à ChirpStack |
|---|---|---|
| Début oct. → 26 oct. | Routeur Teltonika RUTX50 (LAN `192.168.1.0/24`) sur la 5G privée de l'université (neOCampus) | **42 à 61 par jour** du 21 au 25 octobre (logs du serveur disponibles depuis le 19) |
| Depuis le 26 oct., 13:50 UTC | `pi-gateway` sur eduroam | **0** en 22 h 45 (26 oct., 15:48 → 27 oct., 14:34 UTC) |

Avec la 5G, chaque coupure faisait perdre plusieurs minutes de trafic. Le lien
restait bloqué sans erreur, puis la gateway journalisait
`socket error onRecv [2001]` et attendait 60 s avant de se reconnecter. Pendant
le blocage, ChirpStack croyait la gateway connectée : les join requests
n'arrivaient plus, et des join-accepts envoyés à la gateway n'étaient jamais
émis. La mote recevait alors `denied` alors qu'elle était à portée.

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

À distance, seul SSH est possible, par `pi-gateway` : voir
[Accès à distance par `pi-gateway`](#accès-à-distance-par-pi-gateway).

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

### Accès à distance par `pi-gateway`

Depuis le 30 octobre, la gateway est joignable en SSH sans être sur
`wAP-LoRa-admin`, par rebond sur `pi-gateway` (Tailscale) :

```bash
ssh wap-gateway
```

Entrée correspondante dans `~/.ssh/config` du PC (la clé d'hôte est la même que
celle déjà connue pour `192.168.88.1`) :

```
Host wap-gateway
    HostName 10.42.0.33
    User claude
    IdentityFile ~/.ssh/claude_wap
    ProxyJump pi@pi-gateway
    HostKeyAlias 192.168.88.1
```

Seul SSH passe. Pour WebFig à distance, utiliser un tunnel :
`ssh -L 8080:127.0.0.1:80 wap-gateway`, puis `http://localhost:8080`
(nécessite `/ip ssh set forwarding-enabled=local`, désactivé actuellement). Pour
supprimer cet accès : `/ip firewall filter remove [find comment="SSH admin from pi-gateway only"]`.

## Wi-Fi du campus : ne fonctionne pas (problème ouvert)

La connexion de la gateway en client Wi-Fi aux réseaux du campus a été essayée
sans succès :

- **eduroam** (compte INP, PEAP/MSCHAPv2) et **Poseidon** (réseau de l'IRIT) :
  l'authentification 802.1X réussit, mais les DHCP DISCOVER restent sans
  réponse. Le PC obtient un bail sur le même point d'accès, la même bande et le
  même compte, et la gateway obtient immédiatement un bail sur un partage de
  connexion de téléphone et en Ethernet derrière la RUTX50. La cause la plus probable est
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
[`Mote/raspberry-pi.md`](../Mote/raspberry-pi.md#3-eduroam)) : c'est ce qui a
conduit au montage actuel, avec la gateway derrière
[`pi-gateway`](#raspberry-pi-pi-gateway).

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
- **Gateway sourde après une coupure de la liaison Internet (corrigé le
  30 octobre)** : si `pi-gateway` redémarre ou perd eduroam, la connexion TLS
  vers ChirpStack meurt sans que la gateway le voie (perte de la table NAT ou
  changement d'adresse publique). ChirpStack détecte la déconnexion en moins
  d'une minute, mais Basics Station continue de retransmettre sur l'ancienne
  connexion TCP jusqu'à ce que TCP abandonne. Mesuré le 26 octobre : coupure du
  Pi à 15:29, reconnexion de la gateway à 15:48 UTC, soit environ 18 minutes
  sans réception.

  Correctif : un netwatch relance la LoRa dès que l'accès à Internet revient.
  Il envoie toutes les 10 s une salve de 10 pings vers `1.1.1.1` et ne
  déclare la liaison coupée qu'au-delà de 90 % de pertes (seuils de latence
  relevés à 5 s pour ne pas réagir à une simple lenteur). La cible est
  `1.1.1.1` et non ChirpStack : netwatch n'accepte qu'une adresse IP, et celle
  de l'instance AWS change en cas de restauration. Une panne de ChirpStack
  seul n'a pas besoin de ce mécanisme : le serveur ferme la connexion et
  Basics Station se reconnecte de lui-même.

  ```
  /tool netwatch add name=backhaul type=icmp host=1.1.1.1 interval=10s \
      packet-count=10 packet-interval=200ms thr-loss-percent=90% \
      thr-avg=5s thr-max=5s thr-jitter=5s thr-stdev=5s \
      comment="LoRa restart after backhaul outage" \
      down-script=":log warning \"netwatch backhaul down (1.1.1.1)\"" \
      up-script=":log warning \"netwatch backhaul up: restarting LoRa\"; /lora disable [find]; :delay 2s; /lora enable [find]"
  ```

  Le client DHCP d'`ether1` a aussi un script, qui se contente de journaliser
  (`dhcp ether1 bound` / `unbound`). Il relançait la LoRa lors d'un premier
  essai, retiré pour éviter une double relance quand le Pi redémarre (le
  netwatch couvre aussi ce cas).

  Tests du 30 octobre (heures du journal de la gateway, heure de Paris) :

  | Scénario | Coupure | Netwatch | Gateway de nouveau à l'écoute (`forwarder is ready`) |
  |---|---|---|---|
  | Redémarrage de `pi-gateway`, relance par le script DHCP (premier essai) | bail perdu à 15:12:34, repris à 15:13:01 | — | 15:13:27, **53 s** après la perte du bail |
  | eduroam coupé 60 s sur le Pi (`nmcli con down`), sans redémarrage | 15:29:21 → 15:30:21 | `down` 15:29:33, `up` 15:30:32 | 15:30:59, **98 s** après le début de la coupure, 38 s après le retour d'eduroam |

  Pendant le second test, Basics Station n'a journalisé aucune erreur avant
  la relance : sans le netwatch, la gateway serait restée bloquée sur
  l'ancienne connexion. Une relance coûte environ 26 s d'écoute perdue
  (mesuré à l'activation du netwatch). Le scénario « redémarrage du Pi » n'a
  pas été refait avec le netwatch ; il repose sur le même mécanisme (perte
  puis retour de l'accès à Internet).
- **Un `denied` au join ne prouve pas que la mote est hors de portée** : avant
  de conclure, vérifier dans les logs du pont Basics Station que la gateway
  était connectée et a bien confirmé l'émission du join-accept
  (`downlink transmitted message received`).

## Commandes utiles

```
/ip dhcp-client print detail where interface=ether1   # bail WAN
/ping 8.8.8.8 count=3                                 # accès à Internet
/lora print                                           # état LoRa et compteurs de paquets
/lora traffic print                                   # dernières trames (join, uplinks, downlinks)
/log print where topics~"lora"                        # journal de connexion à ChirpStack
/tool netwatch print detail                           # état du netwatch backhaul
/log print where topics~"script"                      # passages down/up et relances LoRa
/interface wireless registration-table print          # clients de wAP-LoRa-admin
```
