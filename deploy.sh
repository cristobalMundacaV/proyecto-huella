#!/usr/bin/env bash
set -Eeuo pipefail

APP_DIR="${APP_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"
FRONTEND_DIR="${FRONTEND_DIR:-$APP_DIR/frontend}"
WEB_ROOT="${WEB_ROOT:-/var/www/carbonozero}"
BRANCH="${BRANCH:-main}"
LANDING_URL="${LANDING_URL:-https://carbonozero.mundacasolutions.com}"
APP_URL="${APP_URL:-https://app.carbonozero.mundacasolutions.com}"
SKIP_GIT_UPDATE="${SKIP_GIT_UPDATE:-0}"

log() {
  printf '\n\033[1;32m[Carbono Zero]\033[0m %s\n' "$1"
}

fail() {
  printf '\n\033[1;31m[Error]\033[0m %s\n' "$1" >&2
  exit 1
}

on_error() {
  local exit_code=$?
  printf '\n\033[1;31m[Deploy fallido]\033[0m línea %s, código %s\n' "$1" "$exit_code" >&2
  exit "$exit_code"
}
trap 'on_error $LINENO' ERR

for command in git docker npm rsync curl flock fuser sha256sum awk; do
  command -v "$command" >/dev/null 2>&1 || fail "Falta el comando requerido: $command"
done

docker compose version >/dev/null 2>&1 || fail "Docker Compose no está disponible"
[[ -d "$APP_DIR/.git" ]] || fail "No existe un repositorio Git en $APP_DIR"
[[ -f "$APP_DIR/.env" ]] || fail "No existe $APP_DIR/.env"
[[ -f "$FRONTEND_DIR/package.json" ]] || fail "No existe el frontend en $FRONTEND_DIR"

cd "$APP_DIR"

DEPLOY_LOCK_FILE="${DEPLOY_LOCK_FILE:-$APP_DIR/.git/carbonozero-deploy.lock}"
if [[ "${DEPLOY_LOCK_HELD:-0}" != "1" ]]; then
  exec 8>"$DEPLOY_LOCK_FILE"
  if ! flock -n 8; then
    fail "Ya existe otro despliegue activo. Sigue sus logs en lugar de iniciar uno en paralelo."
  fi
fi

clear_stale_git_lock() {
  local index_lock="$APP_DIR/.git/index.lock"
  [[ -e "$index_lock" ]] || return 0
  if fuser "$index_lock" >/dev/null 2>&1; then
    fail "Existe una operación Git activa usando $index_lock"
  fi
  log "Retirando lock Git huérfano: $index_lock"
  rm -f -- "$index_lock"
}

if [[ "$SKIP_GIT_UPDATE" != "1" ]]; then
  log "Sincronizando origin/$BRANCH"
  clear_stale_git_lock
  git fetch origin "$BRANCH"
  clear_stale_git_lock
  git reset --hard "origin/$BRANCH"
fi

DEPLOY_SHA="$(git rev-parse --short HEAD)"
log "Desplegando commit $DEPLOY_SHA"

log "Construyendo y levantando servicios Docker"

# Reconcilia servicios y elimina huérfanos sin detener previamente la base de
# datos ni provocar una ventana de caída innecesaria.
docker compose up -d --build --remove-orphans

log "Esperando al backend"
backend_ready=0
for attempt in $(seq 1 30); do
  if docker compose exec -T backend python manage.py check >/dev/null 2>&1; then
    backend_ready=1
    break
  fi
  sleep 2
done
[[ "$backend_ready" == "1" ]] || fail "El backend no quedó disponible después de 60 segundos"

log "Aplicando migraciones y recopilando archivos estáticos"
docker compose exec -T backend python manage.py migrate --noinput
docker compose exec -T backend python manage.py collectstatic --noinput

log "Construyendo frontend"
cd "$FRONTEND_DIR"
rm -rf dist node_modules/.vite
if [[ -f package-lock.json ]]; then
  dependency_fingerprint="$(sha256sum package-lock.json | awk '{print $1}')"
  installed_fingerprint=""
  [[ -f node_modules/.carbonozero-lock.sha256 ]] \
    && installed_fingerprint="$(tr -d '[:space:]' < node_modules/.carbonozero-lock.sha256)"
  if [[ ! -d node_modules || "$dependency_fingerprint" != "$installed_fingerprint" ]]; then
    log "Instalando dependencias frontend (package-lock actualizado)"
    npm ci
    printf '%s\n' "$dependency_fingerprint" > node_modules/.carbonozero-lock.sha256
  else
    log "Dependencias frontend sin cambios; reutilizando node_modules"
  fi
else
  npm install
fi
npm run build
[[ -f dist/index.html ]] || fail "El build no generó frontend/dist/index.html"

log "Publicando frontend versionado en $WEB_ROOT"
sudo mkdir -p "$WEB_ROOT"
# Conserva assets de versiones anteriores para que clientes con HTML cacheado
# no queden apuntando a chunks eliminados durante un despliegue.
sudo rsync -a dist/ "$WEB_ROOT/"

log "Reconciliando Nginx desde la configuración versionada"
sudo env APP_DIR="$APP_DIR" bash "$APP_DIR/scripts/reconcile_web_infra.sh"

log "Comprobando servicios"
docker compose ps
LANDING_URL="$LANDING_URL" APP_URL="$APP_URL" bash "$APP_DIR/scripts/check_web_endpoints.sh"

log "Deploy completado correctamente: $DEPLOY_SHA"
printf 'Landing: %s\n' "$LANDING_URL"
printf 'Plataforma: %s\n' "$APP_URL"
