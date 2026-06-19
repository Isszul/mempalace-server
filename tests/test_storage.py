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
