import os
import sys


errors = []
for name in ("SECRET_KEY", "POSTGRES_PASSWORD"):
    value = os.environ.get(name, "").strip()
    if not value or value.lower().startswith("replace-with"):
        errors.append(f"{name} is missing or still has the example value")

certbot_email = os.environ.get("CERTBOT_EMAIL", "").strip()
if (
    not certbot_email
    or certbot_email.lower().startswith("replace-with")
    or "@" not in certbot_email
):
    errors.append("CERTBOT_EMAIL is missing or still has the example value")

secret_key = os.environ.get("SECRET_KEY", "")
if len(secret_key) < 50:
    errors.append("SECRET_KEY must be at least 50 characters")

email_backend = os.environ.get(
    "EMAIL_BACKEND",
    "django.core.mail.backends.console.EmailBackend",
)
if email_backend.endswith("console.EmailBackend"):
    errors.append("Configure a production email backend")
elif email_backend.endswith("smtp.EmailBackend"):
    for name in ("EMAIL_HOST", "EMAIL_HOST_USER", "EMAIL_HOST_PASSWORD"):
        value = os.environ.get(name, "").strip()
        if not value or value.lower().startswith("replace-with"):
            errors.append(f"{name} is missing or still has the example value")

if os.environ.get("DEBUG", "False").strip().lower() in {"1", "true", "yes", "on"}:
    errors.append("DEBUG must be False")

allowed_hosts = {
    host.strip() for host in os.environ.get("ALLOWED_HOSTS", "").split(",")
}
for host in ("vkusnodasladko.ru", "www.vkusnodasladko.ru", "129.101.102.189"):
    if host not in allowed_hosts:
        errors.append(f"{host} is missing from ALLOWED_HOSTS")

if os.environ.get("NGINX_BIND_ADDRESS") != "0.0.0.0":
    errors.append("NGINX_BIND_ADDRESS must be 0.0.0.0 on the server")

if errors:
    print("\n".join(f"ERROR: {error}" for error in errors), file=sys.stderr)
    sys.exit(1)

print("Production environment is valid.")
