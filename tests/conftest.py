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
def palace_store(tmp_path):
    return PalaceStore(path=str(tmp_path))


@pytest.fixture
def kg_store():
    store = KGStore(":memory:")
    store._mem_conn.executescript(KG_SCHEMA)
    return store


@pytest.fixture
def client(palace_store, kg_store):
    app = create_app(palace_store=palace_store, kg_store=kg_store)
    return TestClient(app)
