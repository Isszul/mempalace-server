from functools import lru_cache

from .config import Settings
from .storage import KGStore, PalaceStore


@lru_cache
def _settings() -> Settings:
    return Settings()


def get_palace_store() -> PalaceStore:
    s = _settings()
    return PalaceStore(path=s.palace_path)


def get_kg_store() -> KGStore:
    s = _settings()
    return KGStore(path=s.resolved_kg_path)
