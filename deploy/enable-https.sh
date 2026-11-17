#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_root"

test -f .env || {
    echo "ERROR: .env is missing." >&2
    exit 1
}

echo "Starting the HTTP service for the ACME challenge..."
docker compose up -d nginx

published_http_port="$(docker compose port nginx 80)"
case "$published_http_port" in
    0.0.0.0:80)
        ;;
    127.*|localhost:*)
        echo "ERROR: Nginx is bound only to localhost ($published_http_port)." >&2
        echo "Set NGINX_BIND_ADDRESS=0.0.0.0 in .env." >&2
        exit 1
        ;;
    *)
        echo "ERROR: Nginx port 80 is published as '${published_http_port:-unavailable}'." >&2
        echo "Expected 0.0.0.0:80." >&2
        exit 1
        ;;
esac

if ! docker compose exec -T nginx nginx -t; then
    echo "ERROR: Nginx is not running with a valid HTTP configuration. Recent logs:" >&2
    docker compose logs --tail=80 nginx
    exit 1
fi

echo "Confirm TCP port 80 is allowed by both the server and provider firewalls."
echo "Requesting the Let's Encrypt certificate..."
docker compose run --rm --no-deps --entrypoint /bin/sh certbot -ec '
    : "${CERTBOT_EMAIL:?Set CERTBOT_EMAIL in .env}"
    certbot certonly \
        --webroot \
        --webroot-path /var/www/certbot \
        --domain vkusnodasladko.ru \
        --domain www.vkusnodasladko.ru \
        --keep-until-expiring \
        --email "$CERTBOT_EMAIL" \
        --agree-tos \
        --no-eff-email \
        --non-interactive
'

python3 - .env <<'PY'
from pathlib import Path
import sys

env_file = Path(sys.argv[1])
lines = [
    line
    for line in env_file.read_text().splitlines()
    if not line.startswith("HTTPS_ENABLED=")
]
lines.append("HTTPS_ENABLED=True")
env_file.write_text("\n".join(lines) + "\n")
PY

echo "Validating HTTPS configuration..."
docker compose run --rm --no-deps --entrypoint /bin/sh nginx /etc/nginx/start-nginx.sh -t

echo "Restarting the web and Nginx services with HTTPS enabled..."
docker compose up -d --no-deps --build --force-recreate web nginx
docker compose exec -T nginx nginx -t

echo "HTTPS is enabled. Install and start bakery-certbot-renew.timer for automatic renewal."
