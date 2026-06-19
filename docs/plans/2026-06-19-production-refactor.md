# mempalace-server Production Refactor — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor monolithic `server.py` (1195 lines) into DRY, SRP modules with full unit test coverage, without changing any API endpoint paths or response shapes.

**Architecture:** FastAPI `create_app()` factory with `Depends()` injection. `PalaceStore` (ChromaDB) and `KGStore` (SQLite) extracted to `src/storage.py`. Route handlers split into four focused `APIRouter` modules. Tests use `chromadb.EphemeralClient()` and SQLite `":memory:"` via `app.dependency_overrides`.

**Tech Stack:** Python 3.12, FastAPI, ChromaDB, SQLite, pydantic-settings≥2, pytest≥8, httpx≥0.27

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `src/__init__.py` | Create | package marker |
| `src/config.py` | Create | `Settings` — all env vars via pydantic-settings |
| `src/storage.py` | Create | `PalaceStore` (ChromaDB) + `KGStore` (SQLite) |
| `src/events.py` | Create | `_update_event` asyncio.Event + `signal_update()` |
| `src/ui_html.py` | Create | `GRAPH_HTML` constant only |
| `src/deps.py` | Create | `get_palace_store()` + `get_kg_store()` FastAPI deps |
| `src/app.py` | Create | `create_app()` factory, mounts routers |
| `src/routes/__init__.py` | Create | package marker |
| `src/routes/ui.py` | Create | `GET /`, `GET /health`, `GET /events` |
| `src/routes/kg.py` | Create | `GET /api/graph`, `/api/entity/{id}`, `/api/triple/{id}` |
| `src/routes/palace.py` | Create | `GET /api/palace`, `GET /api/palace/search`, `POST` mutations |
| `src/routes/drawers.py` | Create | `GET /api/drawers`, `GET /api/drawer/{id}`, `POST /api/palace/delete-drawer` |
| `src/routes/mcp.py` | Create | `POST /mcp` |
| `tests/__init__.py` | Create | package marker |
| `tests/conftest.py` | Create | shared fixtures: `palace_store`, `kg_store`, `client` |
| `tests/test_storage.py` | Create | unit tests for PalaceStore + KGStore |
| `tests/test_kg.py` | Create | route tests for KG endpoints |
| `tests/test_palace.py` | Create | route tests for palace endpoints |
| `tests/test_drawers.py` | Create | route tests for drawer endpoints |
| `tests/test_mcp.py` | Create | route tests for MCP endpoint |
| `requirements.txt` | Modify | add pydantic-settings, pytest, httpx |
| `server.py` | Modify | entry point only — 10 lines |

---

## Task 1: Scaffold — directories and requirements

**Files:**
- Create: `src/__init__.py`, `src/routes/__init__.py`, `tests/__init__.py`
- Modify: `requirements.txt`

- [ ] **Step 1: Create package markers**

```bash
touch src/__init__.py src/routes/__init__.py tests/__init__.py
```

- [ ] **Step 2: Update requirements.txt**

Replace the content of `requirements.txt` with:

```
mempalace==3.4.1
fastapi>=0.110.0
uvicorn[standard]>=0.29.0
pydantic-settings>=2.0
pytest>=8.0
httpx>=0.27
```

- [ ] **Step 3: Install new deps**

```bash
pip install pydantic-settings pytest httpx
```

Expected: all install without errors.

- [ ] **Step 4: Commit**

```bash
git add src/__init__.py src/routes/__init__.py tests/__init__.py requirements.txt
git commit -m "chore: scaffold src/ and tests/ packages, add dev deps"
```

---

## Task 2: `src/config.py`

**Files:**
- Create: `src/config.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_config.py`:

```python
import pytest
from src.config import Settings


def test_defaults():
    s = Settings()
    assert s.palace_path == "/palace"
    assert s.kg_path is None
    assert s.resolved_kg_path == "/palace/knowledge_graph.sqlite3"


def test_custom_palace_path(monkeypatch):
    monkeypatch.setenv("MEMPALACE_PALACE_PATH", "/data")
    s = Settings()
    assert s.palace_path == "/data"
    assert s.resolved_kg_path == "/data/knowledge_graph.sqlite3"


def test_explicit_kg_path_overrides_derived(monkeypatch):
    monkeypatch.setenv("MEMPALACE_PALACE_PATH", "/data")
    monkeypatch.setenv("MEMPALACE_KG_PATH", "/custom/kg.sqlite3")
    s = Settings()
    assert s.resolved_kg_path == "/custom/kg.sqlite3"
```

- [ ] **Step 2: Run tests — expect ImportError**

```bash
pytest tests/test_config.py -v
```

Expected: `ImportError: No module named 'src.config'`

- [ ] **Step 3: Implement `src/config.py`**

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    palace_path: str = "/palace"
    kg_path: str | None = None

    model_config = SettingsConfigDict(env_prefix="MEMPALACE_")

    @property
    def resolved_kg_path(self) -> str:
        return self.kg_path or f"{self.palace_path}/knowledge_graph.sqlite3"
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
pytest tests/test_config.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add src/config.py tests/test_config.py
git commit -m "feat(config): add Settings via pydantic-settings"
```

---

## Task 3: `src/storage.py` — KGStore

**Files:**
- Create: `src/storage.py` (KGStore only for now)
- Create: `tests/test_storage.py` (KGStore tests)

- [ ] **Step 1: Write KGStore tests**

Create `tests/test_storage.py`:

```python
import sqlite3
import pytest
from src.storage import KGStore

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


@pytest.fixture
def kg():
    store = KGStore(":memory:")
    store._mem_conn.executescript(KG_SCHEMA)
    return store


def _seed_kg(kg: KGStore):
    kg._mem_conn.execute(
        "INSERT INTO entities VALUES (?,?,?,?,?)",
        ("e1", "Alice", "person", "{}", "2024-01-01"),
    )
    kg._mem_conn.execute(
        "INSERT INTO entities VALUES (?,?,?,?,?)",
        ("e2", "Bob", "person", "{}", "2024-01-01"),
    )
    kg._mem_conn.execute(
        "INSERT INTO triples VALUES (?,?,?,?,?,?,?,?,?)",
        ("t1", "e1", "knows", "e2", 1.0, None, None, "wing1/room1", None),
    )
    kg._mem_conn.commit()


