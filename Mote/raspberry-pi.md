# Raspberry Pi de contrôle des motes

Les Raspberry Pi pilotent les motes RN2483 (envoi des commandes via la
liaison série USB).

## Matériel

6 × Raspberry Pi 4 Model B, 4 Go de RAM (vérifié par SSH via
`/proc/device-tree/model` et `/proc/meminfo`).

| Machine     | Modèle                 | Révision | RAM  |
| ----------- | ---------------------- | -------- | ---- |
| `pi-mote-1` | Raspberry Pi 4 Model B | 1.5      | 4 Go |
| `pi-mote-2` | Raspberry Pi 4 Model B | 1.5      | 4 Go |
| `pi-mote-3` | Raspberry Pi 4 Model B | 1.5      | 4 Go |
| `pi-mote-4` | Raspberry Pi 4 Model B | 1.5      | 4 Go |
| `pi-mote-5` | Raspberry Pi 4 Model B | 1.5      | 4 Go |
| `pi-mote-6` | Raspberry Pi 4 Model B | 1.1      | 4 Go |

### Problème connu : liaison série de `pi-mote-4`

La liaison série entre `pi-mote-4` et sa mote (HWEUI `0004A30B0023F575`) se
bloque de temps en temps (constaté le 16 octobre 2026) :

- une réponse s'interrompt en cours de route, puis la mote ne répond plus du
  tout, même après une resynchronisation de l'auto-baud ;
- seule une coupure de l'alimentation USB la relance
  (`sudo uhubctl -l 1-1 -a cycle -d 5`, `uhubctl` installé sur ce Pi
  uniquement). Cette commande exacte est autorisée sans mot de passe par
  `/etc/sudoers.d/020_uhubctl` ;
- la première commande après l'ouverture du port répond souvent
  `invalid_param` ;
- en fonctionnement normal, une série de `sys get ver` d'affilée bloque la
  mote après 211 commandes (`pi-mote-5`, témoin : 500 sur 500) ;
- le passage en 1.0.6 RC4 a demandé 20 coupures USB sur 1012 lignes écrites.
  `src/flash_firmware.py` échoue sur cette mote : il a fallu un flash qui
  reprend à la ligne bloquée après chaque coupure.

Les 5 autres Pi flashent sans erreur avec le même montage : le problème vient
de la mote, du câble ou du port USB. Les commandes `mac tx` passent par la
même liaison, la campagne y est donc exposée aussi.

À essayer : changer de port USB, puis de câble.

## Système d'exploitation

**Raspberry Pi OS Lite 64 bits** (sans interface graphique) sur les 6 Pi.

- Même image et même configuration sur les 6 cartes.
- Sans bureau : les Pi sont pilotés en SSH, ce qui garde l'OS léger.
- OS officiel : meilleur support du matériel (firmware, `raspi-config`,
  bootloader du Pi 4).
- Préconfigurable avec Raspberry Pi Imager (nom de machine, utilisateur, clé
  SSH, réseau) : accès SSH dès le premier démarrage, sans écran.
- Python 3.14 : installé par `uv` selon `.python-version`, indépendamment de
  la version fournie par l'OS.

## Installation d'un Pi

Procédure validée sur `pi-mote-1` (Raspberry Pi 4). Remplacer `pi-mote-N` par
le nom de la machine (`pi-mote-1` à `pi-mote-6`).

### 1. Flasher la carte SD

Avec Raspberry Pi Imager, choisir Raspberry Pi OS Lite (64-bit) et
préconfigurer :

