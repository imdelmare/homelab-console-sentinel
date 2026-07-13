# External Sentinel Runbook

This is the third deployment step: prove the Sentinel actually alerts and
recovers before relying on it.

No real VPS hostnames, Telegram tokens or heartbeat tokens belong in this repo.
Use `deploy/env.sentinel.example`, `config/sentinel.example.json` and
`deploy/systemd/sentinel-heartbeat.env.example` only as templates.

## Step 1: VPS Only

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
curl -fsS http://127.0.0.1:8766/health
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
and token. Then install and start the timer:

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

## Current Lab Deployment

As of the first VPS-only smoke test, the Homelab Sentinel deployment is:

- VPS: `49.13.159.26` (`ubuntu-4gb-nbg1-2`);
- path: `/opt/homelab-console-sentinel`;
- container: `homelab-sentinel`;
- bind: `127.0.0.1:8766->8766/tcp`;
- real env/config paths on the VPS:
  - `/opt/homelab-console-sentinel/.env.sentinel`;
  - `/opt/homelab-console-sentinel/config/sentinel.local.json`;
- state DB: `/opt/homelab-console-sentinel/data/sentinel.sqlite3`.

The bind is loopback-only by design. The heartbeat endpoint is not publicly
reachable yet; expose it later through a controlled HTTPS reverse proxy before
enabling the Proxmox-side heartbeat timer.

Smoke test already performed:

1. `GET http://127.0.0.1:8766/health` from the VPS returned `{"ok": true}`.
2. First run opened a local `heartbeat missing` incident.
3. A manual local heartbeat to `/heartbeat/home` returned `{"ok": true}`.
4. The next Sentinel loop marked the incident `resolved`.
5. The container stayed running with restart policy `unless-stopped`.

Do not document the root password, Telegram bot token, Telegram chat id, or
heartbeat token here. They exist only in local/VPS secret files.
