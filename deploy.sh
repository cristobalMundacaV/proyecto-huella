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

for command in git docker npm rsync curl; do
  command -v "$command" >/dev/null 2>&1 || fail "Falta el comando requerido: $command"
done

docker compose version >/dev/null 2>&1 || fail "Docker Compose no está disponible"
[[ -d "$APP_DIR/.git" ]] || fail "No existe un repositorio Git en $APP_DIR"
[[ -f "$APP_DIR/.env" ]] || fail "No existe $APP_DIR/.env"
[[ -f "$FRONTEND_DIR/package.json" ]] || fail "No existe el frontend en $FRONTEND_DIR"

cd "$APP_DIR"

if [[ "$SKIP_GIT_UPDATE" != "1" ]]; then
  log "Sincronizando origin/$BRANCH"
  git fetch origin "$BRANCH"
  git reset --hard "origin/$BRANCH"
fi

DEPLOY_SHA="$(git rev-parse --short HEAD)"
log "Desplegando commit $DEPLOY_SHA"

log "Construyendo y levantando servicios Docker"

docker compose down --remove-orphans || true
docker container prune -f >/dev/null 2>&1 || true
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
  npm ci
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
