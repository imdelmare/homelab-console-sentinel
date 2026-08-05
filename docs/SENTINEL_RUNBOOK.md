# External Sentinel Runbook

This is the third deployment step: prove the Sentinel actually alerts and
recovers before relying on it.

No real VPS hostnames, Telegram tokens or heartbeat tokens belong in this repo.
Use `deploy/env.sentinel.example`, `config/sentinel.example.json` and
`deploy/systemd/sentinel-heartbeat.env.example` only as templates.

## Step 1: VPS Only

### Routine deploy from Homelab Console

After the initial VPS setup below, routine deployments can be launched from
the Homelab Console checkout. The script has a fixed VPS and remote path, uses
strict host-key checking, preserves the remote heartbeat token/config/state,
and synchronizes only the two Telegram values from the local `.env` over SSH
stdin:

```bash
deploy/bootstrap-sentinel-vps-key.sh  # one time, interactive password prompt
deploy/deploy-sentinel-vps.sh --check
deploy/deploy-sentinel-vps.sh --update-public-health
deploy/deploy-sentinel-vps.sh
```

It synchronizes only the fixed Sentinel package and Docker build files,
preserving remote `.env.sentinel`, `config/` and `data/`. Deployments are
serialized with `flock`; the script tags the previous image for rollback,
recreates the fixed `homelab-sentinel` container with its private WireGuard
bind, and waits for `/health`. No credentials are printed or passed through
process arguments.

`--update-public-health` is a separate narrow operation: it changes only the
`api-public-health` target to the repository's fixed Homelab Console health
URL, creates a timestamped backup of the remote JSON, restarts Sentinel and
checks its private health endpoint. It accepts no host, path or URL arguments.
The fixed target is `https://console.example.com/health`; callers cannot
override it through environment variables.

The deploy uses only `/root/.ssh/homelab_sentinel_deploy`. Never copy the VPS
password into a script, shell history or repository file. Rotate any password
that has been pasted into chat or logs.

On the VPS:

```bash
cp deploy/env.sentinel.example .env.sentinel
cp config/sentinel.example.json config/sentinel.local.json
```

Edit `.env.sentinel` and `config/sentinel.local.json` locally on the VPS. Then:

```bash
docker compose -f deploy/docker-compose.sentinel.yml --env-file .env.sentinel up -d --build
docker compose -f deploy/docker-compose.sentinel.yml --env-file .env.sentinel ps
docker compose -f deploy/docker-compose.sentinel.yml --env-file .env.sentinel logs -f sentinel
```

Check process liveness from the VPS:

```bash
curl -fsS http://10.255.0.1:8766/health
```

If the heartbeat endpoint is exposed through a reverse proxy, test that public
URL too. Keep direct public port exposure deliberate, not accidental.

## Step 2: Cluster Heartbeat

On the Proxmox/home-side host or container:

```bash
sudo mkdir -p /etc/homelab-console
sudo cp deploy/systemd/sentinel-heartbeat.env.example /etc/homelab-console/sentinel-heartbeat.env
```

Edit `/etc/homelab-console/sentinel-heartbeat.env` with the real Sentinel URL
and token. For the current private WireGuard deployment, use:

```env
SENTINEL_HEARTBEAT_URL=http://10.255.0.1:8766/heartbeat/home
```

Then install and start the timer:

```bash
sudo cp deploy/systemd/homelab-sentinel-heartbeat.service /etc/systemd/system/
sudo cp deploy/systemd/homelab-sentinel-heartbeat.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now homelab-sentinel-heartbeat.timer
systemctl list-timers homelab-sentinel-heartbeat.timer
```

Send one heartbeat manually:

```bash
sudo systemctl start homelab-sentinel-heartbeat.service
sudo journalctl -u homelab-sentinel-heartbeat.service -n 50 --no-pager
```

## Step 3: Failure Drills

Expected timings with the default config:

- heartbeat sender: every 60 seconds;
- heartbeat timeout: 180 seconds;
- Sentinel loop: every 30 seconds;
- expected heartbeat alert: roughly 3-4 minutes after the last good heartbeat;
- expected recovery: within one Sentinel loop after heartbeat resumes.

Run these drills:

1. Stop only the cluster heartbeat timer:

```bash
sudo systemctl stop homelab-sentinel-heartbeat.timer
```

Expected: one Telegram alert for stale/missing heartbeat, no repeated alert spam
while it stays broken.

2. Start the heartbeat again:

```bash
sudo systemctl start homelab-sentinel-heartbeat.timer
sudo systemctl start homelab-sentinel-heartbeat.service
```

Expected: one Telegram recovery notification.

3. Break the configured public health target temporarily, or point the local
Sentinel config at a known bad test URL and restart Sentinel.

Expected: one health-check alert, then one recovery after restoring the config.

4. Restart Sentinel:

```bash
docker compose -f deploy/docker-compose.sentinel.yml --env-file .env.sentinel restart sentinel
```

Expected: existing open incidents stay deduplicated because the SQLite volume is
preserved.

5. Confirm rollback:

```bash
docker compose -f deploy/docker-compose.sentinel.yml --env-file .env.sentinel down
```

Expected: only the external Sentinel stops; Homelab Console on the cluster is
not affected.

## Evidence To Record

Record these values after the first real drill:

- Sentinel deploy location and public/loopback bind choice;
- heartbeat source id;
- first alert timestamp;
- recovery timestamp;
- Telegram chat that received the alert;
- whether direct public port exposure is used or a reverse proxy terminates TLS.

## Example deployment record

Record the equivalent values for the operator's own environment. For example:

- VPS: `sentinel.example.net`;
- path: `/opt/homelab-console-sentinel`;
- container: `homelab-sentinel`;
- bind: `10.255.0.1:8766->8766/tcp`;
- env/config paths on the VPS:
  - `/opt/homelab-console-sentinel/.env.sentinel`;
  - `/opt/homelab-console-sentinel/config/sentinel.local.json`;
- state DB: `/opt/homelab-console-sentinel/data/sentinel.sqlite3`.

The bind is private-WireGuard-only by design. The heartbeat endpoint is not
publicly reachable and does not need a Sentinel subdomain.

Smoke test already performed:

1. `GET http://10.255.0.1:8766/health` from the VPS returned `{"ok": true}`.
2. First run opened a local `heartbeat missing` incident.
3. A manual local heartbeat to `/heartbeat/home` returned `{"ok": true}`.
4. The next Sentinel loop marked the incident `resolved`.
5. The container stayed running with restart policy `unless-stopped`.

Current active check:

- `api-public-health` -> `https://console.example.com/health`.
- `home` heartbeat -> `http://10.255.0.1:8766/heartbeat/home`.

Do not document the root password, Telegram bot token, Telegram chat id, or
heartbeat token here. They exist only in local/VPS secret files.
