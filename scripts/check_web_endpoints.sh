#!/usr/bin/env bash
set -Eeuo pipefail

LANDING_URL="${LANDING_URL:-https://carbonozero.mundacasolutions.com}"
APP_URL="${APP_URL:-https://app.carbonozero.mundacasolutions.com}"

fail() {
  printf '[Carbono Zero healthcheck] ERROR: %s\n' "$*" >&2
  exit 1
}

for command in curl grep; do
  command -v "$command" >/dev/null 2>&1 || fail "Falta el comando requerido: $command"
done

status="$(curl -sS -o /dev/null -w '%{http_code}' --max-time 20 "$LANDING_URL/")"
[[ "$status" == "200" ]] || fail "$LANDING_URL/ respondió $status; se esperaba 200"

headers="$(curl -sS -o /dev/null -D - --max-time 20 "$APP_URL/")"
printf '%s' "$headers" | grep -Eq '^HTTP/[^ ]+ 302' || fail "$APP_URL/ no respondió 302"
printf '%s' "$headers" | grep -Eiq '^location: /login\r?$' || fail "$APP_URL/ no redirige a /login"

status="$(curl -sS -o /dev/null -w '%{http_code}' --max-time 20 "$APP_URL/login")"
[[ "$status" == "200" ]] || fail "$APP_URL/login respondió $status; se esperaba 200"

headers="$(curl -sS -o /dev/null -D - --max-time 20 "$LANDING_URL/app")"
printf '%s' "$headers" | grep -Eq '^HTTP/[^ ]+ 302' || fail "$LANDING_URL/app no respondió 302"
printf '%s' "$headers" | grep -Eiq "^location: ${APP_URL//./\.}/login\r?$" || fail "$LANDING_URL/app no redirige a $APP_URL/login"

printf '[Carbono Zero healthcheck] Landing y plataforma disponibles.\n'
