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
