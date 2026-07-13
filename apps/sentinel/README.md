# Homelab Sentinel

Standalone external sentinel for Milestone 1. It is intentionally separate from
`apps/api`: if Homelab Console, WireGuard, or the home network fails, this
process can still emit Telegram alerts from the VPS.

Run locally:

```bash
python -m venv .venv
source .venv/bin/activate
python -m sentinel
```

Set `SENTINEL_CONFIG_PATH=config/sentinel.local.json` and keep that file out of
git. See `config/sentinel.example.json` for the schema.

Send one heartbeat from the cluster side:

```bash
PYTHONPATH=apps/sentinel \
SENTINEL_HEARTBEAT_URL=https://sentinel.example.com/heartbeat/home \
SENTINEL_HEARTBEAT_TOKEN=... \
python -m sentinel.heartbeat_client
```
