#!/usr/bin/env bash
set -Eeuo pipefail

# Fixed, narrow operator deployment for the documented External Sentinel VPS.
# This script intentionally accepts no host, path or command arguments.

readonly VPS_TARGET="root@49.13.159.26"
readonly REMOTE_DIR="/opt/homelab-console-sentinel"
readonly REMOTE_ENV="${REMOTE_DIR}/.env.sentinel"
readonly LOCAL_ENV=".env"
readonly DEPLOY_KEY="/root/.ssh/homelab_sentinel_deploy"
readonly RSYNC_SSH="ssh -o BatchMode=yes -o ConnectTimeout=10 -o StrictHostKeyChecking=yes -o IdentitiesOnly=yes -i ${DEPLOY_KEY}"
readonly SSH_OPTIONS=(
  -o BatchMode=yes
  -o ConnectTimeout=10
  -o StrictHostKeyChecking=yes
  -o IdentitiesOnly=yes
  -i "$DEPLOY_KEY"
)

usage() {
  echo "usage: deploy/deploy-sentinel-vps.sh [--check]" >&2
}

mode="deploy"
if [[ ${1:-} == "--check" ]]; then
  mode="check"
  shift
fi
if (($#)); then
  usage
  exit 2
fi
if [[ ! -f "$LOCAL_ENV" ]]; then
  echo "missing local .env" >&2
  exit 1
fi
if [[ ! -f "$DEPLOY_KEY" ]]; then
  echo "missing dedicated deploy key; run deploy/bootstrap-sentinel-vps-key.sh" >&2
  exit 1
fi

echo "Checking fixed Sentinel target..."
ssh "${SSH_OPTIONS[@]}" "$VPS_TARGET" \
  "test -d '$REMOTE_DIR' && test -f '$REMOTE_ENV' && test -f '$REMOTE_DIR/config/sentinel.local.json' && test -d '$REMOTE_DIR/data'"

if [[ "$mode" == "check" ]]; then
  ssh "${SSH_OPTIONS[@]}" "$VPS_TARGET" \
    "docker inspect homelab-sentinel --format 'container={{.Name}} status={{.State.Status}} image={{.Config.Image}}' && curl -fsS http://192.0.2.10:8766/health"
  exit 0
fi

echo "Synchronizing fixed Sentinel release files..."
ssh "${SSH_OPTIONS[@]}" "$VPS_TARGET" \
  "mkdir -p '$REMOTE_DIR/apps/sentinel/sentinel' '$REMOTE_DIR/deploy'"
rsync -a --delete -e "$RSYNC_SSH" \
  apps/sentinel/sentinel/ "$VPS_TARGET:$REMOTE_DIR/apps/sentinel/sentinel/"
rsync -a -e "$RSYNC_SSH" \
  deploy/Dockerfile.sentinel \
  deploy/update-sentinel-secrets.py \
  "$VPS_TARGET:$REMOTE_DIR/deploy/"

echo "Synchronizing Telegram credentials..."
python3 - "$LOCAL_ENV" <<'PY' | ssh "${SSH_OPTIONS[@]}" "$VPS_TARGET" \
  "cd '$REMOTE_DIR' && python3 deploy/update-sentinel-secrets.py '$REMOTE_ENV'"
import json
import sys
from pathlib import Path

allowed = ("TELEGRAM_BOT_TOKEN", "TELEGRAM_ALLOWED_CHAT_ID")
values = {}
for raw_line in Path(sys.argv[1]).read_text(encoding="utf-8").splitlines():
    line = raw_line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    key, value = line.split("=", 1)
    if key.strip() in allowed:
        values[key.strip()] = value.strip()
if set(values) != set(allowed) or not all(values.values()):
    raise SystemExit("local .env is missing non-empty Telegram credentials")
json.dump(values, sys.stdout)
PY

echo "Building and restarting Sentinel..."
ssh "${SSH_OPTIONS[@]}" "$VPS_TARGET" \
  "cd '$REMOTE_DIR' && flock -w 60 /tmp/homelab-sentinel-deploy.lock sh -c 'set -eu; if docker image inspect homelab-sentinel:latest >/dev/null 2>&1; then docker tag homelab-sentinel:latest homelab-sentinel:rollback; fi; docker build -f deploy/Dockerfile.sentinel -t homelab-sentinel:latest .; docker rm -f homelab-sentinel >/dev/null 2>&1 || true; docker run -d --name homelab-sentinel --restart unless-stopped --env-file .env.sentinel -v ${REMOTE_DIR}/config:/app/config:ro -v ${REMOTE_DIR}/data:/app/data -p 192.0.2.10:8766:8766 homelab-sentinel:latest'"

echo "Waiting for Sentinel health..."
ssh "${SSH_OPTIONS[@]}" "$VPS_TARGET" \
  "for attempt in \$(seq 1 12); do curl -fsS http://192.0.2.10:8766/health >/dev/null && exit 0; sleep 5; done; docker logs --tail 80 homelab-sentinel >&2; docker rm -f homelab-sentinel >/dev/null 2>&1 || true; if docker image inspect homelab-sentinel:rollback >/dev/null 2>&1; then docker run -d --name homelab-sentinel --restart unless-stopped --env-file '$REMOTE_ENV' -v ${REMOTE_DIR}/config:/app/config:ro -v ${REMOTE_DIR}/data:/app/data -p 192.0.2.10:8766:8766 homelab-sentinel:rollback; fi; exit 1"

echo "Verifying deployed service..."
ssh "${SSH_OPTIONS[@]}" "$VPS_TARGET" \
  "docker inspect homelab-sentinel --format 'container={{.Name}} status={{.State.Status}} image={{.Config.Image}}' && curl -fsS http://192.0.2.10:8766/health && docker logs --tail 20 homelab-sentinel 2>&1"
