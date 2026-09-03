#!/usr/bin/env bash
set -Eeuo pipefail

REPO_DIR="${APP_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
HTTP_CONFIG="$REPO_DIR/ops/nginx/carbonozero-http.conf"
AVAILABLE_CONFIG="/etc/nginx/sites-available/carbonozero"
ENABLED_CONFIG="/etc/nginx/sites-enabled/carbonozero"
CERT_NAME="carbonozero.mundacasolutions.com"
CERT_PATH="/etc/letsencrypt/live/$CERT_NAME/fullchain.pem"
LOCK_FILE="/var/lock/carbonozero-web-infra.lock"
DOMAINS=("carbonozero.mundacasolutions.com" "app.carbonozero.mundacasolutions.com")

fail() {
  printf '[Carbono Zero web install] ERROR: %s\n' "$*" >&2
  exit 1
}

[[ "$EUID" -eq 0 ]] || fail "Ejecuta install_web_infra.sh con sudo o como root."
for command in nginx certbot openssl install ln flock systemctl; do
  command -v "$command" >/dev/null 2>&1 || fail "Falta el comando requerido: $command"
done
[[ -f "$HTTP_CONFIG" ]] || fail "No existe $HTTP_CONFIG"
[[ -f "$REPO_DIR/scripts/reconcile_web_infra.sh" ]] || fail "Falta scripts/reconcile_web_infra.sh"

touch "$LOCK_FILE"
exec 9>"$LOCK_FILE"
flock -n 9 || fail "Ya existe una instalación/reconciliación web activa."

install -d -m 0755 /var/www/carbonozero /var/www/certbot
install -m 0644 "$HTTP_CONFIG" "$AVAILABLE_CONFIG"
ln -sfn "$AVAILABLE_CONFIG" "$ENABLED_CONFIG"
nginx -t
systemctl reload nginx

certificate_has_domains() {
  [[ -f "$CERT_PATH" ]] || return 1
  local sans
  sans="$(openssl x509 -in "$CERT_PATH" -noout -ext subjectAltName 2>/dev/null || true)"
  for domain in "${DOMAINS[@]}"; do
    [[ "$sans" == *"DNS:$domain"* ]] || return 1
  done
}

if certificate_has_domains; then
  printf '[Carbono Zero web install] El certificado ya contiene ambos hosts; Certbot no se ejecuta.\n'
else
  [[ -n "${LETSENCRYPT_EMAIL:-}" ]] || fail "Define LETSENCRYPT_EMAIL para solicitar o expandir el certificado."
  certbot certonly \
    --webroot --webroot-path /var/www/certbot \
    --cert-name "$CERT_NAME" --expand \
    --domain "${DOMAINS[0]}" --domain "${DOMAINS[1]}" \
    --email "$LETSENCRYPT_EMAIL" --agree-tos --non-interactive
fi

APP_DIR="$REPO_DIR" WEB_INFRA_LOCK_HELD=1 bash "$REPO_DIR/scripts/reconcile_web_infra.sh"
printf '[Carbono Zero web install] Infraestructura web instalada.\n'
