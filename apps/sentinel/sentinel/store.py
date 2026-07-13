from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def iso(value: datetime | None = None) -> str:
    return (value or utcnow()).isoformat()


def parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value)


@dataclass(frozen=True)
class Observation:
    dedupe_key: str
    source_id: str
    kind: str
    ok: bool
    title: str
    description: str


@dataclass(frozen=True)
class IncidentChange:
    action: str
    observation: Observation
    occurrences: int


class SentinelStore:
    def __init__(self, path: str) -> None:
        self.path = path
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                create table if not exists incidents (
                    dedupe_key text primary key,
                    source_id text not null,
                    kind text not null,
                    title text not null,
                    status text not null,
                    occurrences integer not null,
                    first_seen_at text not null,
                    last_seen_at text not null,
                    resolved_at text,
                    last_error text not null,
                    recovery_notified integer not null default 0
                );
                create index if not exists ix_sentinel_incidents_status
                    on incidents(status);
                create table if not exists heartbeats (
                    source_id text primary key,
                    last_seen_at text not null,
                    remote_addr text not null,
                    payload_json text not null
                );
                """
            )

    def record_failure(self, observation: Observation) -> IncidentChange:
        now = iso()
        with self._connect() as conn:
            row = conn.execute(
                "select status, occurrences from incidents where dedupe_key = ?",
                (observation.dedupe_key,),
            ).fetchone()
            if row and row["status"] == "open":
                occurrences = int(row["occurrences"]) + 1
                conn.execute(
                    """
                    update incidents
                    set occurrences = ?, last_seen_at = ?, last_error = ?
                    where dedupe_key = ?
                    """,
                    (occurrences, now, observation.description, observation.dedupe_key),
                )
                return IncidentChange("repeated_open", observation, occurrences)

            # A resolved incident reopening starts a fresh occurrence count rather
            # than resuming the historical one from before it recovered.
            occurrences = 1
            conn.execute(
                """
                insert into incidents (
                    dedupe_key, source_id, kind, title, status, occurrences,
                    first_seen_at, last_seen_at, resolved_at, last_error, recovery_notified
                )
                values (?, ?, ?, ?, 'open', ?, ?, ?, null, ?, 0)
                on conflict(dedupe_key) do update set
                    status = 'open',
                    occurrences = excluded.occurrences,
                    last_seen_at = excluded.last_seen_at,
                    resolved_at = null,
                    last_error = excluded.last_error,
                    recovery_notified = 0
                """,
                (
                    observation.dedupe_key,
                    observation.source_id,
                    observation.kind,
                    observation.title,
                    occurrences,
                    now,
                    now,
                    observation.description,
                ),
            )
            return IncidentChange("opened", observation, occurrences)

    def record_recovery(self, observation: Observation) -> IncidentChange | None:
        now = iso()
        with self._connect() as conn:
            row = conn.execute(
                """
                select occurrences from incidents
                where dedupe_key = ? and status = 'open'
                """,
                (observation.dedupe_key,),
            ).fetchone()
            if row is None:
                return None
            conn.execute(
                """
                update incidents
                set status = 'resolved', resolved_at = ?, last_seen_at = ?,
                    last_error = '', recovery_notified = 1
                where dedupe_key = ?
                """,
                (now, now, observation.dedupe_key),
            )
            return IncidentChange("resolved", observation, int(row["occurrences"]))

    def record_heartbeat(self, source_id: str, remote_addr: str, payload: dict[str, Any]) -> None:
        payload_json = json.dumps(payload, sort_keys=True)[:4096]
        with self._connect() as conn:
            conn.execute(
                """
                insert into heartbeats(source_id, last_seen_at, remote_addr, payload_json)
                values (?, ?, ?, ?)
                on conflict(source_id) do update set
                    last_seen_at = excluded.last_seen_at,
                    remote_addr = excluded.remote_addr,
                    payload_json = excluded.payload_json
                """,
                (source_id, iso(), remote_addr, payload_json),
            )

    def last_heartbeat_at(self, source_id: str) -> datetime | None:
        with self._connect() as conn:
            row = conn.execute(
                "select last_seen_at from heartbeats where source_id = ?",
                (source_id,),
            ).fetchone()
        return parse_iso(row["last_seen_at"]) if row else None

    def list_open_incidents(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                select dedupe_key, source_id, kind, title, occurrences,
                    first_seen_at, last_seen_at, last_error
                from incidents
                where status = 'open'
                order by last_seen_at desc
                """
            ).fetchall()
        return [dict(row) for row in rows]
