# mempalace-server — Production Refactor Design Spec
Date: 2026-06-19

## Goal

Refactor the monolithic `server.py` (1195 lines) into a production-ready codebase that is
DRY, follows SRP, is fully unit tested, and is testable via dependency injection without
external services.

---

## Current Problems

| Problem | Location |
|---------|----------|
| 15 route handlers + env bootstrap + 600-line HTML + entry point in one file | `server.py` |
| `chromadb.PersistentClient(path=...) + get_collection(...)` repeated in 8+ endpoints | `server.py` |
| `sqlite3.connect(KG_PATH); conn.row_factory = sqlite3.Row` repeated in 3+ endpoints | `server.py` |
| No dependency injection — storage deps hardcoded as module-level globals | `server.py` |
| Untestable without real ChromaDB on disk | `server.py` |

---

## Target Structure

```
mempalace-server/
├── src/
│   ├── config.py          # Settings — env vars via pydantic-settings
│   ├── storage.py         # PalaceStore (ChromaDB) + KGStore (SQLite) — thin data-access classes
│   ├── ui_html.py         # GRAPH_HTML string only — no logic
│   ├── app.py             # FastAPI factory: create_app(store, kg) — mounts all routers
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── kg.py          # GET /api/graph  /api/entity/{id}  /api/triple/{id}
│   │   ├── palace.py      # GET /api/palace  GET /api/palace/search  POST mutations
│   │   ├── drawers.py     # GET /api/drawers  GET /api/drawer/{id}
│   │   ├── mcp.py         # POST /mcp
│   │   └── ui.py          # GET /  GET /events
│   └── deps.py            # FastAPI Depends() factories for PalaceStore + KGStore
├── tests/
│   ├── conftest.py        # fixtures: in-memory stores, TestClient
│   ├── test_storage.py    # PalaceStore + KGStore unit tests
│   ├── test_kg.py         # KG route tests
│   ├── test_palace.py     # Palace route + mutation tests
│   ├── test_drawers.py    # Drawer route tests
│   └── test_mcp.py        # MCP endpoint tests
├── server.py              # Entry point only — reads config, calls uvicorn.run(create_app())
├── warmup.py              # Unchanged
├── requirements.txt       # Add pytest, pytest-anyio, httpx
├── Dockerfile             # Unchanged
├── docker-compose.yml     # Unchanged
└── helm/                  # Unchanged
```

---

## Component Designs

### `src/config.py`

`pydantic-settings` `Settings` class. All config in one place, validated at startup.

```python
class Settings(BaseSettings):
    palace_path: str = "/palace"
    kg_path: str | None = None       # derived from palace_path if None
    port: int = 8080

    @property
    def resolved_kg_path(self) -> str:
        return self.kg_path or f"{self.palace_path}/knowledge_graph.sqlite3"

    model_config = SettingsConfigDict(env_prefix="MEMPALACE_")
```

`PORT` read directly from `os.environ` in `server.py` (not MEMPALACE_ prefixed — existing behaviour preserved).

### `src/storage.py`

Two thin classes. No business logic — pure data access.

**`PalaceStore`** wraps ChromaDB:
```python
class PalaceStore:
    def __init__(self, path: str | None = None): ...
    # path=None → chromadb.EphemeralClient() (in-memory, for tests)
    # path=str  → chromadb.PersistentClient(path=path) (production)
    def get_collection(self): ...        # cached @property
    def search(self, q, limit) -> list[dict]: ...
    def get_tree(self) -> dict: ...
    def get_drawers(self, wing, room, limit, offset) -> list[dict]: ...
    def get_drawer_by_id(self, id) -> dict | None: ...
    def merge_wings(self, source, target) -> int: ...
    def dedupe_wing(self, wing) -> dict: ...
    def delete_wing(self, wing) -> int: ...
    def delete_room(self, wing, room) -> int: ...
    def delete_drawer(self, id) -> None: ...
```

**`KGStore`** wraps SQLite:
```python
class KGStore:
    def __init__(self, path: str): ...  # ":memory:" for tests
    def get_graph(self, show_invalidated) -> dict: ...
    def get_entity(self, id) -> dict | None: ...
    def get_entity_relations(self, id) -> dict: ...
    def get_triple(self, id) -> dict | None: ...
    def update_triple_wing(self, source, target) -> None: ...  # used by merge
```

Both classes open connections on demand (not at construction). `KGStore` uses context managers internally.

### `src/deps.py`

FastAPI dependency factories. Allow override in tests via `app.dependency_overrides`.

