#!/bin/bash
# Generate the private CA and the server certificate used by the Basic Station
# (LNS) TLS listener of the Gateway Bridge.
#
# ChirpStack signs per-gateway client certificates with the same CA, and the
# Gateway Bridge only accepts gateways presenting one of them.
# Never re-run once gateways are provisioned: a new CA invalidates their
# certificates. The script refuses to overwrite an existing CA.
set -euo pipefail

cd "$(dirname "$0")/.."
CERTS_DIR=configuration/certs
GATEWAY_TLS_HOST=${GATEWAY_TLS_HOST:-chirpstack.kouidri.fr}
CERTS_GID=65533 # nogroup, the group of the ChirpStack containers

if [ -e "$CERTS_DIR/ca.pem" ]; then
    echo "$CERTS_DIR/ca.pem already exists, refusing to overwrite it" >&2
    exit 1
fi

mkdir -p "$CERTS_DIR"
umask 077

openssl req -x509 -newkey ec -pkeyopt ec_paramgen_curve:prime256v1 -nodes -days 3650 \
    -subj "/CN=LoRaWAN-Infra gateway CA" \
    -addext "basicConstraints=critical,CA:TRUE" \
    -addext "keyUsage=critical,keyCertSign,cRLSign" \
    -keyout "$CERTS_DIR/ca-key.pem" -out "$CERTS_DIR/ca.pem"

openssl req -newkey ec -pkeyopt ec_paramgen_curve:prime256v1 -nodes \
    -subj "/CN=$GATEWAY_TLS_HOST" \
    -keyout "$CERTS_DIR/server-key.pem" -out "$CERTS_DIR/server.csr"
openssl x509 -req -in "$CERTS_DIR/server.csr" \
    -CA "$CERTS_DIR/ca.pem" -CAkey "$CERTS_DIR/ca-key.pem" -CAcreateserial -days 825 \
    -extfile <(printf 'subjectAltName=DNS:%s\nextendedKeyUsage=serverAuth\nkeyUsage=critical,digitalSignature\n' "$GATEWAY_TLS_HOST") \
    -out "$CERTS_DIR/server.pem"
rm -f "$CERTS_DIR/server.csr" "$CERTS_DIR/ca.srl"

chmod 755 "$CERTS_DIR"
chmod 644 "$CERTS_DIR/ca.pem" "$CERTS_DIR/server.pem"
chmod 640 "$CERTS_DIR/ca-key.pem" "$CERTS_DIR/server-key.pem"
sudo chgrp "$CERTS_GID" "$CERTS_DIR/ca-key.pem" "$CERTS_DIR/server-key.pem"

echo "Generated in $CERTS_DIR:"
ls -l "$CERTS_DIR"
