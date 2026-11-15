#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_root"

domain="${DEPLOY_DOMAIN:-vkusnodasladko.ru}"
server_ip="${DEPLOY_SERVER_IP:-129.101.102.189}"

command -v docker >/dev/null 2>&1 || {
    echo "ERROR: Docker is not installed." >&2
    exit 1
}
command -v getent >/dev/null 2>&1 || {
    echo "ERROR: getent is required to check DNS." >&2
    exit 1
}
test -f .env || {
    echo "ERROR: .env is missing; copy .env.example and set production secrets." >&2
    exit 1
}

echo "Checking DNS for ${domain}..."
for hostname in "$domain" "www.$domain"; do
    resolved_ips="$(getent ahostsv4 "$hostname" | awk '{print $1}' | sort -u)"
    if ! printf '%s\n' "$resolved_ips" | grep -Fxq "$server_ip"; then
        echo "ERROR: ${hostname} does not resolve to ${server_ip}." >&2
        printf 'Resolved IPv4 addresses: %s\n' "${resolved_ips:-none}" >&2
        exit 1
    fi
done

echo "Checking Compose configuration..."
docker compose config --quiet

echo "Building the application image..."
docker compose build web

echo "Checking production environment..."
docker compose run --rm --no-deps --entrypoint python web deploy/check_environment.py

echo "Running Django deployment checks..."
docker compose run --rm --no-deps --entrypoint gunicorn web --check-config bakery.wsgi:application
docker compose run --rm --no-deps --entrypoint python web manage.py check --deploy
docker compose run --rm --no-deps --entrypoint python web manage.py makemigrations --check --dry-run

echo "Checking Nginx configuration..."
docker compose run --rm --no-deps --entrypoint /bin/sh nginx /etc/nginx/start-nginx.sh -t

echo "After the HTTP service is publicly reachable, run bash deploy/enable-https.sh."
echo "Pre-deployment checks passed."
