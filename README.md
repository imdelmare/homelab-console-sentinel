# Homelab Console Sentinel

Standalone external availability observer for Homelab Console. Sentinel runs
outside the homelab control plane so it can report loss of the console, its
network path or the home site itself.

Sentinel is deliberately not a second control plane: it performs fixed startup-
configured HTTP checks, receives authenticated heartbeats, deduplicates state in
local SQLite and sends Telegram alert/recovery notifications. It has no MCP
identity, provider credentials, remediation actions, shell or caller-selected
targets.

## Quick start

```bash
cp config/sentinel.example.json config/sentinel.local.json
cp deploy/env.example .env.sentinel
# Edit both local files; never commit them.
docker compose -f deploy/compose.yaml --env-file .env.sentinel up -d --build
```

The service binds to loopback by default. Prefer a private WireGuard/LAN address
for heartbeats; do not expose it publicly without a controlled TLS boundary.

## Interfaces

- `GET /health` — process liveness.
- `POST /heartbeat/{source_id}` — bearer- or header-authenticated heartbeat.
- fixed HTTP targets declared only in configuration.

The stable external boundary is [Sentinel contract v1](docs/CONTRACT_V1.md).

## Documentation

- [Installation](docs/INSTALLATION.md)
- [Operations and failure drills](docs/RUNBOOK.md)
- [Security policy](SECURITY.md)
- [Release process](docs/RELEASE.md)
- [Rollback](docs/ROLLBACK.md)
- [Development](docs/DEVELOPMENT.md)

The repository preserves Sentinel history extracted from Homelab Console. The
core project remains the owner of its optional heartbeat integration contract.
