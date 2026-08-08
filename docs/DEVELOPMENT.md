# Development

Sentinel intentionally uses only the Python standard library at runtime. Keep
the service narrow: fixed startup configuration, one heartbeat receiver, local
SQLite state and Telegram notification delivery. Do not add arbitrary runtime
URLs, commands, remediation or Homelab Console credentials.

## Local validation

```bash
python -m pip install -e ".[dev]"
python -m pytest -q
python -m compileall -q sentinel scripts/update-sentinel-secrets.py
bash -n scripts/*.sh
docker build -f deploy/Dockerfile -t homelab-console-sentinel:test .
```

For an isolated runtime test:

```bash
cp config/sentinel.example.json config/sentinel.local.json
SENTINEL_CONFIG_PATH=config/sentinel.local.json \
SENTINEL_HEARTBEAT_TOKEN=replace-me \
python -m sentinel
```

Send a heartbeat from another terminal:

```bash
SENTINEL_HEARTBEAT_URL=http://127.0.0.1:8766/heartbeat/home \
SENTINEL_HEARTBEAT_TOKEN=replace-me \
python -m sentinel.heartbeat_client
```

Contract changes require conformance tests and a new major contract version when
they break v1 clients, persisted state or deployment assumptions.
