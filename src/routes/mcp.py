import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from mempalace.mcp_server import handle_request

from ..events import signal_update

logger = logging.getLogger("mempalace-server")
router = APIRouter()

_MUTATION_KEYWORDS = ("add", "delete", "invalidate", "write")


@router.post("/mcp")
async def mcp_endpoint(
    request: Request,
) -> JSONResponse:
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(
            {"jsonrpc": "2.0", "id": None,
             "error": {"code": -32700, "message": "Parse error"}},
            status_code=400,
        )

    logger.info("MCP %s id=%s", body.get("method"), body.get("id"))
    response = handle_request(body)

    method = body.get("method", "")
    if method.startswith("mempalace_") and any(kw in method for kw in _MUTATION_KEYWORDS):
        signal_update()

    if response is None:
        return JSONResponse({}, status_code=204)

    return JSONResponse(response)
