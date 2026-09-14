#!/usr/bin/env bash
set -Eeuo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEPLOY="$REPO_DIR/deploy.sh"
WORKER="$REPO_DIR/scripts/deploy_worker.sh"
INSTALLER="$REPO_DIR/scripts/install_deploy_worker.sh"
SERVICE="$REPO_DIR/ops/systemd/carbonozero-deploy-worker.service"
TIMER="$REPO_DIR/ops/systemd/carbonozero-deploy-worker.timer"

fail() { printf '[deploy worker static test] ERROR: %s\n' "$*" >&2; exit 1; }
contains() { grep -Fq -- "$2" "$1" || fail "$1 no contiene: $2"; }
excludes() { ! grep -Fq -- "$2" "$1" || fail "$1 contiene texto obsoleto: $2"; }

bash -n "$DEPLOY" "$WORKER" "$INSTALLER"

contains "$DEPLOY" 'clear_stale_git_lock'
contains "$DEPLOY" 'docker compose up -d --build --remove-orphans'
excludes "$DEPLOY" 'docker compose down'
contains "$DEPLOY" 'node_modules/.carbonozero-lock.sha256'
contains "$WORKER" 'APP_DEPLOY_LOCK="$APP_DIR/.git/carbonozero-deploy.lock"'
contains "$WORKER" 'DEPLOY_LOCK_HELD=1'
contains "$WORKER" 'systemd volverá a intentarlo'
contains "$SERVICE" 'Restart=on-failure'
contains "$TIMER" 'OnUnitInactiveSec=15s'
contains "$TIMER" 'AccuracySec=1s'

printf '[deploy worker static test] OK\n'
