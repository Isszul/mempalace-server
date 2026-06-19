from unittest.mock import patch


def test_mcp_malformed_json(client):
    resp = client.post(
        "/mcp",
        content=b"not json",
        headers={"content-type": "application/json"},
    )
    assert resp.status_code == 400
    err = resp.json()
    assert err["error"]["code"] == -32700
    assert err["error"]["message"] == "Parse error"


def test_mcp_valid_request_returns_200(client):
    mock_response = {"jsonrpc": "2.0", "id": 1, "result": {"capabilities": {}}}
    with patch("src.routes.mcp.handle_request", return_value=mock_response):
        resp = client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        )
    assert resp.status_code == 200
    assert resp.json()["result"]["capabilities"] == {}


def test_mcp_notification_returns_204(client):
    with patch("src.routes.mcp.handle_request", return_value=None):
        resp = client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "method": "notifications/initialized"},
        )
    assert resp.status_code == 204


def test_mcp_mutation_calls_signal(client):
    mock_response = {"jsonrpc": "2.0", "id": 2, "result": {}}
    with patch("src.routes.mcp.handle_request", return_value=mock_response), \
         patch("src.routes.mcp.signal_update") as mock_signal:
        client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "id": 2, "method": "mempalace_add_drawer", "params": {}},
        )
    mock_signal.assert_called_once()
