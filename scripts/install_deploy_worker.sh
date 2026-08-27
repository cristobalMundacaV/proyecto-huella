#!/usr/bin/env bash
set -Eeuo pipefail

fail() {
  printf '[INFRA-DEPLOY-01] ERROR: %s\n' "$*" >&2
  exit 1
}

[[ "$EUID" -eq 0 ]] || fail "Ejecuta este instalador con sudo o como root."

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_USER="${APP_USER:-${SUDO_USER:-ubuntu}}"
APP_DIR="${APP_DIR:-$REPO_DIR}"
BRANCH="${BRANCH:-main}"
MAX_ROUNDS="${MAX_ROUNDS:-4}"

id "$APP_USER" >/dev/null 2>&1 || fail "No existe el usuario $APP_USER"
[[ "$APP_USER" != "root" ]] || fail "APP_USER debe ser una cuenta de aplicación no root"
[[ -d "$APP_DIR/.git" ]] || fail "APP_DIR no contiene un repositorio Git: $APP_DIR"
[[ -f "$APP_DIR/deploy.sh" ]] || fail "No existe $APP_DIR/deploy.sh"
[[ "$(stat -c '%U' "$APP_DIR")" == "$APP_USER" ]] || fail "APP_DIR debe pertenecer a $APP_USER"

for command in docker git install runuser stat systemctl systemd-analyze; do
  command -v "$command" >/dev/null 2>&1 || fail "Falta el comando requerido: $command"
done
runuser -u "$APP_USER" -- git -C "$APP_DIR" rev-parse --is-inside-work-tree >/dev/null \
  || fail "$APP_USER no puede leer el repositorio"
runuser -u "$APP_USER" -- git -C "$APP_DIR" remote get-url origin >/dev/null \
  || fail "El repositorio no tiene remote origin accesible"
runuser -u "$APP_USER" -- docker info >/dev/null 2>&1 \
  || fail "$APP_USER no puede acceder al daemon Docker"

for value in "$APP_DIR" "$APP_USER" "$BRANCH" "$MAX_ROUNDS"; do
  [[ "$value" != *$'\n'* ]] || fail "La configuración contiene saltos de línea"
done

install -m 0755 "$REPO_DIR/scripts/deploy_worker.sh" /usr/local/sbin/carbonozero-deploy-worker
install -m 0755 "$REPO_DIR/scripts/request_deploy.sh" /usr/local/sbin/carbonozero-request-deploy
install -m 0644 "$REPO_DIR/ops/systemd/carbonozero-deploy-worker.service" /etc/systemd/system/carbonozero-deploy-worker.service
install -m 0644 "$REPO_DIR/ops/systemd/carbonozero-deploy-worker.timer" /etc/systemd/system/carbonozero-deploy-worker.timer
install -d -o root -g root -m 0755 /var/lib/carbonozero-deploy

umask 022
{
  printf 'APP_DIR=%q\n' "$APP_DIR"
  printf 'APP_USER=%q\n' "$APP_USER"
  printf 'BRANCH=%q\n' "$BRANCH"
  printf 'MAX_ROUNDS=%q\n' "$MAX_ROUNDS"
} > /etc/default/carbonozero-deploy
chmod 0644 /etc/default/carbonozero-deploy

systemd-analyze verify \
  /etc/systemd/system/carbonozero-deploy-worker.service \
  /etc/systemd/system/carbonozero-deploy-worker.timer
systemctl daemon-reload
systemctl enable --now carbonozero-deploy-worker.timer

printf '\nINFRA-DEPLOY-01 instalado.\n'
printf 'Timer:   systemctl status carbonozero-deploy-worker.timer\n'
printf 'Logs:    journalctl -u carbonozero-deploy-worker.service -f\n'
printf 'Manual:  sudo carbonozero-request-deploy\n'
printf 'Estado:  cat /var/lib/carbonozero-deploy/deployed.sha\n'