- nom de machine : `pi-mote-N` (un nom unique par Pi) ;
- utilisateur : `pi` et son mot de passe ;
- SSH activé (clé publique de préférence) ;
- pas de Wi-Fi (eduroam n'est pas configurable dans Imager).

### 2. Première connexion SSH par Ethernet

1. Sous Windows, partager la connexion Wi-Fi du PC vers le port Ethernet :
   Paramètres réseau → propriétés de la carte Wi-Fi → onglet Partage →
   partager avec « Ethernet ». Le Pi reçoit une adresse en `192.168.137.x` et
   l'accès à Internet.
2. Relier le Pi au PC par un câble Ethernet direct, puis le mettre sous
   tension. Attendre 1 à 2 minutes (le premier démarrage redémarre une fois).
3. Depuis PowerShell (WSL2 ne voit pas ce réseau) :

   ```bash
   ssh pi@pi-mote-N.local
   ```

   Si le nom ne répond pas, trouver l'adresse du Pi avec `arp -a` et s'y
   connecter directement.

Brancher les Pi un par un.

### Étapes 3 et 4 automatisées

Le script [`scripts/setup-pi.sh`](scripts/setup-pi.sh) enchaîne les étapes 3
et 4. Il vérifie d'abord si la connexion eduroam existe et donne accès à
Internet via `wlan0` : si oui, il la conserve. Sinon, ou avec l'option
`--force-eduroam`, il demande l'identifiant et le mot de passe eduroam, vérifie
l'empreinte du certificat, recrée la connexion et teste Internet via `wlan0`.
Ensuite, il passe les dépôts APT en HTTPS (le HTTP est bloqué sur eduroam), met à jour le
système (`apt update` et `apt upgrade`), installe `git`, `vim`
et `tree`, clone ce dépôt dans `~/DMX-LoRa-Exp-1`, installe
[uv](https://docs.astral.sh/uv/) dans `~/.local/bin`, puis installe et lance
Tailscale. Depuis le PC, avec le câble branché :

```bash
scp Mote/scripts/setup-pi.sh pi@pi-mote-N.local:
```

```bash
ssh -t pi@pi-mote-N.local sudo ./setup-pi.sh
```

Le script est idempotent : il peut être relancé sans risque et saute ce qui
est déjà en place (connexion eduroam fonctionnelle, dépôts déjà en HTTPS, dépôt
déjà cloné, uv déjà installé, Tailscale déjà installé et connecté).

Pour forcer la recréation de la connexion eduroam (changement d'identifiant,
par exemple) :

```bash
ssh -t pi@pi-mote-N.local sudo ./setup-pi.sh --force-eduroam
```

Le détail des commandes est donné ci-dessous.

### 3. Eduroam

Paramètres de l'INP Toulouse, issus de son profil
[eduroam CAT](https://cat.eduroam.org) (profil 406) :

| Paramètre                  | Valeur                                    |
| -------------------------- | ----------------------------------------- |
| Méthode                    | PEAP avec MSCHAPv2                        |
| Identité                   | `<login>@inp-toulouse.fr`                 |
| Identité anonyme           | `anonymous@inp-toulouse.fr`               |
| Serveur d'authentification | `eduroam.inp-toulouse.fr`                 |
| Certificat (CA)            | `rootCA.eduroam.inpt`, valide jusqu'en 2034 |

Installer le certificat, propre à l'INP et absent de l'OS :

```bash
sudo mkdir -p /etc/NetworkManager/certs && curl -sL "https://cat.eduroam.org/user/API.php?action=downloadInstaller&api_version=2&lang=en&device=linux&profile=406" | sed -n '/^Config.CA = """/,/"""$/p' | sed -e 's/^Config.CA = """//' -e 's/"""$//' | sudo tee /etc/NetworkManager/certs/eduroam-inpt-ca.pem
```

Vérifier son empreinte :

```bash
openssl x509 -in /etc/NetworkManager/certs/eduroam-inpt-ca.pem -noout -subject -fingerprint -sha256
```

Résultat attendu : `CN=rootCA.eduroam.inpt` et
`AB:95:3A:55:F4:C9:FB:DB:8E:9D:5B:16:EE:80:D1:50:28:C3:1C:3F:C9:AE:B6:69:BA:5A:E6:7A:4A:8B:56:4A`.

Activer le Wi-Fi (bloqué tant que le pays n'est pas défini) :

```bash
sudo raspi-config nonint do_wifi_country FR
```

Créer la connexion :

```bash
sudo nmcli con add type wifi ifname wlan0 con-name eduroam ssid eduroam wifi-sec.key-mgmt wpa-eap 802-1x.eap peap 802-1x.phase2-auth mschapv2 802-1x.identity "<login>@inp-toulouse.fr" 802-1x.anonymous-identity "anonymous@inp-toulouse.fr" 802-1x.ca-cert /etc/NetworkManager/certs/eduroam-inpt-ca.pem 802-1x.domain-suffix-match "eduroam.inp-toulouse.fr" 802-1x.password-flags 0 connection.autoconnect yes
```

Ajouter le mot de passe sans qu'il s'affiche ni reste dans l'historique
(`read` attend la saisie) :

```bash
read -rs PW
```

```bash
sudo nmcli con modify eduroam 802-1x.password "$PW"; unset PW
```

⚠️ Le mot de passe est stocké en clair dans
`/etc/NetworkManager/system-connections/` (lisible par root uniquement).

Se connecter et vérifier que `wlan0` obtient une adresse en `172.17.x.x` :

```bash
sudo nmcli con up eduroam
```

```bash
ip -4 addr show wlan0
```

Tester Internet en forçant la sortie par `wlan0` (la route par défaut reste
eth0 tant que le câble est branché) :

```bash
ping -I wlan0 -c 4 1.1.1.1
```

En cas d'échec : `journalctl -u NetworkManager -n 50 --no-pager`.

### 4. Tailscale

Sur eduroam, les appareils ne peuvent pas se joindre entre eux : l'accès à
distance passe par Tailscale. À installer avec le câble encore branché :

```bash
curl -fsSL https://tailscale.com/install.sh | sh
```

```bash
sudo tailscale up --ssh
```

1. Ouvrir le lien affiché pour autoriser le Pi.
2. Dans la console Tailscale, désactiver l'expiration de clé du Pi
   (« Disable key expiry »), sinon il est déconnecté au bout de 180 jours.
3. Débrancher le câble Ethernet, puis depuis un PC du tailnet :

   ```bash
   ssh pi@pi-mote-N
   ```

Si la connexion aboutit, le Pi sort bien par eduroam.

La règle SSH par défaut de Tailscale redemande une authentification dans le
navigateur environ toutes les 12 heures. Elle bloquera les scripts qui se
connectent sans intervention : il faudra alors l'assouplir dans la politique
d'accès Tailscale.
