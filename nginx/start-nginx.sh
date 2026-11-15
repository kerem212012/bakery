#!/bin/sh
set -eu

https_enabled="$(printf '%s' "${HTTPS_ENABLED:-false}" | tr '[:upper:]' '[:lower:]')"

case "$https_enabled" in
    true | 1 | yes | on)
        if [ ! -s /etc/letsencrypt/live/vkusnodasladko.ru/fullchain.pem ] || [ ! -s /etc/letsencrypt/live/vkusnodasladko.ru/privkey.pem ]; then
            echo "HTTPS_ENABLED is true, but the Let's Encrypt certificate is missing." >&2
            exit 1
        fi
        cp /etc/nginx/http-https.conf /etc/nginx/conf.d/default.conf
        cp /etc/nginx/https.conf /etc/nginx/conf.d/https.conf
        ;;
    *)
        cp /etc/nginx/http.conf /etc/nginx/conf.d/default.conf
        rm -f /etc/nginx/conf.d/https.conf
        ;;
esac

if [ "$#" -gt 0 ]; then
    exec nginx "$@"
fi

exec nginx -g "daemon off;"
