import logging

from fastapi import FastAPI

from .deps import get_kg_store, get_palace_store
from .routes.drawers import router as drawers_router
from .routes.kg import router as kg_router
from .routes.mcp import router as mcp_router
from .routes.palace import router as palace_router
from .routes.ui import router as ui_router
from .storage import KGStore, PalaceStore

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def create_app(
    palace_store: PalaceStore | None = None,
    kg_store: KGStore | None = None,
) -> FastAPI:
    """FastAPI factory. Pass stores to override deps in tests."""
    app = FastAPI(title="MemPalace MCP", version="3.4.1")

    if palace_store is not None:
        app.dependency_overrides[get_palace_store] = lambda: palace_store
    if kg_store is not None:
        app.dependency_overrides[get_kg_store] = lambda: kg_store

    app.include_router(ui_router)
    app.include_router(kg_router)
    app.include_router(palace_router)
    app.include_router(drawers_router)
    app.include_router(mcp_router)

    return app
