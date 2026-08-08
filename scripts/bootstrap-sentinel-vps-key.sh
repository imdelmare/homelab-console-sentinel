#!/usr/bin/env bash
set -Eeuo pipefail

# One-time interactive bootstrap. The password is entered directly into
# ssh-copy-id and is never read from repository configuration or command args.

readonly VPS_TARGET="${HOMELAB_SENTINEL_VPS_TARGET:?set HOMELAB_SENTINEL_VPS_TARGET to the fixed user@host target}"
readonly DEPLOY_KEY="/root/.ssh/homelab_sentinel_deploy"

if (($#)); then
  echo "usage: scripts/bootstrap-sentinel-vps-key.sh" >&2
  exit 2
fi

install -d -m 700 /root/.ssh
if [[ ! -f "$DEPLOY_KEY" ]]; then
  ssh-keygen -q -t ed25519 -N '' -C 'homelab-console-sentinel-deploy' -f "$DEPLOY_KEY"
fi
chmod 600 "$DEPLOY_KEY"
chmod 644 "$DEPLOY_KEY.pub"

echo "Installing the dedicated Sentinel deploy key on the fixed VPS."
echo "Enter the VPS password only at the ssh-copy-id prompt."
ssh-copy-id \
  -i "$DEPLOY_KEY.pub" \
  -o StrictHostKeyChecking=yes \
  "$VPS_TARGET"

echo "Verifying key-only access..."
ssh \
  -o BatchMode=yes \
  -o StrictHostKeyChecking=yes \
  -o IdentitiesOnly=yes \
  -i "$DEPLOY_KEY" \
  "$VPS_TARGET" \
  'true'

echo "Bootstrap complete. Run scripts/deploy-sentinel-vps.sh --check next."
