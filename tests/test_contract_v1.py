from __future__ import annotations

import json
import urllib.error
import urllib.request

from sentinel.heartbeat import HeartbeatServer
from sentinel.store import SentinelStore


def _request(url: str, *, data: bytes | None = None, token: str = "contract-token"):
    request = urllib.request.Request(url, data=data)
    if data is not None:
        request.add_header("Authorization", f"Bearer {token}")
        request.add_header("Content-Type", "application/json")
    return urllib.request.urlopen(request, timeout=2)


def test_health_and_unknown_path_contract(tmp_path):
    server = HeartbeatServer("127.0.0.1", 0, "contract-token", SentinelStore(str(tmp_path / "state.sqlite3")))
    server.start()
    try:
        assert server._server is not None
        base = f"http://127.0.0.1:{server._server.server_port}"
        with _request(f"{base}/health") as response:
            assert response.status == 200
            assert json.load(response) == {"ok": True}
        try:
            _request(f"{base}/unknown")
        except urllib.error.HTTPError as exc:
            assert exc.code == 404
        else:
            raise AssertionError("unknown path was accepted")
    finally:
        server.stop()


def test_malformed_body_is_empty_evidence_and_missing_source_is_rejected(tmp_path):
    store = SentinelStore(str(tmp_path / "state.sqlite3"))
    server = HeartbeatServer("127.0.0.1", 0, "contract-token", store)
    server.start()
    try:
        assert server._server is not None
        base = f"http://127.0.0.1:{server._server.server_port}"
        with _request(f"{base}/heartbeat/home", data=b"not-json") as response:
            assert response.status == 200
            assert json.load(response) == {"ok": True}
        assert store.last_heartbeat_at("home") is not None
        try:
            _request(f"{base}/heartbeat/", data=b"{}")
        except urllib.error.HTTPError as exc:
            assert exc.code == 400
            assert json.load(exc) == {"ok": False, "error": "missing_source_id"}
        else:
            raise AssertionError("empty source id was accepted")
    finally:
        server.stop()