def test_get_graph_empty(kg):
    result = kg.get_graph()
    assert result == {"nodes": [], "edges": []}


def test_get_graph_returns_nodes_and_edges(kg):
    _seed_kg(kg)
    result = kg.get_graph()
    assert len(result["nodes"]) == 2
    assert len(result["edges"]) == 1
    node_ids = {n["id"] for n in result["nodes"]}
    assert node_ids == {"e1", "e2"}
    edge = result["edges"][0]
    assert edge["subject"] == "e1"
    assert edge["predicate"] == "knows"
    assert edge["object"] == "e2"


def test_get_entity_returns_none_for_missing(kg):
    assert kg.get_entity("nonexistent") is None


def test_get_entity_returns_dict(kg):
    _seed_kg(kg)
    e = kg.get_entity("e1")
    assert e is not None
    assert e["name"] == "Alice"
    assert e["type"] == "person"


def test_get_entity_relations(kg):
    _seed_kg(kg)
    rel = kg.get_entity_relations("e1")
    assert len(rel["outgoing"]) == 1
    assert rel["outgoing"][0]["predicate"] == "knows"
    assert len(rel["incoming"]) == 0
    assert "wing1/room1" in rel["closets"]


def test_get_triple_returns_none_for_missing(kg):
    triple, subject, obj = kg.get_triple("nonexistent")
    assert triple is None
    assert subject is None
    assert obj is None


def test_get_triple_returns_tuple(kg):
    _seed_kg(kg)
    triple, subject, obj = kg.get_triple("t1")
    assert triple is not None
    assert triple["predicate"] == "knows"
    assert subject["name"] == "Alice"
    assert obj["name"] == "Bob"


def test_update_triple_wing(kg):
    _seed_kg(kg)
    kg.update_triple_wing("wing1", "wing2")
    row = kg._mem_conn.execute(
        "SELECT source_closet FROM triples WHERE id='t1'"
    ).fetchone()
    assert row[0] == "wing2/room1"
```

- [ ] **Step 2: Run tests — expect ImportError**

```bash
pytest tests/test_storage.py -v
```

Expected: `ImportError: cannot import name 'KGStore' from 'src.storage'`

- [ ] **Step 3: Implement KGStore in `src/storage.py`**

```python
import sqlite3
from typing import Any


class KGStore:
    """Read/write access to the mempalace SQLite knowledge graph."""

    def __init__(self, path: str) -> None:
        self.path = path
        self._mem_conn: sqlite3.Connection | None = None
        if path == ":memory:":
            self._mem_conn = sqlite3.connect(":memory:", check_same_thread=False)
            self._mem_conn.row_factory = sqlite3.Row

    def _get_conn(self) -> tuple[sqlite3.Connection, bool]:
        """Return (connection, should_close_after_use)."""
        if self._mem_conn is not None:
            return self._mem_conn, False
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn, True

    def get_graph(self, show_invalidated: bool = False) -> dict:
        conn, close = self._get_conn()
        try:
            triples = conn.execute(
                "SELECT id, subject, predicate, object, confidence "
                "FROM triples WHERE valid_to IS NULL"
            ).fetchall()

            active_ids: set[str] = set()
            for t in triples:
                active_ids.add(t["subject"])
                active_ids.add(t["object"])

            all_entities = conn.execute(
                "SELECT id, name, type, properties, created_at FROM entities"
            ).fetchall()
            entities = (
                all_entities
                if show_invalidated
                else [e for e in all_entities if e["id"] in active_ids]
            )

            indegree: dict[str, int] = {}
            for t in triples:
                indegree[t["object"]] = indegree.get(t["object"], 0) + 1

            seen: set[str] = set()
            nodes = []
            for e in entities:
                if e["id"] in seen:
                    continue
                seen.add(e["id"])
                nodes.append({
                    "id": e["id"],
                    "name": e["name"],
                    "type": e["type"] or "unknown",
                    "created_at": e["created_at"],
                    "is_root": indegree.get(e["id"], 0) == 0,
                })

            edges = [
                {
                    "id": t["id"],
                    "subject": t["subject"],
                    "predicate": t["predicate"],
                    "object": t["object"],
                    "confidence": t["confidence"],
                }
                for t in triples
            ]
            return {"nodes": nodes, "edges": edges}
        finally:
            if close:
                conn.close()

    def get_entity(self, entity_id: str) -> dict[str, Any] | None:
        conn, close = self._get_conn()
        try:
            row = conn.execute(
                "SELECT * FROM entities WHERE id = ?", (entity_id,)
            ).fetchone()
            return dict(row) if row else None
        finally:
            if close:
                conn.close()

    def get_entity_relations(self, entity_id: str) -> dict:
        conn, close = self._get_conn()
        try:
            outgoing = conn.execute(
                """
                SELECT t.predicate, t.object, t.confidence, t.valid_from, t.valid_to,
                       t.source_closet, t.source_file,
                       e.name AS object_name, e.type AS object_type
                FROM triples t LEFT JOIN entities e ON t.object = e.id
                WHERE t.subject = ? AND t.valid_to IS NULL
                ORDER BY t.predicate
                """,
                (entity_id,),
            ).fetchall()
            incoming = conn.execute(
                """
                SELECT t.subject, t.predicate, t.confidence, t.valid_from, t.valid_to,
                       t.source_closet, t.source_file,
                       e.name AS subject_name, e.type AS subject_type
                FROM triples t LEFT JOIN entities e ON t.subject = e.id
                WHERE t.object = ? AND t.valid_to IS NULL
                ORDER BY t.predicate
                """,
                (entity_id,),
            ).fetchall()
            closets: set[str] = set()
            for t in list(outgoing) + list(incoming):
                if t["source_closet"]:
                    closets.add(t["source_closet"])
            return {
                "outgoing": [dict(t) for t in outgoing],
                "incoming": [dict(t) for t in incoming],
                "closets": sorted(closets),
            }
        finally:
            if close:
                conn.close()

    def get_triple(
        self, triple_id: str
    ) -> tuple[dict | None, dict | None, dict | None]:
        conn, close = self._get_conn()
        try:
            triple = conn.execute(
                "SELECT * FROM triples WHERE id = ?", (triple_id,)
            ).fetchone()
            if not triple:
                return None, None, None
            subject = conn.execute(
                "SELECT id, name, type FROM entities WHERE id = ?",
                (triple["subject"],),
            ).fetchone()
            obj = conn.execute(
                "SELECT id, name, type FROM entities WHERE id = ?",
                (triple["object"],),
            ).fetchone()
            return (
                dict(triple),
                dict(subject) if subject else None,
                dict(obj) if obj else None,
            )
        finally:
            if close:
                conn.close()

    def update_triple_wing(self, source: str, target: str) -> None:
        conn, close = self._get_conn()
        try:
            conn.execute(
                "UPDATE triples SET source_closet = ? || SUBSTR(source_closet, ?) "
                "WHERE source_closet LIKE ?",
                (target + "/", len(source) + 2, source + "/%"),
            )
            conn.commit()
        finally:
            if close:
                conn.close()
