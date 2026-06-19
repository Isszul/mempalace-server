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
