# mempalace-server

HTTP server and web UI for [MemPalace](https://github.com/MemPalace/mempalace) — exposes all MCP tools over Streamable HTTP and provides a browser-based knowledge graph explorer.

## What this is

- **`POST /mcp`** — Streamable HTTP MCP endpoint (connect via supergateway or any MCP client)
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
| `PORT` | `8080` | HTTP port |

## Connecting an MCP client

With [supergateway](https://github.com/supermaven-inc/supergateway):

```bash
supergateway --streamableHttp http://localhost:8080/mcp
```

Or configure directly in your MCP client pointing to `http://<host>:8080/mcp`.
