from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse

from ..deps import get_kg_store, get_palace_store
from ..events import signal_update
from ..storage import KGStore, PalaceStore

router = APIRouter()


_INVALID_CHARS = set("$\\{}[]")


def _sanitize_name(name: str) -> str:
    if any(c in _INVALID_CHARS for c in name):
        raise HTTPException(status_code=400, detail=f"Invalid characters in name: {name}")
    return name


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


@router.post("/api/palace/merge", response_model=None)
async def merge_wings(
    source: str,
    target: str,
    palace: PalaceStore = Depends(get_palace_store),
    kg: KGStore = Depends(get_kg_store),
) -> dict | JSONResponse:
    _sanitize_name(source); _sanitize_name(target)
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
    _sanitize_name(wing)
    result = palace.dedupe_wing(wing)
    signal_update()
    return {"wing": wing, **result}


@router.post("/api/palace/delete-wing")
async def delete_wing(
    wing: str,
    palace: PalaceStore = Depends(get_palace_store),
) -> dict:
    _sanitize_name(wing)
    deleted = palace.delete_wing(wing)
    signal_update()
    return {"deleted": deleted}


@router.post("/api/palace/delete-room")
async def delete_room(
    wing: str,
    room: str,
    palace: PalaceStore = Depends(get_palace_store),
) -> dict:
    _sanitize_name(wing); _sanitize_name(room)
    deleted = palace.delete_room(wing, room)
    signal_update()
    return {"deleted": deleted}
