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
            "id":     e["id"],
            "from":   e["subject"],
            "to":     e["object"],
            "label":  e["predicate"],
            "arrows": "to",
            "title":  (
                f"{e['subject']} <b>{e['predicate']}</b> {e['object']}<br>"
                f"confidence: {e['confidence']}"
            ),
        }
        for e in data["edges"]
    ]
    return {"nodes": nodes, "edges": edges}


@router.get("/api/entity/{entity_id:path}", response_model=None)
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


@router.get("/api/triple/{triple_id:path}", response_model=None)
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
