# Release process

1. Confirm `main` is clean and up to date.
2. Run the full unit tests, Python compilation and shell syntax checks.
3. Build the Docker image from `deploy/Dockerfile`.
4. Run the v1 HTTP contract smoke test against a fresh SQLite volume.
5. Verify upgrade and rollback while preserving the volume.
6. Update `CHANGELOG.md` and the package version.
7. Create an annotated `vMAJOR.MINOR.PATCH` tag and GitHub release.

Release source and images must not contain `.env.sentinel`, local configuration,
SQLite state, Telegram credentials or heartbeat tokens. Breaking endpoint, auth,
dedupe or persistence semantics require contract v2.
