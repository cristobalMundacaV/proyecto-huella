#!/usr/bin/env bash
set -Eeuo pipefail

REPO_DIR="${APP_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
SOURCE_CONFIG="$REPO_DIR/ops/nginx/carbonozero.conf"
AVAILABLE_CONFIG="/etc/nginx/sites-available/carbonozero"
ENABLED_CONFIG="/etc/nginx/sites-enabled/carbonozero"
LOCK_FILE="/var/lock/carbonozero-web-infra.lock"

fail() {
  printf '[Carbono Zero web] ERROR: %s\n' "$*" >&2
  exit 1
}

for command in nginx install ln systemctl; do
  command -v "$command" >/dev/null 2>&1 || fail "Falta el comando requerido: $command"
done
[[ "$EUID" -eq 0 ]] || fail "Ejecuta reconcile_web_infra.sh con sudo o como root."
[[ -f "$SOURCE_CONFIG" ]] || fail "No existe la configuración versionada: $SOURCE_CONFIG"

if [[ "${WEB_INFRA_LOCK_HELD:-0}" != "1" ]]; then
  command -v flock >/dev/null 2>&1 || fail "Falta el comando requerido: flock"
  touch "$LOCK_FILE"
  exec 9>"$LOCK_FILE"
  flock -n 9 || fail "Ya existe una instalación/reconciliación web activa."
fi

install -m 0644 "$SOURCE_CONFIG" "$AVAILABLE_CONFIG"
ln -sfn "$AVAILABLE_CONFIG" "$ENABLED_CONFIG"
nginx -t
systemctl reload nginx

printf '[Carbono Zero web] Configuración Nginx reconciliada.\n'