```python
def get_palace_store() -> PalaceStore: ...   # reads Settings(), cached per-process
def get_kg_store() -> KGStore: ...           # reads Settings(), cached per-process
def get_update_signal() -> Callable: ...     # returns signal_update()
```

### `src/routes/`

Each router owns one domain. All storage deps injected via `Depends()`.

| Router | Endpoints | Deps |
|--------|-----------|------|
| `kg.py` | `GET /api/graph`, `/api/entity/{id}`, `/api/triple/{id}` | `KGStore`, `PalaceStore` (triple detail needs chroma) |
| `palace.py` | `GET /api/palace`, `GET /api/palace/search`, `POST /api/palace/merge`, `POST /api/palace/dedupe`, `POST /api/palace/delete-wing`, `POST /api/palace/delete-room` | `PalaceStore`, `KGStore` (merge updates KG), signal |
| `drawers.py` | `GET /api/drawers`, `GET /api/drawer/{id}`, `POST /api/palace/delete-drawer` | `PalaceStore`, signal |
| `mcp.py` | `POST /mcp` | `handle_request` (imported once at module level), signal |
| `ui.py` | `GET /`, `GET /events` | none |

### `src/app.py`

Factory function — not a module-level `app` global. Enables clean test instantiation.

```python
def create_app(
    palace_store: PalaceStore | None = None,
    kg_store: KGStore | None = None,
) -> FastAPI:
    app = FastAPI(title="MemPalace MCP", version="3.4.1")
    if palace_store:
        app.dependency_overrides[get_palace_store] = lambda: palace_store
    if kg_store:
        app.dependency_overrides[get_kg_store] = lambda: kg_store
    app.include_router(kg_router)
    app.include_router(palace_router)
    app.include_router(drawers_router)
    app.include_router(mcp_router)
    app.include_router(ui_router)
    return app
```

### `server.py` (entry point only)

```python
from src.app import create_app
import uvicorn, os

if __name__ == "__main__":
    app = create_app()
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
```

---

## Testing

### Test backends

- `PalaceStore`: `chromadb.EphemeralClient()` — in-memory, no disk, auto-reset per test
- `KGStore`: `sqlite3.connect(":memory:")` — in-memory SQLite

### `tests/conftest.py`

```python
@pytest.fixture
def palace_store():
    return PalaceStore(path=None)   # signals EphemeralClient

@pytest.fixture
def kg_store():
    return KGStore(path=":memory:")

@pytest.fixture
def client(palace_store, kg_store):
    app = create_app(palace_store=palace_store, kg_store=kg_store)
    return TestClient(app)
```

### Coverage targets

| Module | What's tested |
|--------|--------------|
| `test_kg.py` | Empty graph returns `{nodes:[], edges:[]}`. Entity not found → 404. Triple not found → 404. Graph with seeded KG data returns correct nodes/edges. |
| `test_palace.py` | Palace tree returns correct wings/rooms. Semantic search returns results. Merge moves drawers. Dedupe removes exact-duplicate drawers. Delete wing removes all drawers. Delete room removes room drawers only. |
| `test_drawers.py` | `GET /api/drawers` returns all. Wing filter works. Room filter works. `GET /api/drawer/{id}` returns content. Unknown ID → 404. `POST /api/palace/delete-drawer` removes it. |
| `test_mcp.py` | Valid JSON-RPC body → 200. Malformed JSON → 400 parse error. `notifications/initialized` → 204. |
| `test_storage.py` | `PalaceStore` unit tests: add/search/delete. `KGStore` unit tests: schema init, entity insert, triple query. |

### Test dependencies added to `requirements.txt`

```
pydantic-settings>=2.0   # for src/config.py
pytest>=8.0
httpx>=0.27              # required by FastAPI TestClient
```

---

## Error Handling

Routes return `JSONResponse({"error": ...}, status_code=...)` for known errors (not found,
bad input). Unhandled exceptions bubble to FastAPI's default 500 handler. No change from
current behaviour — but now centralisable via FastAPI exception handlers in `app.py` if
needed later.

---

## What Does NOT Change

- `server.py` startup behaviour (env vars, port, palace path)
- All API endpoint paths and response shapes
- The HTML/JS web UI (moved to `ui_html.py`, served identically)
- `warmup.py`, `Dockerfile`, `docker-compose.yml`, `helm/`
- The mempalace KG path patch (`_kg_module.DEFAULT_KG_PATH = KG_PATH`) — moved to `server.py`
