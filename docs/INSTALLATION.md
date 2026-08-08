# Installation

## Docker Compose

Requirements: Docker Engine with the Compose plugin and a persistent local disk.

```bash
git clone https://github.com/imdelmare/homelab-console-sentinel.git
cd homelab-console-sentinel
cp config/sentinel.example.json config/sentinel.local.json
cp deploy/env.example .env.sentinel
```

Edit the two local files, generate a long random heartbeat token and set the
Telegram bot token/chat id. Then validate and start:

```bash
docker compose -f deploy/compose.yaml --env-file .env.sentinel config --quiet
docker compose -f deploy/compose.yaml --env-file .env.sentinel up -d --build
docker compose -f deploy/compose.yaml --env-file .env.sentinel ps
curl --fail http://127.0.0.1:8766/health
```

`config/` is mounted read-only and SQLite uses the `sentinel-data` volume. Never
run `docker compose down -v` unless state destruction is intentional.

## Python

```bash
python3.12 -m venv .venv
. .venv/bin/activate
pip install .
SENTINEL_CONFIG_PATH=config/sentinel.local.json homelab-sentinel
```

The package has no third-party runtime dependencies. Configure a process manager
to restart it and preserve the configured SQLite state path.

## Heartbeat sender

Install the same package on the source host or run from a checkout:

```bash
SENTINEL_HEARTBEAT_URL=http://sentinel.example.internal:8766/heartbeat/home \
SENTINEL_HEARTBEAT_TOKEN=replace-me \
homelab-sentinel-heartbeat
```

Systemd templates are available under `deploy/systemd/`. Review paths and copy
the environment example into `/etc/homelab-console/sentinel-heartbeat.env`.
