from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = (
        "postgresql+psycopg://service_desk:service_desk@localhost:5432/service_desk"
    )
    jwt_secret: str = "local-dev-secret-change-me-32-bytes-minimum"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    admin_username: str = "admin"
    admin_password: str = "Admin123!"
    admin_email: str = "admin@example.com"


@lru_cache
def get_settings() -> Settings:
    return Settings()
