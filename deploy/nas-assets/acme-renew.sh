#!/bin/sh
set -eu

config=/run/secrets/ddns-go.yaml
domain=${ASSET_DOMAIN:?ASSET_DOMAIN is required}

yaml_value() {
    sed -n "s/^[[:space:]]*$1:[[:space:]]*//p" "$config" \
        | tail -n 1 \
        | sed "s/^[\"']//; s/[\"']$//"
}

export Ali_Key="$(yaml_value id)"
export Ali_Secret="$(yaml_value secret)"

if [ -z "$Ali_Key" ] || [ -z "$Ali_Secret" ]; then
    echo "AliDNS credentials are unavailable" >&2
    exit 1
fi

acme.sh --set-default-ca --server letsencrypt --home /acme.sh

while :; do
    if [ ! -s "/acme.sh/${domain}_ecc/fullchain.cer" ]; then
        acme.sh --issue --home /acme.sh --server letsencrypt \
            --dns dns_ali --dnssleep 60 --keylength ec-256 -d "$domain"
    else
        acme.sh --cron --home /acme.sh
    fi
    sleep 43200
done
