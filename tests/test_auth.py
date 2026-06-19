import base64
from unittest.mock import patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from src.auth import verify_auth
from src.config import Settings


class _Request:
    def __init__(self, path, headers=None, method="POST"):
        self.url = type("URL", (), {"path": path})()
        self.headers = headers or {}
        self.method = method


def _req(path, auth_header=None, method="POST"):
    headers = {}
    if auth_header:
        headers["authorization"] = auth_header
    return _Request(path, headers, method)


def test_no_auth_configured_passes():
    with patch("src.auth.Settings") as mock:
        mock.return_value.auth_token = None
        mock.return_value.auth_password = None
        assert verify_auth(_req("/mcp")) is None
        assert verify_auth(_req("/api/graph")) is None


def test_health_check_bypasses_auth():
    with patch("src.auth.Settings") as mock:
        mock.return_value.auth_token = "secret"
        mock.return_value.auth_password = "pass"
        assert verify_auth(_req("/health")) is None
        assert verify_auth(_req("/health", "Bearer wrong")) is None


def test_missing_header_raises():
    with patch("src.auth.Settings") as mock:
        mock.return_value.auth_token = "secret"
        mock.return_value.auth_password = None
        with pytest.raises(HTTPException) as exc:
            verify_auth(_req("/mcp"))
        assert exc.value.status_code == 401


def test_bearer_token_valid():
    with patch("src.auth.Settings") as mock:
        mock.return_value.auth_token = "secret"
        mock.return_value.auth_password = None
        assert verify_auth(_req("/mcp", "Bearer secret")) is None


def test_bearer_token_wrong():
    with patch("src.auth.Settings") as mock:
        mock.return_value.auth_token = "secret"
        mock.return_value.auth_password = None
        with pytest.raises(HTTPException):
            verify_auth(_req("/mcp", "Bearer wrong"))


def test_basic_auth_valid_password():
    with patch("src.auth.Settings") as mock:
        mock.return_value.auth_token = None
        mock.return_value.auth_password = "pass"
        mock.return_value.auth_username = "admin"
        encoded = base64.b64encode(b"admin:pass").decode()
        assert verify_auth(_req("/mcp", f"Basic {encoded}")) is None


def test_basic_auth_wrong_password():
    with patch("src.auth.Settings") as mock:
        mock.return_value.auth_token = None
        mock.return_value.auth_password = "pass"
        mock.return_value.auth_username = "admin"
        encoded = base64.b64encode(b"admin:wrong").decode()
        with pytest.raises(HTTPException):
            verify_auth(_req("/mcp", f"Basic {encoded}"))


def test_basic_auth_uses_token_as_password_fallback():
    with patch("src.auth.Settings") as mock:
        mock.return_value.auth_token = "token-val"
        mock.return_value.auth_password = None
        mock.return_value.auth_username = "admin"
        encoded = base64.b64encode(b"user:token-val").decode()
        assert verify_auth(_req("/mcp", f"Basic {encoded}")) is None


def test_root_get_bypasses_auth():
    with patch("src.auth.Settings") as mock:
        mock.return_value.auth_token = "secret"
        mock.return_value.auth_password = None
        assert verify_auth(_req("", method="GET")) is None


def test_root_post_requires_auth():
    with patch("src.auth.Settings") as mock:
        mock.return_value.auth_token = "secret"
        mock.return_value.auth_password = None
        with pytest.raises(HTTPException):
            verify_auth(_req("", method="POST"))


def test_events_bypasses_auth():
    with patch("src.auth.Settings") as mock:
        mock.return_value.auth_token = "secret"
        mock.return_value.auth_password = None
        assert verify_auth(_req("/events", "Bearer wrong")) is None


def test_all_routes_protected_end_to_end():
    settings = Settings()
    assert settings.auth_token is None  # no env var in test
    client = TestClient(create_test_app())
    resp = client.get("/api/graph")
    assert resp.status_code == 200  # auth disabled

    with patch("src.auth.Settings") as mock:
        mock.return_value.auth_token = "secret"
        mock.return_value.auth_password = None
        mock.return_value.auth_username = "admin"
        client2 = TestClient(create_test_app())
        resp = client2.get("/api/graph")
        assert resp.status_code == 401  # no auth header

        resp = client2.get("/api/graph", headers={"Authorization": "Bearer secret"})
        assert resp.status_code == 200

        resp = client2.get("/")
        assert resp.status_code == 200  # web UI bypasses auth

        resp = client2.get("/health")
        assert resp.status_code == 200  # health bypasses auth


def create_test_app():
    from src.app import create_app
    from src.storage import KGStore, PalaceStore
    import tempfile
    tmp = tempfile.mkdtemp()
    kg = KGStore(":memory:")
    kg._mem_conn.executescript(KG_SCHEMA)
    return create_app(
        palace_store=PalaceStore(path=tmp),
        kg_store=kg,
    )


KG_SCHEMA = """
CREATE TABLE IF NOT EXISTS entities (
    id TEXT PRIMARY KEY,
    name TEXT,
    type TEXT DEFAULT 'unknown',
    properties TEXT DEFAULT '{}',
    created_at TEXT DEFAULT '2024-01-01'
);
CREATE TABLE IF NOT EXISTS triples (
    id TEXT PRIMARY KEY,
    subject TEXT,
    predicate TEXT,
    object TEXT,
    confidence REAL DEFAULT 1.0,
    valid_from TEXT,
    valid_to TEXT,
    source_closet TEXT,
    source_file TEXT
);
"""
