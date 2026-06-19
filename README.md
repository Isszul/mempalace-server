# mempalace-server

HTTP server and web UI for [MemPalace](https://github.com/MemPalace/mempalace) — exposes all MCP tools over Streamable HTTP and provides a browser-based knowledge graph explorer.

## What this is

- **`POST /mcp`** — Streamable HTTP MCP endpoint (connect via any MCP client)
- **`GET /`** — interactive web UI: vis-network KG graph, palace tree browser, semantic search
- **`GET /health`** — Kubernetes liveness/readiness probe

The `mempalace` Python library is a PyPI dependency — no API key required.

## Quick start

### Plain Python

```bash
pip install -r requirements.txt
MEMPALACE_PALACE_PATH=./palace python server.py
# open http://localhost:8080
```

### Docker

```bash
docker build -t mempalace-server .
docker run -p 8080:8080 -v $(pwd)/palace:/palace mempalace-server
```

### Docker Compose

```bash
docker compose up --build
# open http://localhost:8080
```

### Helm (Kubernetes)

```bash
docker build -t mempalace-server:latest .
# import image into your cluster, e.g. for K3s:
#   sudo k3s ctr images import <(docker save mempalace-server:latest)

helm install mempalace ./helm \
  --set ingress.className=nginx \
  --set ingress.hosts[0].host=mempalace.example.com \
  --set image.pullPolicy=Never
```

## Configuration

| Env var | Default | Description |
|---------|---------|-------------|
| `MEMPALACE_PALACE_PATH` | `/palace` | Path to ChromaDB storage directory |
| `MEMPALACE_KG_PATH` | `$PALACE_PATH/knowledge_graph.sqlite3` | Path to SQLite knowledge graph |
| `MEMPALACE_AUTH_TOKEN` | _(none)_ | Bearer token for API/MCP auth |
| `MEMPALACE_AUTH_USERNAME` | `admin` | Basic auth username |
| `MEMPALACE_AUTH_PASSWORD` | _(none)_ | Basic auth password |
| `PORT` | `8080` | HTTP port |

### Authentication

When `MEMPALACE_AUTH_TOKEN` or `MEMPALACE_AUTH_PASSWORD` is set, all routes except
`GET /health` require authentication. Two mechanisms are supported:

- **Bearer token**: send `Authorization: Bearer <token>`
- **Basic auth**: send `Authorization: Basic <base64>` using `MEMPALACE_AUTH_USERNAME` / `MEMPALACE_AUTH_PASSWORD`. Falls back to using `MEMPALACE_AUTH_TOKEN` as the password if no password is configured.

Both work on every route (`/mcp`, `/api/*`, web UI).

## Connecting an MCP client

Configure your MCP client to point at `http://<host>:8080/mcp`.

### Example: OpenCode

```json
{
  "mcp": {
    "mempalace": {
      "type": "remote",
      "url": "http://mempalace.home/mcp",
      "headers": {
        "Authorization": "Bearer <token>"
      }
    }
  }
}
```

### Example: curl

```bash
# Bearer token
curl -H "Authorization: Bearer <token>" http://localhost:8080/mcp

# Basic auth
curl -u admin:<password> http://localhost:8080/api/graph

# Health check (no auth required)
curl http://localhost:8080/health
```
