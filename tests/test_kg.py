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
