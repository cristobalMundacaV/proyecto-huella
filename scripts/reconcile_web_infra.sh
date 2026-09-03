#!/usr/bin/env bash
set -Eeuo pipefail

REPO_DIR="${APP_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
SOURCE_CONFIG="$REPO_DIR/ops/nginx/carbonozero.conf"
AVAILABLE_CONFIG="/etc/nginx/sites-available/carbonozero"
ENABLED_CONFIG="/etc/nginx/sites-enabled/carbonozero"
LOCK_FILE="/var/lock/carbonozero-web-infra.lock"
BACKUP_DIR=""
ROLLBACK_ARMED=0
HAD_AVAILABLE=0
HAD_ENABLED=0

fail() {
  printf '[Carbono Zero web] ERROR: %s\n' "$*" >&2
  exit 1
}

for command in nginx install ln systemctl cp rm mktemp rmdir; do
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

snapshot_previous_state() {
  BACKUP_DIR="$(mktemp -d /var/tmp/carbonozero-web-reconcile.XXXXXX)"
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
  printf '[Carbono Zero web] Restaurando configuración Nginx anterior.\n' >&2
  rm -f "$AVAILABLE_CONFIG"
  if [[ "$HAD_AVAILABLE" == "1" ]]; then
    cp -a --no-dereference "$BACKUP_DIR/available" "$AVAILABLE_CONFIG"
  fi
  rm -f "$ENABLED_CONFIG"
  if [[ "$HAD_ENABLED" == "1" ]]; then
    cp -a --no-dereference "$BACKUP_DIR/enabled" "$ENABLED_CONFIG"
  fi
  if nginx -t; then
    systemctl reload nginx || printf '[Carbono Zero web] ERROR: no fue posible recargar Nginx tras el rollback.\n' >&2
  else
    printf '[Carbono Zero web] ERROR: la configuración anterior tampoco supera nginx -t.\n' >&2
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

snapshot_previous_state
install -m 0644 "$SOURCE_CONFIG" "$AVAILABLE_CONFIG"
ln -sfn "$AVAILABLE_CONFIG" "$ENABLED_CONFIG"
nginx -t
systemctl reload nginx
ROLLBACK_ARMED=0

printf '[Carbono Zero web] Configuración Nginx reconciliada.\n'
