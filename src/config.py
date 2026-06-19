from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    palace_path: str = "/palace"
    kg_path: str | None = None
    auth_token: str | None = None
    auth_username: str = "admin"
    auth_password: str | None = None

    model_config = SettingsConfigDict(env_prefix="MEMPALACE_")

    @property
    def resolved_kg_path(self) -> str:
        return self.kg_path or f"{self.palace_path}/knowledge_graph.sqlite3"
