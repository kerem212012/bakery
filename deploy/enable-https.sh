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
