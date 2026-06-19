"""
MemPalace MCP Server
====================
Exposes all mempalace MCP tools over Streamable HTTP (POST /mcp).

Env vars:
  MEMPALACE_PALACE_PATH   - where ChromaDB lives  (default: /palace)
  MEMPALACE_KG_PATH       - SQLite knowledge graph (default: /palace/knowledge_graph.sqlite3)
  PORT                    - HTTP port              (default: 8080)
"""

import os

# ── path bootstrap (must happen before any mempalace import) ────────────────
PALACE_PATH = os.environ.get("MEMPALACE_PALACE_PATH", "/palace")
os.environ["MEMPALACE_PALACE_PATH"] = PALACE_PATH

KG_PATH = os.environ.get(
    "MEMPALACE_KG_PATH",
    os.path.join(PALACE_PATH, "knowledge_graph.sqlite3"),
)

import mempalace.knowledge_graph as _kg_module  # noqa: E402
_kg_module.DEFAULT_KG_PATH = KG_PATH

# ── now safe to import the app (which pulls in mempalace.mcp_server) ─────────
from src.app import create_app  # noqa: E402

app = create_app()

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
