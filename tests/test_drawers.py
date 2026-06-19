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
