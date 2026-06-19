from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse

from ..deps import get_palace_store
from ..events import signal_update
from ..storage import PalaceStore

router = APIRouter()


def _sanitize_name(name: str | None) -> str | None:
    if name is not None and set("$\\{}[]") & set(name):
        raise HTTPException(status_code=400, detail=f"Invalid characters in name: {name}")
    return name


@router.get("/api/drawers")
async def get_drawers(
    wing: str | None = None,
    room: str | None = None,
    limit: int = 50,
    offset: int = 0,
    palace: PalaceStore = Depends(get_palace_store),
) -> dict:
    _sanitize_name(wing); _sanitize_name(room)
    drawers = palace.get_drawers(wing, room, limit, offset)
    return {"drawers": drawers, "total": len(drawers)}


@router.get("/api/drawer/{drawer_id:path}", response_model=None)
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
