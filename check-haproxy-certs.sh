#!/bin/bash

CERT_DIR="/etc/haproxy/ssl"
DAYS_WARNING=30

echo "== Local certificates in $CERT_DIR =="

now_epoch=$(date +%s)

for certfile in "$CERT_DIR"/*.pem; do
    domain=$(basename "$certfile" .pem)

    echo -e "\n>>> Checking: $domain ($certfile)"

    if ! openssl x509 -in "$certfile" -noout &>/dev/null; then
        echo "❌ File is not a valid X.509 certificate!"
        continue
    fi

    # Local certificate info
    local_expiry=$(openssl x509 -in "$certfile" -enddate -noout | cut -d= -f2)
    local_fingerprint=$(openssl x509 -in "$certfile" -noout -fingerprint -sha256 | cut -d= -f2)
    local_expiry_epoch=$(date -d "$local_expiry" +%s)
    days_left=$(( (local_expiry_epoch - now_epoch) / 86400 ))

    echo "Local certificate expires on: $local_expiry ($days_left days remaining)"

    if [ "$days_left" -lt 0 ]; then
        echo "❌ Certificate has expired!"
    elif [ "$days_left" -lt "$DAYS_WARNING" ]; then
        echo "⚠️  Certificate will expire soon – only $days_left days left"
    fi

    # HTTPS validation
    echo "Connecting to https://$domain ..."
    cert_output=$(echo | timeout 5 openssl s_client -connect "$domain:443" -servername "$domain" -showcerts 2>/dev/null)
    if [[ $? -ne 0 ]]; then
        echo "❌ HTTPS connection failed – domain is unreachable"
        continue
    fi

    https_expiry=$(echo "$cert_output" | openssl x509 -noout -enddate | cut -d= -f2)
    https_fingerprint=$(echo "$cert_output" | openssl x509 -noout -fingerprint -sha256 | cut -d= -f2)

    echo "HTTPS certificate expires on: $https_expiry"

    if [[ "$https_fingerprint" == "$local_fingerprint" ]]; then
        echo "✅ HTTPS certificate matches local certificate"
    else
        echo "❌ Mismatch between local and HTTPS certificate"
        echo "    Local fingerprint : $local_fingerprint"
        echo "    HTTPS fingerprint : $https_fingerprint"
    fi
done
