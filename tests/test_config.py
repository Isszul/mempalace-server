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
