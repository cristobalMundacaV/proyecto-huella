#!/usr/bin/env bash
set -Eeuo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HTTPS_CONFIG="$REPO_DIR/ops/nginx/carbonozero.conf"
HTTP_CONFIG="$REPO_DIR/ops/nginx/carbonozero-http.conf"

fail() {
  printf '[web infra static test] ERROR: %s\n' "$*" >&2
  exit 1
}

assert_contains() {
  local file="$1"
  local text="$2"
  grep -Fq -- "$text" "$file" || fail "$file no contiene: $text"
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

printf '[web infra static test] OK\n'
