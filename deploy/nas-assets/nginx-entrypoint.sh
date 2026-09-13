#!/bin/sh
set -eu

certificate=/acme.sh/robot-assets.timo0604.xyz_ecc/fullchain.cer

while [ ! -s "$certificate" ]; do
    echo "Waiting for the first TLS certificate"
    sleep 5
done

last_checksum=$(sha256sum "$certificate" | awk '{print $1}')
(
    while sleep 3600; do
        current_checksum=$(sha256sum "$certificate" | awk '{print $1}')
        if [ "$current_checksum" != "$last_checksum" ]; then
            nginx -s reload
            last_checksum=$current_checksum
        fi
    done
) &

exec nginx -g 'daemon off;'
