#!/usr/bin/env python3
"""Update the two allowed Telegram values in an existing VPS .env.sentinel.

The JSON payload is read from stdin so credentials never appear in argv. No
other environment key can be changed through this helper.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path


ALLOWED_KEYS = ("TELEGRAM_BOT_TOKEN", "TELEGRAM_ALLOWED_CHAT_ID")


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: update-sentinel-secrets.py /absolute/path/.env.sentinel")
    target = Path(sys.argv[1])
    if not target.is_absolute() or target.name != ".env.sentinel" or not target.is_file():
        raise SystemExit("refusing to update an unknown or missing env file")

    payload = json.load(sys.stdin)
    if set(payload) != set(ALLOWED_KEYS):
        raise SystemExit("payload must contain exactly the allowed Telegram keys")
    if not all(isinstance(payload[key], str) and payload[key].strip() for key in ALLOWED_KEYS):
        raise SystemExit("Telegram values must be non-empty strings")

    original = target.read_text(encoding="utf-8").splitlines()
    found: set[str] = set()
    updated: list[str] = []
    for line in original:
        key = line.split("=", 1)[0].strip() if "=" in line else ""
        if key in ALLOWED_KEYS:
            if key not in found:
                updated.append(f"{key}={payload[key]}")
                found.add(key)
            continue
        updated.append(line)
    for key in ALLOWED_KEYS:
        if key not in found:
            updated.append(f"{key}={payload[key]}")

    mode = target.stat().st_mode & 0o777
    fd, temporary = tempfile.mkstemp(prefix=".env.sentinel.", dir=target.parent, text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write("\n".join(updated) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, mode)
        os.replace(temporary, target)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


if __name__ == "__main__":
    main()
