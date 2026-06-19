from unittest.mock import patch

import pytest
from fastapi import HTTPException

from src.auth import verify_mcp_token


def test_no_token_configured_passes():
    with patch("src.auth.Settings") as mock:
        mock.return_value.auth_token = None
        assert verify_mcp_token(authorization=None) is None


def test_no_token_configured_with_header_ignored():
    with patch("src.auth.Settings") as mock:
        mock.return_value.auth_token = None
        assert verify_mcp_token(authorization="Bearer some-token") is None


def test_missing_header_raises():
    with patch("src.auth.Settings") as mock:
        mock.return_value.auth_token = "secret"
        with pytest.raises(HTTPException) as exc:
            verify_mcp_token(authorization=None)
        assert exc.value.status_code == 401


def test_basic_auth_accepted():
    with patch("src.auth.Settings") as mock:
        mock.return_value.auth_token = "secret"
        assert verify_mcp_token(authorization="Basic dXNlcjpwYXNz") is None


def test_wrong_bearer_token_raises():
    with patch("src.auth.Settings") as mock:
        mock.return_value.auth_token = "secret"
        with pytest.raises(HTTPException):
            verify_mcp_token(authorization="Bearer wrong")


def test_valid_bearer_token_passes():
    with patch("src.auth.Settings") as mock:
        mock.return_value.auth_token = "secret"
        assert verify_mcp_token(authorization="Bearer secret") is None
