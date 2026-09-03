#!/usr/bin/env bash
set -Eeuo pipefail

REPO_DIR="${APP_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
HTTP_CONFIG="$REPO_DIR/ops/nginx/carbonozero-http.conf"
AVAILABLE_CONFIG="/etc/nginx/sites-available/carbonozero"
ENABLED_CONFIG="/etc/nginx/sites-enabled/carbonozero"
CERT_NAME="carbonozero.mundacasolutions.com"
CERT_PATH="/etc/letsencrypt/live/$CERT_NAME/fullchain.pem"
LOCK_FILE="/var/lock/carbonozero-web-infra.lock"
ENV_FILE="$REPO_DIR/.env"
DOMAINS=("carbonozero.mundacasolutions.com" "app.carbonozero.mundacasolutions.com")
BACKUP_DIR=""
ROLLBACK_ARMED=0
HAD_AVAILABLE=0
HAD_ENABLED=0

fail() {
  printf '[Carbono Zero web install] ERROR: %s\n' "$*" >&2
  exit 1
}

[[ "$EUID" -eq 0 ]] || fail "Ejecuta install_web_infra.sh con sudo o como root."
for command in nginx certbot openssl install ln flock systemctl cp grep rm mktemp rmdir sed tr; do
  command -v "$command" >/dev/null 2>&1 || fail "Falta el comando requerido: $command"
done
[[ -f "$HTTP_CONFIG" ]] || fail "No existe $HTTP_CONFIG"
[[ -f "$REPO_DIR/scripts/reconcile_web_infra.sh" ]] || fail "Falta scripts/reconcile_web_infra.sh"

touch "$LOCK_FILE"
exec 9>"$LOCK_FILE"
flock -n 9 || fail "Ya existe una instalación/reconciliación web activa."

snapshot_previous_state() {
  BACKUP_DIR="$(mktemp -d /var/tmp/carbonozero-web-install.XXXXXX)"
  if [[ -e "$AVAILABLE_CONFIG" || -L "$AVAILABLE_CONFIG" ]]; then
    cp -a --no-dereference "$AVAILABLE_CONFIG" "$BACKUP_DIR/available"
    HAD_AVAILABLE=1
  fi
  if [[ -e "$ENABLED_CONFIG" || -L "$ENABLED_CONFIG" ]]; then
    cp -a --no-dereference "$ENABLED_CONFIG" "$BACKUP_DIR/enabled"
    HAD_ENABLED=1
  fi
  ROLLBACK_ARMED=1
}

restore_previous_state() {
  set +e
  printf '[Carbono Zero web install] Restaurando configuración Nginx anterior.\n' >&2
  rm -f "$AVAILABLE_CONFIG"
  if [[ "$HAD_AVAILABLE" == "1" ]]; then
    cp -a --no-dereference "$BACKUP_DIR/available" "$AVAILABLE_CONFIG"
  fi
  rm -f "$ENABLED_CONFIG"
  if [[ "$HAD_ENABLED" == "1" ]]; then
    cp -a --no-dereference "$BACKUP_DIR/enabled" "$ENABLED_CONFIG"
  fi
  if nginx -t; then
    systemctl reload nginx || printf '[Carbono Zero web install] ERROR: no fue posible recargar Nginx tras el rollback.\n' >&2
  else
    printf '[Carbono Zero web install] ERROR: la configuración anterior tampoco supera nginx -t.\n' >&2
  fi
}

cleanup() {
  local exit_code=$?
  trap - EXIT
  if [[ "$exit_code" != "0" && "$ROLLBACK_ARMED" == "1" ]]; then
    restore_previous_state
  fi
  if [[ -n "$BACKUP_DIR" ]]; then
    rm -f "$BACKUP_DIR/available" "$BACKUP_DIR/enabled"
    rmdir "$BACKUP_DIR" 2>/dev/null || true
  fi
  exit "$exit_code"
}
trap cleanup EXIT

read_letsencrypt_email() {
  local line value
  [[ -f "$ENV_FILE" ]] || return 1
  line="$(grep -m 1 -E '^[[:space:]]*LETSENCRYPT_EMAIL=' "$ENV_FILE" || true)"
  [[ -n "$line" ]] || return 1
  value="${line#*=}"
  value="$(printf '%s' "$value" | tr -d '\r' | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"
  if [[ "$value" == \"*\" && "$value" == *\" ]]; then
    value="${value:1:${#value}-2}"
  elif [[ "$value" == \'*\' && "$value" == *\' ]]; then
    value="${value:1:${#value}-2}"
  fi
  printf '%s' "$value"
}

if [[ -z "${LETSENCRYPT_EMAIL:-}" ]]; then
  LETSENCRYPT_EMAIL="$(read_letsencrypt_email || true)"
fi
[[ -n "$LETSENCRYPT_EMAIL" ]] || fail "LETSENCRYPT_EMAIL está vacío; complétalo en $ENV_FILE o en el environment."
[[ "$LETSENCRYPT_EMAIL" =~ ^[^[:space:]@]+@[^[:space:]@]+\.[^[:space:]@]+$ ]] \
  || fail "LETSENCRYPT_EMAIL no tiene un formato de email válido."

snapshot_previous_state
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
  certbot certonly \
    --webroot --webroot-path /var/www/certbot \
    --cert-name "$CERT_NAME" --expand \
    --domain "${DOMAINS[0]}" --domain "${DOMAINS[1]}" \
    --email "$LETSENCRYPT_EMAIL" --agree-tos --non-interactive
fi

APP_DIR="$REPO_DIR" WEB_INFRA_LOCK_HELD=1 bash "$REPO_DIR/scripts/reconcile_web_infra.sh"
ROLLBACK_ARMED=0
printf '[Carbono Zero web install] Infraestructura web instalada.\n'