```

- [ ] **Step 4: Run KGStore tests — expect PASS**

```bash
pytest tests/test_storage.py -k "kg" -v
```

Expected: 8 passed.

- [ ] **Step 5: Commit**

```bash
git add src/storage.py tests/test_storage.py
git commit -m "feat(storage): add KGStore with in-memory test support"
```

---

## Task 4: `src/storage.py` — PalaceStore

**Files:**
- Modify: `src/storage.py` (append PalaceStore)
- Modify: `tests/test_storage.py` (append PalaceStore tests)

- [ ] **Step 1: Append PalaceStore tests to `tests/test_storage.py`**

First, add `PalaceStore` to the existing import at the top of the file:
```python
from src.storage import KGStore, PalaceStore   # was: KGStore only
```

Then append the following tests at the bottom of the file:

```python
# ── PalaceStore tests ──────────────────────────────────────────────────────


@pytest.fixture
def palace():
    return PalaceStore()   # path=None → EphemeralClient


def _seed_palace(palace: PalaceStore, drawers: list[dict] | None = None) -> list[str]:
    """Add drawers and return their IDs."""
    if drawers is None:
        drawers = [
            {"id": "d1", "content": "Alice likes cats", "wing": "wing1", "room": "room1"},
            {"id": "d2", "content": "Bob likes dogs",   "wing": "wing1", "room": "room2"},
            {"id": "d3", "content": "Charlie likes fish","wing": "wing2", "room": "room1"},
        ]
    col = palace._col
    for d in drawers:
        col.add(
            ids=[d["id"]],
            documents=[d["content"]],
            metadatas=[{"wing": d["wing"], "room": d["room"], "source_file": ""}],
        )
    return [d["id"] for d in drawers]


def test_palace_get_tree_empty(palace):
    tree = palace.get_tree()
    assert tree["wings"] == []
    assert tree["total_drawers"] == 0


def test_palace_get_tree_populated(palace):
    _seed_palace(palace)
    tree = palace.get_tree()
    assert tree["total_drawers"] == 3
    wing_names = [w["name"] for w in tree["wings"]]
    assert "wing1" in wing_names
    assert "wing2" in wing_names


def test_palace_get_drawers_all(palace):
    _seed_palace(palace)
    drawers = palace.get_drawers(None, None, 50, 0)
    assert len(drawers) == 3


def test_palace_get_drawers_wing_filter(palace):
    _seed_palace(palace)
    drawers = palace.get_drawers("wing1", None, 50, 0)
    assert len(drawers) == 2
    assert all(d["wing"] == "wing1" for d in drawers)


def test_palace_get_drawers_room_filter(palace):
    _seed_palace(palace)
    drawers = palace.get_drawers("wing1", "room1", 50, 0)
    assert len(drawers) == 1
    assert drawers[0]["id"] == "d1"


def test_palace_get_drawer_by_id(palace):
    _seed_palace(palace)
    d = palace.get_drawer_by_id("d1")
    assert d is not None
    assert d["content"] == "Alice likes cats"
    assert d["wing"] == "wing1"


def test_palace_get_drawer_by_id_missing(palace):
    palace_store = PalaceStore()
    assert palace_store.get_drawer_by_id("nonexistent") is None


def test_palace_search_returns_results(palace):
    _seed_palace(palace)
    results = palace.search("Alice cats", limit=5)
    assert len(results) > 0
    assert results[0]["wing"] == "wing1"


def test_palace_search_empty_collection(palace):
    results = palace.search("anything", limit=5)
    assert results == []


def test_palace_merge_wings(palace):
    _seed_palace(palace)
    moved = palace.merge_wings("wing1", "merged")
    assert moved == 2
    drawers = palace.get_drawers("merged", None, 50, 0)
    assert len(drawers) == 2


def test_palace_dedupe_wing(palace):
    col = palace._col
    col.add(ids=["x1"], documents=["same content"], metadatas=[{"wing": "w", "room": "r", "source_file": ""}])
    col.add(ids=["x2"], documents=["same content"], metadatas=[{"wing": "w", "room": "r", "source_file": ""}])
    col.add(ids=["x3"], documents=["unique"],       metadatas=[{"wing": "w", "room": "r", "source_file": ""}])
    result = palace.dedupe_wing("w")
    assert result["removed"] == 1
    assert result["kept"] == 2


def test_palace_delete_wing(palace):
    _seed_palace(palace)
    count = palace.delete_wing("wing1")
    assert count == 2
    assert palace.get_drawers("wing1", None, 50, 0) == []


def test_palace_delete_room(palace):
    _seed_palace(palace)
    count = palace.delete_room("wing1", "room1")
    assert count == 1
    remaining = palace.get_drawers("wing1", None, 50, 0)
    assert len(remaining) == 1
    assert remaining[0]["id"] == "d2"


def test_palace_delete_drawer(palace):
    _seed_palace(palace)
    palace.delete_drawer("d1")
    assert palace.get_drawer_by_id("d1") is None
```

- [ ] **Step 2: Run new tests — expect ImportError / AttributeError**

```bash
pytest tests/test_storage.py -k "palace" -v
```

Expected: `ImportError: cannot import name 'PalaceStore' from 'src.storage'`

- [ ] **Step 3: Append PalaceStore to `src/storage.py`**

```python
# ── PalaceStore ────────────────────────────────────────────────────────────

