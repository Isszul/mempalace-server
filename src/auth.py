import base64
import logging

from fastapi import HTTPException, Request

from .config import Settings

logger = logging.getLogger("mempalace-server")
_WWW_AUTH = 'Basic realm="MemPalace", Bearer'


def verify_auth(request: Request) -> None:
    settings = Settings()
    if not settings.auth_token and not settings.auth_password:
        return
    if request.url.path == "/health":
        return

    auth = request.headers.get("authorization")
    if not auth:
        logger.warning("missing auth header path=%s", request.url.path)
        raise HTTPException(status_code=401, headers={"WWW-Authenticate": _WWW_AUTH})

    parts = auth.split(None, 1)
    if len(parts) != 2:
        raise HTTPException(status_code=401, headers={"WWW-Authenticate": _WWW_AUTH})

    scheme, credentials = parts[0].lower(), parts[1]

    if scheme == "bearer" and settings.auth_token:
        if credentials == settings.auth_token:
            return

    if scheme == "basic":
        try:
            decoded = base64.b64decode(credentials).decode()
            username, _, password = decoded.partition(":")
            expected_user = settings.auth_username or "admin"
            if settings.auth_password and username == expected_user and password == settings.auth_password:
                return
            if settings.auth_token and password == settings.auth_token:
                return
        except Exception:
            pass

    logger.warning("auth rejected: scheme=%s path=%s", scheme, request.url.path)
    raise HTTPException(status_code=401, headers={"WWW-Authenticate": _WWW_AUTH})
