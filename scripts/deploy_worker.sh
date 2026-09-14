#!/usr/bin/env bash
set -Eeuo pipefail

APP_DIR="${APP_DIR:-/home/ubuntu/proyecto-huella}"
APP_USER="${APP_USER:-ubuntu}"
BRANCH="${BRANCH:-main}"
STATE_DIR="${STATE_DIR:-/var/lib/carbonozero-deploy}"
LOCK_FILE="${LOCK_FILE:-/var/lock/carbonozero-deploy-worker.lock}"
MAX_ROUNDS="${MAX_ROUNDS:-4}"
RETRY_DELAY_SECONDS="${RETRY_DELAY_SECONDS:-15}"
DEPLOYED_SHA_FILE="$STATE_DIR/deployed.sha"

log() {
  printf '[Carbono Zero deploy] %s\n' "$*"
}

fail() {
  log "ERROR: $*"
  exit 1
}

as_app_user() {
  runuser -u "$APP_USER" -- "$@"
}

git_as_app_user() {
  as_app_user git -C "$APP_DIR" "$@"
}

clear_stale_git_lock() {
  local index_lock="$APP_DIR/.git/index.lock"
  [[ -e "$index_lock" ]] || return 0

  # Git mantiene abierto index.lock mientras lo usa. Si ningún proceso tiene
  # el descriptor, el archivo pertenece a una ejecución interrumpida.
  if command -v fuser >/dev/null 2>&1 && fuser "$index_lock" >/dev/null 2>&1; then
    fail "Existe una operación Git activa usando $index_lock"
  fi

  log "Retirando lock Git huérfano: $index_lock"
  rm -f -- "$index_lock"
}

for command in flock git runuser; do
  command -v "$command" >/dev/null 2>&1 || fail "Falta el comando requerido: $command"
done

[[ "$EUID" -eq 0 ]] || fail "El worker debe ejecutarse como root mediante systemd."
id "$APP_USER" >/dev/null 2>&1 || fail "No existe el usuario de aplicación: $APP_USER"
[[ -d "$APP_DIR/.git" ]] || fail "No existe un checkout Git en $APP_DIR"
[[ -f "$APP_DIR/deploy.sh" ]] || fail "No existe $APP_DIR/deploy.sh"
[[ "$MAX_ROUNDS" =~ ^[1-9][0-9]*$ ]] || fail "MAX_ROUNDS debe ser un entero positivo"
[[ "$RETRY_DELAY_SECONDS" =~ ^[1-9][0-9]*$ ]] || fail "RETRY_DELAY_SECONDS debe ser un entero positivo"

install -d -m 0755 "$STATE_DIR"
touch "$LOCK_FILE"
exec 9>"$LOCK_FILE"
if ! flock -n 9; then
  log "Ya existe un despliegue activo"
  exit 0
fi

# Este segundo lock también lo respeta deploy.sh cuando alguien intenta
# ejecutarlo manualmente. Cubre checkout, reset y despliegue como una unidad.
APP_DEPLOY_LOCK="$APP_DIR/.git/carbonozero-deploy.lock"
touch "$APP_DEPLOY_LOCK"
chown "$APP_USER":"$(id -gn "$APP_USER")" "$APP_DEPLOY_LOCK"
chmod 0664 "$APP_DEPLOY_LOCK"
exec 8>"$APP_DEPLOY_LOCK"
if ! flock -n 8; then
  log "Existe un despliegue manual activo; el timer lo revisará nuevamente"
  exit 0
fi

deployed_sha=""
last_deploy_failed=0
if [[ -f "$DEPLOYED_SHA_FILE" ]]; then
  deployed_sha="$(tr -d '[:space:]' < "$DEPLOYED_SHA_FILE")"
fi

for ((round = 1; round <= MAX_ROUNDS; round++)); do
  log "Ronda $round/$MAX_ROUNDS: consultando origin/$BRANCH"
  clear_stale_git_lock
  git_as_app_user fetch --prune origin "$BRANCH"
  target_sha="$(git_as_app_user rev-parse --verify "refs/remotes/origin/$BRANCH")"
  [[ "$target_sha" =~ ^[0-9a-f]{40}$ ]] || fail "SHA remoto inválido"

  log "SHA desplegado: ${deployed_sha:-ninguno}"
  log "SHA objetivo: $target_sha"
  if [[ "$target_sha" == "$deployed_sha" ]]; then
    log "No hay cambios desplegables"
    exit 0
  fi

  log "Sincronizando checkout productivo con $target_sha"
  clear_stale_git_lock
  git_as_app_user checkout -B "$BRANCH" "origin/$BRANCH"
  git_as_app_user reset --hard "$target_sha"

  log "Iniciando despliegue de $target_sha"
  if ! as_app_user env \
    APP_DIR="$APP_DIR" \
    BRANCH="$BRANCH" \
    DEPLOY_LOCK_HELD=1 \
    SKIP_GIT_UPDATE=1 \
    bash "$APP_DIR/deploy.sh"; then
    log "Falló el despliegue de $target_sha; reintentando en ${RETRY_DELAY_SECONDS}s"
    last_deploy_failed=1
    sleep "$RETRY_DELAY_SECONDS"
    continue
  fi

  last_deploy_failed=0

  temporary_sha="$STATE_DIR/.deployed.sha.$$"
  printf '%s\n' "$target_sha" > "$temporary_sha"
  mv -f "$temporary_sha" "$DEPLOYED_SHA_FILE"
  deployed_sha="$target_sha"
  log "Despliegue exitoso; SHA registrado: $deployed_sha"

  git_as_app_user fetch --prune origin "$BRANCH"
  latest_sha="$(git_as_app_user rev-parse --verify "refs/remotes/origin/$BRANCH")"
  if [[ "$latest_sha" == "$deployed_sha" ]]; then
    log "origin/$BRANCH permanece en $deployed_sha; reconciliación completa"
    exit 0
  fi
  log "Se detectó un push nuevo durante el despliegue: $latest_sha"
done

if [[ "$last_deploy_failed" == "1" ]]; then
  fail "Se agotaron $MAX_ROUNDS intentos; systemd volverá a intentarlo"
fi
log "Se alcanzó MAX_ROUNDS=$MAX_ROUNDS; el siguiente timer continuará la reconciliación"
exit 0