from functools import cached_property
from pathlib import Path as _Path


class PalaceStore:
    """ChromaDB-backed palace: drawer storage and retrieval."""

    COLLECTION = "mempalace_drawers"

    def __init__(self, path: str | None = None) -> None:
        import chromadb
        if path is None:
            self._client = chromadb.EphemeralClient()
        else:
            self._client = chromadb.PersistentClient(path=path)

    @cached_property
    def _col(self):
        return self._client.get_or_create_collection(self.COLLECTION)

    # ── reads ──────────────────────────────────────────────────────────────

    def search(self, q: str, limit: int = 30) -> list[dict]:
        try:
            results = self._col.query(
                query_texts=[q],
                n_results=limit,
                include=["documents", "metadatas", "distances"],
            )
        except Exception:
            return []
        ids   = results["ids"][0]
        docs  = results["documents"][0]
        metas = results["metadatas"][0]
        dists = results["distances"][0]
        return [
            {
                "id":         doc_id,
                "content":    doc[:300],
                "wing":       meta.get("wing", "unknown"),
                "room":       meta.get("room", "unknown"),
                "source":     _Path(meta.get("source_file", "") or "").name,
                "similarity": round(max(0.0, 1.0 - dist / 2), 3),
            }
            for doc_id, doc, meta, dist in zip(ids, docs, metas, dists)
        ]

    def get_tree(self) -> dict:
        all_data = self._col.get(include=["metadatas"])
        wings_map: dict = {}
        for m in all_data["metadatas"]:
            w  = m.get("wing", "?")
            r  = m.get("room", "?")
            sf = m.get("source_file", "")
            wings_map.setdefault(w, {}).setdefault(r, {"count": 0, "files": set()})
            wings_map[w][r]["count"] += 1
            fname = sf.rsplit("/", 1)[-1]
            if fname:
                wings_map[w][r]["files"].add(fname)
        wings = [
            {
                "name": w_name,
                "rooms": [
                    {
                        "name": r_name,
                        "drawer_count": data["count"],
                        "sources": sorted(data["files"])[:8],
                    }
                    for r_name, data in sorted(rooms.items())
                ],
            }
            for w_name, rooms in sorted(wings_map.items())
        ]
        return {"wings": wings, "total_drawers": len(all_data["metadatas"])}

    def get_drawers(
        self,
        wing: str | None,
        room: str | None,
        limit: int,
        offset: int,
    ) -> list[dict]:
        where: dict = {}
        if wing and room:
            where = {"$and": [{"wing": wing}, {"room": room}]}
        elif wing:
            where = {"wing": wing}
        elif room:
            where = {"room": room}
        kwargs: dict = {"include": ["documents", "metadatas"], "limit": limit, "offset": offset}
        if where:
            kwargs["where"] = where
        results = self._col.get(**kwargs)
        ids = results.get("ids", [])
        return [
            {
                "id":      ids[i] if i < len(ids) else None,
                "content": doc,
                "wing":    meta.get("wing"),
                "room":    meta.get("room"),
                "source":  meta.get("source_file"),
            }
            for i, (doc, meta) in enumerate(zip(results["documents"], results["metadatas"]))
        ]

    def get_drawer_by_id(self, drawer_id: str) -> dict | None:
        results = self._col.get(ids=[drawer_id], include=["documents", "metadatas"])
        if not results["ids"]:
            return None
        return {
            "id":      drawer_id,
            "content": results["documents"][0],
            "wing":    results["metadatas"][0].get("wing"),
            "room":    results["metadatas"][0].get("room"),
            "source":  results["metadatas"][0].get("source_file"),
        }

    def get_source_drawer(self, source_closet: str) -> str | None:
        """Fetch the first drawer that matches source_closet (used by triple detail)."""
        try:
            where: dict = {}
            if "/" in source_closet:
                where = {"wing": source_closet.split("/")[0]}
            results = self._col.query(
                query_texts=[source_closet],
                n_results=1,
                where=where or None,
                include=["documents"],
            )
            if results["documents"] and results["documents"][0]:
                return results["documents"][0][0]
            return None
        except Exception:
            return None

    # ── mutations ──────────────────────────────────────────────────────────

    def merge_wings(self, source: str, target: str) -> int:
        src = self._col.get(where={"wing": source}, include=["metadatas", "documents"])
        moved = 0
        for i, doc_id in enumerate(src["ids"]):
            meta = {**src["metadatas"][i], "wing": target}
            self._col.update(ids=[doc_id], metadatas=[meta])
            moved += 1
        return moved

    def dedupe_wing(self, wing: str) -> dict:
        src = self._col.get(where={"wing": wing}, include=["documents"])
        seen: dict[str, str] = {}
        dup_ids: list[str] = []
        for doc_id, doc in zip(src["ids"], src["documents"]):
            if doc in seen:
                dup_ids.append(doc_id)
            else:
                seen[doc] = doc_id
        if dup_ids:
            self._col.delete(ids=dup_ids)
        return {"removed": len(dup_ids), "kept": len(seen)}

    def delete_wing(self, wing: str) -> int:
        src = self._col.get(where={"wing": wing}, include=[])
        if src["ids"]:
            self._col.delete(ids=src["ids"])
        return len(src["ids"])

    def delete_room(self, wing: str, room: str) -> int:
        src = self._col.get(
            where={"$and": [{"wing": wing}, {"room": room}]}, include=[]
        )
        if src["ids"]:
            self._col.delete(ids=src["ids"])
        return len(src["ids"])

    def delete_drawer(self, drawer_id: str) -> None:
        self._col.delete(ids=[drawer_id])
```

- [ ] **Step 4: Run all storage tests — expect PASS**

```bash
pytest tests/test_storage.py -v
```

Expected: all passed (8 KGStore + 15 PalaceStore = 23 total).

- [ ] **Step 5: Commit**

```bash
git add src/storage.py tests/test_storage.py
git commit -m "feat(storage): add PalaceStore with ChromaDB EphemeralClient support"
```

---

## Task 5: `src/events.py`

**Files:**
- Create: `src/events.py`

No tests — this is a pure asyncio primitive, tested indirectly via SSE route tests.

- [ ] **Step 1: Create `src/events.py`**

```python
import asyncio

