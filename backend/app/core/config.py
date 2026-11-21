from typing import Literal

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "BankGuard AI"
    app_env: Literal["development", "test", "production"] = "development"

    database_url: str

    jwt_secret: str = "change-me"
    jwt_algorithm: Literal["HS256"] = "HS256"
    jwt_issuer: str = "bankguard-api"
    jwt_audience: str = "bankguard-web"
    
    access_token_expire_minutes: int = 30

    frontend_origin: str = "http://localhost:3000"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("database_url")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        if value.startswith("postgresql://"):
            return value.replace(
                "postgresql://",
                "postgresql+psycopg://",
                1,
            )

        return value

    @model_validator(mode="after")
    def require_production_jwt_secret(self):
        if self.app_env == "production" and len(self.jwt_secret.encode("utf-8")) < 32:
            raise ValueError("Production JWT secret must contain at least 32 bytes.")
        return self


settings = Settings()
