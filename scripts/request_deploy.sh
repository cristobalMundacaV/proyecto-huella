#!/usr/bin/env bash
set -Eeuo pipefail

if [[ "$EUID" -ne 0 ]]; then
  exec sudo systemctl start --no-block carbonozero-deploy-worker.service
fi

systemctl start --no-block carbonozero-deploy-worker.service
printf 'Reconciliación solicitada. Logs: journalctl -u carbonozero-deploy-worker.service -f\n'
