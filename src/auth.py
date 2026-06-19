import base64
import hmac
import logging

from fastapi import HTTPException, Request

from .config import Settings

logger = logging.getLogger("mempalace-server")
_WWW_AUTH = 'Bearer realm="MemPalace", Basic realm="MemPalace"'


def _safe_eq(a: str | None, b: str | None) -> bool:
    if a is None or b is None:
        return False
    return hmac.compare_digest(a.encode(), b.encode())


def verify_auth(request: Request) -> None:
    settings = Settings()
    if not settings.auth_token and not settings.auth_password:
        return
    path = request.url.path.rstrip("/").lower()
    if path == "/health":
        return

    auth = request.headers.get("authorization")
    if not auth:
        raise HTTPException(status_code=401, headers={"WWW-Authenticate": _WWW_AUTH})

    parts = auth.split(None, 1)
    if len(parts) != 2:
        raise HTTPException(status_code=401, headers={"WWW-Authenticate": _WWW_AUTH})

    scheme, credentials = parts[0].lower(), parts[1]

    if scheme == "bearer" and _safe_eq(credentials, settings.auth_token):
        return

    if scheme == "basic":
        try:
            decoded = base64.b64decode(credentials).decode()
            username, _, password = decoded.partition(":")
            expected_user = settings.auth_username or "admin"
            if _safe_eq(username, expected_user) and _safe_eq(password, settings.auth_password):
                return
            if _safe_eq(password, settings.auth_token):
                return
        except Exception:
            pass

    logger.warning("auth rejected path=%s", request.url.path)
    raise HTTPException(status_code=401, headers={"WWW-Authenticate": _WWW_AUTH})
