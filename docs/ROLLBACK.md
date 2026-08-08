# Rollback

Before an upgrade, back up `config/sentinel.local.json`, `.env.sentinel` and the
SQLite volume or state file. Keep the previous image tagged locally.

For a failed Docker upgrade:

1. stop and remove only the failed container;
2. restore the previous image tag;
3. recreate the container with the same config and data volume;
4. verify `GET /health`;
5. send one authenticated heartbeat;
6. confirm existing incident and heartbeat state remains visible in SQLite.

Do not delete or replace the volume during code rollback. If a future release
requires a non-additive state migration, it must provide a separate migration and
reverse-migration procedure before release.
