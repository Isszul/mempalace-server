from fastapi import Header, HTTPException

from .config import Settings


def verify_mcp_token(authorization: str | None = Header(None)) -> None:
    settings = Settings()
    if not settings.auth_token:
        return
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    parts = authorization.split(None, 1)
    if len(parts) != 2 or parts[0].lower() != "bearer" or parts[1] != settings.auth_token:
        raise HTTPException(status_code=401, detail="Invalid token")