_update_event: asyncio.Event = asyncio.Event()


def signal_update() -> None:
    """Signal all SSE clients that palace data has changed."""
    _update_event.set()


def get_event() -> asyncio.Event:
    return _update_event
```

- [ ] **Step 2: Commit**

```bash
git add src/events.py
git commit -m "feat(events): add SSE signal_update and get_event"
```

---

## Task 6: `src/ui_html.py`

**Files:**
- Create: `src/ui_html.py`

Extract the `GRAPH_HTML` string from `server.py`. No logic changes.

- [ ] **Step 1: Create `src/ui_html.py`**

Open `server.py` and find the line `GRAPH_HTML = """\`. Copy everything from that line through the closing `"""` (lines 487–1152) into a new file:

```python
# src/ui_html.py
"""Static HTML/JS for the MemPalace browser UI."""

GRAPH_HTML = """\
<!DOCTYPE html>
...   # paste the full string from server.py here
"""
```

The string ends at the line `"""` just before `@app.get("/")`.

- [ ] **Step 2: Verify the string is intact**

```bash
python3 -c "from src.ui_html import GRAPH_HTML; assert '<!DOCTYPE html>' in GRAPH_HTML; assert 'vis-network' in GRAPH_HTML; print('OK', len(GRAPH_HTML), 'chars')"
```

Expected: `OK <number> chars` with no error.

- [ ] **Step 3: Commit**

```bash
git add src/ui_html.py
git commit -m "refactor: extract GRAPH_HTML to src/ui_html.py"
```

---

## Task 7: `src/deps.py`

**Files:**
- Create: `src/deps.py`

- [ ] **Step 1: Create `src/deps.py`**

```python
from functools import lru_cache
from .config import Settings
from .storage import KGStore, PalaceStore


@lru_cache
def _settings() -> Settings:
    return Settings()


def get_palace_store() -> PalaceStore:
    s = _settings()
    return PalaceStore(path=s.palace_path)


def get_kg_store() -> KGStore:
    s = _settings()
    return KGStore(path=s.resolved_kg_path)
```

- [ ] **Step 2: Commit**

```bash
git add src/deps.py
git commit -m "feat(deps): add FastAPI dependency factories for storage"
```

---

## Task 8: `src/routes/ui.py`

**Files:**
- Create: `src/routes/ui.py`

- [ ] **Step 1: Create `src/routes/ui.py`**

```python
import asyncio

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, StreamingResponse

from ..config import Settings
from ..events import get_event
from ..ui_html import GRAPH_HTML

router = APIRouter()


@router.get("/health")
async def health() -> dict:
    s = Settings()
    return {"status": "ok", "palace_path": s.palace_path}


@router.get("/")
async def graph_ui() -> HTMLResponse:
    return HTMLResponse(GRAPH_HTML)


@router.get("/events")
async def sse_events() -> StreamingResponse:
    event = get_event()

    async def stream():
        while True:
            try:
                await asyncio.wait_for(event.wait(), timeout=30)
            except asyncio.TimeoutError:
                yield ": keepalive\n\n"
                continue
            event.clear()
            yield "event: update\ndata:\n\n"

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )
```

- [ ] **Step 2: Commit**

```bash
git add src/routes/ui.py
git commit -m "feat(routes/ui): add health, graph UI, and SSE endpoints"
```

---

## Task 9: `src/routes/kg.py`

**Files:**
- Create: `src/routes/kg.py`

- [ ] **Step 1: Create `src/routes/kg.py`**

```python
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from ..deps import get_kg_store, get_palace_store
from ..storage import KGStore, PalaceStore

router = APIRouter()

_TYPE_COLORS = {
    "person":   "#4CAF50",
    "project":  "#2196F3",
    "artifact": "#FF9800",
    "concept":  "#9C27B0",
    "tool":     "#F44336",
    "location": "#00BCD4",
    "event":    "#795548",
    "unknown":  "#607D8B",
}


@router.get("/api/graph")
async def get_graph(
    show_invalidated: bool = False,
    kg: KGStore = Depends(get_kg_store),
) -> dict:
    data = kg.get_graph(show_invalidated)
    nodes = [
        {
            "id":    n["id"],
            "label": n["name"],
            "group": n["type"],
            "color": _TYPE_COLORS.get(n["type"], "#607D8B"),
            "root":  n["is_root"],
            "title": (
                f"<b>{n['name']}</b><br>"
                f"type: {n['type']}<br>"
                f"created: {n['created_at']}<br>"
                f"id: {n['id']}"
            ),
        }
        for n in data["nodes"]
    ]
    edges = [
        {
            "id":      e["id"],
            "from":    e["subject"],
            "to":      e["object"],
            "label":   e["predicate"],
            "arrows":  "to",
            "title":   (
                f"{e['subject']} <b>{e['predicate']}</b> {e['object']}<br>"
                f"confidence: {e['confidence']}"
            ),
        }
        for e in data["edges"]
    ]
    return {"nodes": nodes, "edges": edges}


@router.get("/api/entity/{entity_id:path}")
async def get_entity_detail(
    entity_id: str,
    kg: KGStore = Depends(get_kg_store),
) -> dict | JSONResponse:
    entity = kg.get_entity(entity_id)
    if entity is None:
        return JSONResponse({"error": "Entity not found"}, status_code=404)
    relations = kg.get_entity_relations(entity_id)
    return {
        "entity":   entity,
        "outgoing": relations["outgoing"],
        "incoming": relations["incoming"],
        "closets":  relations["closets"],
    }


@router.get("/api/triple/{triple_id:path}")
async def get_triple_detail(
    triple_id: str,
    kg: KGStore = Depends(get_kg_store),
    palace: PalaceStore = Depends(get_palace_store),
) -> dict | JSONResponse:
    triple, subject, obj = kg.get_triple(triple_id)
    if triple is None:
        return JSONResponse({"error": "Triple not found"}, status_code=404)
    drawer_text = (
        palace.get_source_drawer(triple["source_closet"])
        if triple.get("source_closet")
        else None
    )
    return {
        "triple":        triple,
        "subject":       subject,
        "object":        obj,
        "source_drawer": drawer_text,
    }
```

- [ ] **Step 2: Commit**

```bash
git add src/routes/kg.py
git commit -m "feat(routes/kg): add graph, entity, and triple endpoints"
```

---

## Task 10: `src/routes/palace.py`

**Files:**
- Create: `src/routes/palace.py`

- [ ] **Step 1: Create `src/routes/palace.py`**

```python
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from ..deps import get_kg_store, get_palace_store
from ..events import signal_update
from ..storage import KGStore, PalaceStore

router = APIRouter()


@router.get("/api/palace")
async def get_palace_tree(palace: PalaceStore = Depends(get_palace_store)) -> dict:
    return palace.get_tree()


@router.get("/api/palace/search")
async def search_drawers(
    q: str = "",
    limit: int = 30,
    palace: PalaceStore = Depends(get_palace_store),
) -> dict:
    if not q.strip():
        return {"results": []}
    return {"results": palace.search(q, limit)}


@router.post("/api/palace/merge")
async def merge_wings(
    source: str,
    target: str,
    palace: PalaceStore = Depends(get_palace_store),
    kg: KGStore = Depends(get_kg_store),
) -> dict | JSONResponse:
    if source == target:
        return JSONResponse({"error": "Cannot merge wing into itself"}, status_code=400)
    moved = palace.merge_wings(source, target)
    if moved == 0:
        return JSONResponse({"error": f"Wing '{source}' not found"}, status_code=404)
    kg.update_triple_wing(source, target)
    signal_update()
    return {"merged": moved, "source": source, "target": target}


@router.post("/api/palace/dedupe")
async def dedupe_wing(
    wing: str,
    palace: PalaceStore = Depends(get_palace_store),
) -> dict:
    result = palace.dedupe_wing(wing)
    signal_update()
    return {"wing": wing, **result}


@router.post("/api/palace/delete-wing")
async def delete_wing(
    wing: str,
    palace: PalaceStore = Depends(get_palace_store),
) -> dict:
    deleted = palace.delete_wing(wing)
    signal_update()
    return {"deleted": deleted}


@router.post("/api/palace/delete-room")
async def delete_room(
    wing: str,
    room: str,
    palace: PalaceStore = Depends(get_palace_store),
) -> dict:
    deleted = palace.delete_room(wing, room)
    signal_update()
    return {"deleted": deleted}
```

- [ ] **Step 2: Commit**

```bash
git add src/routes/palace.py
git commit -m "feat(routes/palace): add palace tree, search, and mutation endpoints"
```

---

## Task 11: `src/routes/drawers.py`

**Files:**
- Create: `src/routes/drawers.py`

- [ ] **Step 1: Create `src/routes/drawers.py`**

```python
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from ..deps import get_palace_store
from ..events import signal_update
from ..storage import PalaceStore

router = APIRouter()


@router.get("/api/drawers")
async def get_drawers(
    wing: str | None = None,
    room: str | None = None,
    limit: int = 50,
    offset: int = 0,
    palace: PalaceStore = Depends(get_palace_store),
) -> dict:
    drawers = palace.get_drawers(wing, room, limit, offset)
    return {"drawers": drawers, "total": len(drawers)}


@router.get("/api/drawer/{drawer_id:path}")
async def get_drawer_by_id(
    drawer_id: str,
    palace: PalaceStore = Depends(get_palace_store),
) -> dict | JSONResponse:
    drawer = palace.get_drawer_by_id(drawer_id)
    if drawer is None:
        return JSONResponse({"error": "not found"}, status_code=404)
    return drawer


@router.post("/api/palace/delete-drawer")
async def delete_drawer(
    id: str,
    palace: PalaceStore = Depends(get_palace_store),
) -> dict:
    palace.delete_drawer(id)
    signal_update()
    return {"deleted": 1}
```

- [ ] **Step 2: Commit**

```bash
git add src/routes/drawers.py
git commit -m "feat(routes/drawers): add drawer list, get, and delete endpoints"
```

---

## Task 12: `src/routes/mcp.py`

**Files:**
- Create: `src/routes/mcp.py`

- [ ] **Step 1: Create `src/routes/mcp.py`**

```python
import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from mempalace.mcp_server import handle_request

from ..events import signal_update

logger = logging.getLogger("mempalace-server")
router = APIRouter()

_MUTATION_KEYWORDS = ("add", "delete", "invalidate", "write")


@router.post("/mcp")
async def mcp_endpoint(request: Request) -> JSONResponse:
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(
            {"jsonrpc": "2.0", "id": None,
             "error": {"code": -32700, "message": "Parse error"}},
            status_code=400,
        )

    logger.info("MCP %s id=%s", body.get("method"), body.get("id"))
    response = handle_request(body)

    method = body.get("method", "")
    if method.startswith("mempalace_") and any(kw in method for kw in _MUTATION_KEYWORDS):
        signal_update()

    if response is None:
        return JSONResponse({}, status_code=204)

    return JSONResponse(response)
```

- [ ] **Step 2: Commit**

```bash
git add src/routes/mcp.py
git commit -m "feat(routes/mcp): add MCP streamable HTTP endpoint"
```

---

## Task 13: `src/app.py`

**Files:**
- Create: `src/app.py`

- [ ] **Step 1: Create `src/app.py`**

```python
import logging

from fastapi import FastAPI

from .deps import get_kg_store, get_palace_store
from .routes.drawers import router as drawers_router
from .routes.kg import router as kg_router
from .routes.mcp import router as mcp_router
from .routes.palace import router as palace_router
from .routes.ui import router as ui_router
from .storage import KGStore, PalaceStore

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def create_app(
    palace_store: PalaceStore | None = None,
    kg_store: KGStore | None = None,
) -> FastAPI:
    """FastAPI factory. Pass stores to override deps in tests."""
    app = FastAPI(title="MemPalace MCP", version="3.4.1")

    if palace_store is not None:
        app.dependency_overrides[get_palace_store] = lambda: palace_store
    if kg_store is not None:
        app.dependency_overrides[get_kg_store] = lambda: kg_store

    app.include_router(ui_router)
    app.include_router(kg_router)
    app.include_router(palace_router)
    app.include_router(drawers_router)
    app.include_router(mcp_router)

    return app
```

- [ ] **Step 2: Smoke test the factory**

```bash
python3 -c "from src.app import create_app; app = create_app(); print('routes:', [r.path for r in app.routes])"
```

Expected: prints a list of route paths including `/`, `/health`, `/api/graph`, `/mcp`, etc.

- [ ] **Step 3: Commit**

```bash
git add src/app.py
git commit -m "feat(app): add create_app factory with dependency injection"
```

---

## Task 14: `tests/conftest.py`

**Files:**
- Create: `tests/conftest.py`

- [ ] **Step 1: Create `tests/conftest.py`**

```python
import sqlite3

import pytest
from fastapi.testclient import TestClient

from src.app import create_app
from src.storage import KGStore, PalaceStore

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


@pytest.fixture
def palace_store():
    return PalaceStore()   # EphemeralClient — fresh per test


@pytest.fixture
def kg_store():
    store = KGStore(":memory:")
    store._mem_conn.executescript(KG_SCHEMA)
    return store


@pytest.fixture
def client(palace_store, kg_store):
    app = create_app(palace_store=palace_store, kg_store=kg_store)
    return TestClient(app)
```

- [ ] **Step 2: Verify conftest loads**

```bash
pytest tests/conftest.py --collect-only
```

Expected: no errors, `0 tests collected`.

- [ ] **Step 3: Commit**

```bash
git add tests/conftest.py
git commit -m "test: add conftest with in-memory palace and kg fixtures"
```

---

## Task 15: `tests/test_kg.py`

**Files:**
- Create: `tests/test_kg.py`

- [ ] **Step 1: Create `tests/test_kg.py`**

```python
import pytest


def _seed(kg_store):
    kg_store._mem_conn.execute(
        "INSERT INTO entities VALUES (?,?,?,?,?)",
        ("e1", "Alice", "person", "{}", "2024-01-01"),
    )
    kg_store._mem_conn.execute(
        "INSERT INTO entities VALUES (?,?,?,?,?)",
        ("e2", "Bob", "person", "{}", "2024-01-01"),
    )
    kg_store._mem_conn.execute(
        "INSERT INTO triples VALUES (?,?,?,?,?,?,?,?,?)",
        ("t1", "e1", "knows", "e2", 0.9, None, None, "wing1/room1", None),
    )
    kg_store._mem_conn.commit()


def test_graph_empty(client):
    resp = client.get("/api/graph")
    assert resp.status_code == 200
    data = resp.json()
    assert data["nodes"] == []
    assert data["edges"] == []


def test_graph_with_data(client, kg_store):
    _seed(kg_store)
    resp = client.get("/api/graph")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["nodes"]) == 2
    assert len(data["edges"]) == 1
    node = next(n for n in data["nodes"] if n["id"] == "e1")
    assert node["label"] == "Alice"
    assert node["color"] == "#4CAF50"   # person color
    edge = data["edges"][0]
    assert edge["from"] == "e1"
    assert edge["to"] == "e2"
    assert edge["label"] == "knows"


def test_entity_not_found(client):
    resp = client.get("/api/entity/nonexistent")
    assert resp.status_code == 404
    assert "error" in resp.json()


def test_entity_detail(client, kg_store):
    _seed(kg_store)
    resp = client.get("/api/entity/e1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["entity"]["name"] == "Alice"
    assert len(data["outgoing"]) == 1
    assert data["outgoing"][0]["predicate"] == "knows"
    assert len(data["incoming"]) == 0
    assert "wing1/room1" in data["closets"]


def test_triple_not_found(client):
    resp = client.get("/api/triple/nonexistent")
    assert resp.status_code == 404


def test_triple_detail(client, kg_store):
    _seed(kg_store)
    resp = client.get("/api/triple/t1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["triple"]["predicate"] == "knows"
    assert data["subject"]["name"] == "Alice"
    assert data["object"]["name"] == "Bob"
    assert data["source_drawer"] is None   # palace is empty
```

- [ ] **Step 2: Run tests**

```bash
pytest tests/test_kg.py -v
```

Expected: 6 passed.

- [ ] **Step 3: Commit**

```bash
git add tests/test_kg.py
git commit -m "test(kg): add route tests for graph, entity, and triple endpoints"
```

---

## Task 16: `tests/test_palace.py`

**Files:**
- Create: `tests/test_palace.py`

- [ ] **Step 1: Create `tests/test_palace.py`**

```python
def _seed(palace_store):
    col = palace_store._col
    col.add(
        ids=["d1", "d2", "d3"],
        documents=["Alice likes cats", "Bob likes dogs", "Charlie likes fish"],
        metadatas=[
            {"wing": "wing1", "room": "room1", "source_file": ""},
            {"wing": "wing1", "room": "room2", "source_file": ""},
            {"wing": "wing2", "room": "room1", "source_file": ""},
        ],
    )


def test_palace_tree_empty(client):
    resp = client.get("/api/palace")
    assert resp.status_code == 200
    data = resp.json()
    assert data["wings"] == []
    assert data["total_drawers"] == 0


def test_palace_tree_populated(client, palace_store):
    _seed(palace_store)
    resp = client.get("/api/palace")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_drawers"] == 3
    wing_names = [w["name"] for w in data["wings"]]
    assert "wing1" in wing_names
    assert "wing2" in wing_names


def test_search_empty_query(client):
    resp = client.get("/api/palace/search?q=")
    assert resp.status_code == 200
    assert resp.json() == {"results": []}


def test_search_returns_results(client, palace_store):
    _seed(palace_store)
    resp = client.get("/api/palace/search?q=cats")
    assert resp.status_code == 200
    results = resp.json()["results"]
    assert len(results) > 0
    assert results[0]["wing"] == "wing1"


def test_merge_wings(client, palace_store):
    _seed(palace_store)
    resp = client.post("/api/palace/merge?source=wing1&target=merged")
    assert resp.status_code == 200
    data = resp.json()
    assert data["merged"] == 2


def test_merge_same_wing_returns_400(client):
    resp = client.post("/api/palace/merge?source=wing1&target=wing1")
    assert resp.status_code == 400


def test_merge_missing_wing_returns_404(client):
    resp = client.post("/api/palace/merge?source=nonexistent&target=other")
    assert resp.status_code == 404


def test_dedupe_removes_duplicates(client, palace_store):
    col = palace_store._col
    col.add(
        ids=["x1", "x2", "x3"],
        documents=["same", "same", "unique"],
        metadatas=[
            {"wing": "w", "room": "r", "source_file": ""},
            {"wing": "w", "room": "r", "source_file": ""},
            {"wing": "w", "room": "r", "source_file": ""},
        ],
    )
    resp = client.post("/api/palace/dedupe?wing=w")
    assert resp.status_code == 200
    data = resp.json()
    assert data["removed"] == 1
    assert data["kept"] == 2


def test_delete_wing(client, palace_store):
    _seed(palace_store)
    resp = client.post("/api/palace/delete-wing?wing=wing1")
    assert resp.status_code == 200
    assert resp.json()["deleted"] == 2
    check = client.get("/api/palace")
    wing_names = [w["name"] for w in check.json()["wings"]]
    assert "wing1" not in wing_names


def test_delete_room(client, palace_store):
    _seed(palace_store)
    resp = client.post("/api/palace/delete-room?wing=wing1&room=room1")
    assert resp.status_code == 200
    assert resp.json()["deleted"] == 1
    tree = client.get("/api/palace").json()
    wing1 = next(w for w in tree["wings"] if w["name"] == "wing1")
    room_names = [r["name"] for r in wing1["rooms"]]
    assert "room1" not in room_names
    assert "room2" in room_names
```

- [ ] **Step 2: Run tests**

```bash
pytest tests/test_palace.py -v
```

Expected: all passed.

- [ ] **Step 3: Commit**

```bash
git add tests/test_palace.py
git commit -m "test(palace): add route tests for palace tree, search, and mutations"
```

---

## Task 17: `tests/test_drawers.py`

**Files:**
- Create: `tests/test_drawers.py`

- [ ] **Step 1: Create `tests/test_drawers.py`**

```python
def _seed(palace_store):
    palace_store._col.add(
        ids=["d1", "d2", "d3"],
        documents=["content one", "content two", "content three"],
        metadatas=[
            {"wing": "wing1", "room": "room1", "source_file": "a.md"},
            {"wing": "wing1", "room": "room2", "source_file": "b.md"},
            {"wing": "wing2", "room": "room1", "source_file": "c.md"},
        ],
    )


def test_get_all_drawers(client, palace_store):
    _seed(palace_store)
    resp = client.get("/api/drawers")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3


def test_get_drawers_wing_filter(client, palace_store):
    _seed(palace_store)
    resp = client.get("/api/drawers?wing=wing1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert all(d["wing"] == "wing1" for d in data["drawers"])


def test_get_drawers_room_filter(client, palace_store):
    _seed(palace_store)
    resp = client.get("/api/drawers?wing=wing1&room=room1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["drawers"][0]["id"] == "d1"


def test_get_drawer_by_id(client, palace_store):
    _seed(palace_store)
    resp = client.get("/api/drawer/d1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["content"] == "content one"
    assert data["wing"] == "wing1"


def test_get_drawer_not_found(client):
    resp = client.get("/api/drawer/nonexistent")
    assert resp.status_code == 404
    assert "error" in resp.json()


def test_delete_drawer(client, palace_store):
    _seed(palace_store)
    resp = client.post("/api/palace/delete-drawer?id=d1")
    assert resp.status_code == 200
    assert resp.json()["deleted"] == 1
    check = client.get("/api/drawer/d1")
    assert check.status_code == 404
```

- [ ] **Step 2: Run tests**

```bash
pytest tests/test_drawers.py -v
```

Expected: 6 passed.

- [ ] **Step 3: Commit**

```bash
git add tests/test_drawers.py
git commit -m "test(drawers): add route tests for drawer CRUD endpoints"
```

---

## Task 18: `tests/test_mcp.py`

**Files:**
- Create: `tests/test_mcp.py`

- [ ] **Step 1: Create `tests/test_mcp.py`**

```python
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
```

- [ ] **Step 2: Run tests**

```bash
pytest tests/test_mcp.py -v
```

Expected: 4 passed.

- [ ] **Step 3: Commit**

```bash
git add tests/test_mcp.py
git commit -m "test(mcp): add MCP endpoint tests with mocked handle_request"
```

---

## Task 19: Refactor `server.py` to entry point

**Files:**
- Modify: `server.py`

- [ ] **Step 1: Replace `server.py` with entry-point only**

```python
"""
MemPalace MCP Server — entry point.

