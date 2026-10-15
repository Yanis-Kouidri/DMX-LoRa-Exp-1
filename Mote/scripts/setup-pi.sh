#!/usr/bin/env bash
# Configure eduroam (INP Toulouse) et installe Tailscale sur un Raspberry Pi
# de contrôle des motes. Voir Mote/raspberry-pi.md.
#
# Usage : sudo ./setup-pi.sh [--force-eduroam]
# À lancer avec le câble Ethernet branché. Le script est idempotent : il peut
# être relancé et saute ce qui est déjà en place. Si la connexion eduroam
# existe et donne accès à Internet, elle est conservée, sauf avec
# --force-eduroam qui la recrée.

set -euo pipefail

CON_NAME="eduroam"
REALM="inp-toulouse.fr"
ANONYMOUS_IDENTITY="anonymous@${REALM}"
SERVER_MATCH="eduroam.${REALM}"
CAT_URL="https://cat.eduroam.org/user/API.php?action=downloadInstaller&api_version=2&lang=en&device=linux&profile=406"
CA_FILE="/etc/NetworkManager/certs/eduroam-inpt-ca.pem"
REPO_URL="https://github.com/Yanis-Kouidri/DMX-LoRa-Exp-1"
REPO_DIR="DMX-LoRa-Exp-1"
CA_FINGERPRINT="AB:95:3A:55:F4:C9:FB:DB:8E:9D:5B:16:EE:80:D1:50:28:C3:1C:3F:C9:AE:B6:69:BA:5A:E6:7A:4A:8B:56:4A"

step() { printf '\n==> %s\n' "$*"; }
die() { printf 'Erreur : %s\n' "$*" >&2; exit 1; }
usage() { printf 'Usage : sudo %s [--force-eduroam]\n' "$0"; }

FORCE_EDUROAM=0
for arg in "$@"; do
    case $arg in
        --force-eduroam) FORCE_EDUROAM=1 ;;
        -h|--help) usage; exit 0 ;;
        *) usage >&2; die "argument inconnu : ${arg}" ;;
    esac
done

[[ $EUID -eq 0 && -n ${SUDO_USER:-} ]] || die "lancer le script avec sudo"

# Vrai si la connexion eduroam existe, est active (ou peut l'être) et donne
# accès à Internet via wlan0.
eduroam_works() {
    nmcli -t -f NAME con show | grep -qx "$CON_NAME" || return 1
    if ! nmcli -t -f NAME con show --active | grep -qx "$CON_NAME"; then
        nmcli --wait 60 con up "$CON_NAME" >/dev/null 2>&1 || return 1
    fi
    ip -4 -o addr show wlan0 | grep -q inet || return 1
    ping -I wlan0 -c 4 -W 2 1.1.1.1 >/dev/null 2>&1
}

