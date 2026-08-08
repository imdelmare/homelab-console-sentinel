# Operations and failure drills

## Routine checks

```bash
docker compose -f deploy/compose.yaml --env-file .env.sentinel ps
docker compose -f deploy/compose.yaml --env-file .env.sentinel logs --since 15m sentinel
curl --fail http://127.0.0.1:8766/health
```

Confirm the configured SQLite state path is on persistent storage and include it
in backups. Verify that the configured HTTP targets are fixed operator-owned
values and that the listener is not unintentionally public.

## Heartbeat drill

1. Send one authenticated heartbeat and record its timestamp.
2. Stop the heartbeat sender for longer than the configured timeout.
3. Confirm exactly one grouped alert after the configured failure threshold.
4. Restore the sender.
5. Confirm recovery only after the configured healthy streak.
6. Verify the same incident row was resolved rather than duplicated.

## HTTP target drill

Use a non-critical declared test target or a controlled maintenance window.
Make the fixed target fail for the configured number of confirmations, verify one
alert, restore it and verify one recovery. Runtime requests must never be able to
change the target URL.

## Notification failure drill

Temporarily use a test notifier or deny outbound Telegram in an isolated
environment. Monitoring and SQLite state updates must continue while delivery
fails. Restore delivery and verify normal future alerts. Never use a real token
in test output.

## VPS deployment helper

`scripts/deploy-sentinel-vps.sh` is an optional fixed-shape operator helper. It
requires these exported non-secret deployment coordinates plus the dedicated SSH
target/key and local `.env.sentinel` credentials file:

```bash
export HOMELAB_SENTINEL_VPS_TARGET=sentinel-deploy@vps.example.net
export SENTINEL_PUBLIC_HEALTH_URL=https://console.example.com/health
export SENTINEL_PRIVATE_HEALTH_URL=http://console.example.internal/health
export SENTINEL_BIND_ADDRESS=192.0.2.10
```

Bootstrap the dedicated key once, check the existing remote installation, then
deploy:

```bash
scripts/bootstrap-sentinel-vps-key.sh
scripts/deploy-sentinel-vps.sh --check
scripts/deploy-sentinel-vps.sh
```

The helper tags the previous image as `homelab-sentinel:rollback`, serializes
operations with a lock and restores that image when the new healthcheck fails.
Review the fixed remote path and script before use; it is not a generic SSH or
deployment framework.

## After any drill

Record timestamps, expected and observed notifications, incident state and the
recovery result. Restore all temporary target, firewall and credential changes.
Follow [ROLLBACK.md](ROLLBACK.md) if the new release is not healthy.