Env vars:
  MEMPALACE_PALACE_PATH   path to ChromaDB storage  (default: /palace)
  MEMPALACE_KG_PATH       path to SQLite KG          (default: $PALACE_PATH/knowledge_graph.sqlite3)
  PORT                    HTTP port                   (default: 8080)
"""
import os

# ── KG path bootstrap — must happen before any mempalace import ────────────
_palace_path = os.environ.get("MEMPALACE_PALACE_PATH", "/palace")
_kg_path = os.environ.get(
    "MEMPALACE_KG_PATH",
    os.path.join(_palace_path, "knowledge_graph.sqlite3"),
)
import mempalace.knowledge_graph as _kg_module  # noqa: E402
_kg_module.DEFAULT_KG_PATH = _kg_path

# ── App ────────────────────────────────────────────────────────────────────
from src.app import create_app  # noqa: E402

app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)), log_level="info")
```

- [ ] **Step 2: Commit**

```bash
git add server.py
git commit -m "refactor: reduce server.py to entry point only"
```

---

## Task 20: Full test run and cleanup

**Files:**
- None new

- [ ] **Step 1: Run the full test suite**

```bash
pytest -v
```

Expected: all tests in `test_config.py`, `test_storage.py`, `test_kg.py`, `test_palace.py`, `test_drawers.py`, `test_mcp.py` pass.

- [ ] **Step 2: Smoke test the server boots**

```bash
python3 server.py &
sleep 2
curl -s http://localhost:8080/health
kill %1
```

Expected: `{"status":"ok","palace_path":"/palace"}`

- [ ] **Step 3: Final commit**

```bash
git add -A
git commit -m "chore: production refactor complete — DRY, SRP, fully tested"
```
