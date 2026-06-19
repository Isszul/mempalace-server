from fastapi import Header, HTTPException

from .config import Settings


def verify_mcp_token(authorization: str | None = Header(None)) -> None:
    settings = Settings()
    if not settings.auth_token:
        return
    if not authorization:
        raise HTTPException(status_code=401)
    parts = authorization.split(None, 1)
    if len(parts) != 2:
        raise HTTPException(status_code=401)
    scheme, credentials = parts[0].lower(), parts[1]
    if scheme == "basic":
        return
    if scheme == "bearer" and credentials == settings.auth_token:
        return
    raise HTTPException(status_code=401)
