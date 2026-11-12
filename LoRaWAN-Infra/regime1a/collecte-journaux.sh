#!/usr/bin/env bash
# Collecte des journaux du régime 1a : copie ~/lora-logs de chaque Pi des motes
# vers le serveur, par rsync sur Tailscale. Voir ../README.md, section
# « Collecte automatique des journaux du régime 1a ».
#
# Lancé toutes les 10 min par regime1a-collecte.timer. Les journaux ne font que
# grossir : rsync ne transfère que les ajouts. Côté Pi, la clé est limitée à la
# lecture de ~/lora-logs (rrsync -ro). On passe par le port 2222 : sur le port
# 22, Tailscale SSH intercepte la connexion et ignorerait cette restriction.
# Un Pi injoignable n'arrête pas la
# collecte des autres ; chaque passage est noté dans le fichier d'état.

set -uo pipefail

CONF=${CONF:-"$(dirname "$(readlink -f "$0")")/pis.conf"}
BASE=${BASE:-/srv/regime1a}
KEY=${KEY:-"$HOME/.ssh/regime1a_collecte"}
DEST="$BASE/journaux"
ETAT="$BASE/etat-collecte.csv"

PORT=${PORT:-2222}

SSH="ssh -p $PORT -i $KEY -o BatchMode=yes -o IdentitiesOnly=yes -o ConnectTimeout=15 \
-o StrictHostKeyChecking=accept-new -o UserKnownHostsFile=$BASE/known_hosts"

[[ -f $ETAT ]] || echo "utc,host,ip,statut,code_rsync,octets" > "$ETAT"

echecs=0
while read -r host ip _; do
    [[ -z $host || $host == \#* ]] && continue
    mkdir -p "$DEST/$host"
    # Avec rrsync, le chemin distant est relatif à ~/lora-logs
    rsync -a --timeout=60 -e "$SSH" "pi@$ip:" "$DEST/$host/"
    code=$?
    if (( code == 0 )); then statut=ok; else statut=echec; echecs=$((echecs + 1)); fi
    octets=$(du -sb "$DEST/$host" | cut -f1)
    echo "$(date -u +%FT%TZ),$host,$ip,$statut,$code,$octets" >> "$ETAT"
    echo "$host ($ip) : $statut (rsync $code), $octets octets"
done < "$CONF"

echo "Collecte terminée : $echecs Pi en échec."