configure_eduroam() {
    step "Identifiants eduroam"
    read -rp "Identifiant (login@${REALM}) : " IDENTITY
    [[ $IDENTITY == *@"$REALM" ]] || die "l'identifiant doit être de la forme login@${REALM}"
    read -rsp "Mot de passe : " PW; echo
    read -rsp "Mot de passe (confirmation) : " PW2; echo
    [[ -n $PW ]] || die "mot de passe vide"
    [[ $PW == "$PW2" ]] || die "les mots de passe ne correspondent pas"
    unset PW2

    step "Certificat CA de l'INP Toulouse"
    mkdir -p "$(dirname "$CA_FILE")"
    curl -fsSL "$CAT_URL" \
        | sed -n '/^Config.CA = """/,/"""$/p' \
        | sed -e 's/^Config.CA = """//' -e 's/"""$//' > "$CA_FILE"
    fingerprint=$(openssl x509 -in "$CA_FILE" -noout -fingerprint -sha256 | cut -d= -f2)
    [[ $fingerprint == "$CA_FINGERPRINT" ]] \
        || die "empreinte du certificat inattendue : ${fingerprint}"
    echo "Empreinte vérifiée."

    step "Activation du Wi-Fi"
    raspi-config nonint do_wifi_country FR
    nmcli radio wifi on

    step "Connexion ${CON_NAME}"
    if nmcli -t -f NAME con show | grep -qx "$CON_NAME"; then
        nmcli con delete "$CON_NAME"
    fi
    nmcli con add type wifi ifname wlan0 con-name "$CON_NAME" ssid eduroam \
        wifi-sec.key-mgmt wpa-eap \
        802-1x.eap peap \
        802-1x.phase2-auth mschapv2 \
        802-1x.identity "$IDENTITY" \
        802-1x.anonymous-identity "$ANONYMOUS_IDENTITY" \
        802-1x.ca-cert "$CA_FILE" \
        802-1x.domain-suffix-match "$SERVER_MATCH" \
        802-1x.password-flags 0 \
        connection.autoconnect yes
    nmcli con modify "$CON_NAME" 802-1x.password "$PW"
    unset PW
    nmcli --wait 60 con up "$CON_NAME"

    ip4=$(ip -4 -o addr show wlan0 | awk '{print $4}')
    [[ -n $ip4 ]] || die "wlan0 n'a pas d'adresse IPv4 (journalctl -u NetworkManager -n 50)"
    echo "wlan0 : ${ip4}"
    ping -I wlan0 -c 4 -W 2 1.1.1.1 >/dev/null || die "pas d'accès à Internet via wlan0"
    echo "Accès à Internet via wlan0 : OK"
}

if (( FORCE_EDUROAM )); then
    configure_eduroam
else
    step "Vérification de la connexion ${CON_NAME}"
    if eduroam_works; then
        echo "Connexion existante et fonctionnelle : configuration conservée"
        echo "(relancer avec --force-eduroam pour la recréer)."
    else
        echo "Connexion absente ou sans accès à Internet : configuration."
        configure_eduroam
    fi
fi

step "Passage des dépôts APT en HTTPS"
# Le HTTP est bloqué sur eduroam.
shopt -s nullglob
apt_sources=(/etc/apt/sources.list /etc/apt/sources.list.d/*.list /etc/apt/sources.list.d/*.sources)
shopt -u nullglob
http_sources=()
for f in "${apt_sources[@]}"; do
    if [[ -f $f ]] && grep -q 'http://' "$f"; then
        http_sources+=("$f")
    fi
done
if (( ${#http_sources[@]} )); then
    sed -i 's|http://|https://|g' "${http_sources[@]}"
    printf 'Modifié : %s\n' "${http_sources[@]}"
else
    echo "Dépôts déjà en HTTPS."
fi

step "Mise à jour du système et outils"
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get -y upgrade
apt-get -y install git vim tree

step "Dépôt ${REPO_URL}"
user_home=$(getent passwd "$SUDO_USER" | cut -d: -f6)
if [[ -d "${user_home}/${REPO_DIR}/.git" ]]; then
    echo "Déjà cloné dans ${user_home}/${REPO_DIR}."
else
    sudo -u "$SUDO_USER" git clone "$REPO_URL" "${user_home}/${REPO_DIR}"
fi

step "Tailscale"
if ! command -v tailscale >/dev/null; then
    curl -fsSL https://tailscale.com/install.sh | sh
fi
# tailscale up échoue si le nœud tourne déjà avec d'autres options :
# tailscale set ne modifie que l'option donnée.
if tailscale status --json | grep -q '"BackendState": *"Running"'; then
    echo "Déjà connecté à Tailscale."
    tailscale set --ssh
else
    tailscale up --ssh
fi
tailscale status --self --peers=false

cat <<EOF

Terminé. Reste à faire :
  1. Dans la console Tailscale, désactiver l'expiration de clé de $(hostname).
  2. Débrancher le câble Ethernet, puis tester : ssh ${SUDO_USER}@$(hostname)
EOF
