#!/usr/bin/env bash
set -Eeuo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HTTPS_CONFIG="$REPO_DIR/ops/nginx/carbonozero.conf"
HTTP_CONFIG="$REPO_DIR/ops/nginx/carbonozero-http.conf"
INSTALL_SCRIPT="$REPO_DIR/scripts/install_web_infra.sh"
RECONCILE_SCRIPT="$REPO_DIR/scripts/reconcile_web_infra.sh"
DEPLOY_SCRIPT="$REPO_DIR/deploy.sh"
HEALTHCHECK_SCRIPT="$REPO_DIR/scripts/check_web_endpoints.sh"
ARCHITECTURE_DOC="$REPO_DIR/docs/architecture/WEB_INFRASTRUCTURE.md"
README="$REPO_DIR/readme.md"

fail() {
  printf '[web infra static test] ERROR: %s\n' "$*" >&2
  exit 1
}

assert_contains() {
  local file="$1"
  local text="$2"
  grep -Fq -- "$text" "$file" || fail "$file no contiene: $text"
}

assert_not_contains() {
  local file="$1"
  local text="$2"
  if grep -Fq -- "$text" "$file"; then
    fail "$file contiene texto prohibido: $text"
  fi
}

for script in \
  "$REPO_DIR/deploy.sh" \
  "$REPO_DIR/scripts/install_web_infra.sh" \
  "$REPO_DIR/scripts/reconcile_web_infra.sh" \
  "$REPO_DIR/scripts/check_web_endpoints.sh"; do
  bash -n "$script"
done

assert_contains "$HTTP_CONFIG" "location ^~ /.well-known/acme-challenge/"
assert_contains "$HTTP_CONFIG" "root /var/www/certbot;"
assert_contains "$HTTPS_CONFIG" "server_name carbonozero.mundacasolutions.com;"
assert_contains "$HTTPS_CONFIG" "server_name app.carbonozero.mundacasolutions.com;"
assert_contains "$HTTPS_CONFIG" "return 302 https://app.carbonozero.mundacasolutions.com/login;"
assert_contains "$HTTPS_CONFIG" "return 302 /login;"
assert_contains "$HTTPS_CONFIG" "location ^~ /verificar/"
assert_contains "$HTTPS_CONFIG" "proxy_pass http://127.0.0.1:8000;"
assert_contains "$HTTPS_CONFIG" 'add_header X-Robots-Tag "noindex, nofollow" always;'

body_size_count="$(grep -Fc 'client_max_body_size 50M;' "$HTTPS_CONFIG")"
[[ "$body_size_count" == "2" ]] || fail "client_max_body_size 50M debe aparecer en ambos hosts HTTPS"

assert_contains "$INSTALL_SCRIPT" "snapshot_previous_state"
assert_contains "$INSTALL_SCRIPT" "restore_previous_state"
assert_contains "$INSTALL_SCRIPT" "trap cleanup EXIT"
assert_contains "$INSTALL_SCRIPT" "read_letsencrypt_email"
assert_contains "$RECONCILE_SCRIPT" "snapshot_previous_state"
assert_contains "$RECONCILE_SCRIPT" "restore_previous_state"
assert_contains "$RECONCILE_SCRIPT" "trap cleanup EXIT"

assert_not_contains "$ARCHITECTURE_DOC" "source .env"
assert_not_contains "$README" "source .env"
assert_not_contains "$DEPLOY_SCRIPT" "certbot"
assert_contains "$HEALTHCHECK_SCRIPT" '[[ "$location" == "/login" || "$location" == "$APP_LOGIN_URL" ]]'
assert_contains "$HEALTHCHECK_SCRIPT" 'APP_LOGIN_URL="${APP_URL%/}/login"'

# La separación landing/app y sus redirecciones continúan siendo contractuales.
assert_contains "$HTTPS_CONFIG" "server_name carbonozero.mundacasolutions.com;"
assert_contains "$HTTPS_CONFIG" "server_name app.carbonozero.mundacasolutions.com;"
assert_contains "$HTTPS_CONFIG" "return 302 https://app.carbonozero.mundacasolutions.com/login;"
assert_contains "$HTTPS_CONFIG" "return 302 /login;"

printf '[web infra static test] OK\n'
