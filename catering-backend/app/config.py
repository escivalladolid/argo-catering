from pydantic import model_validator
from pydantic_settings import BaseSettings
from functools import lru_cache
import os


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/catering_db"
    JWT_SECRET_KEY: str = "super-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_MINUTES: int = 1440
    JWT_ISSUER: str = "catering-api"
    JWT_AUDIENCE: str = "catering-app"
    # Optional: the tenant that the public customer portal operates against.
    # When unset, the public portal resolves the single organization present
    # in the database (fail-closed if there is more than one). The org is
    # always resolved server-side and never trusted from the client.
    PUBLIC_ORGANIZATION_ID: str | None = None
    PUBLIC_BASE_URL: str = "http://127.0.0.1:8001"

    # SMTP settings for step-up email verification (sensitive admin actions).
    # SMTP_PASSWORD must be set in the environment / secrets store, never
    # committed to the repository.
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_NAME: str = "ARGO Catering"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @model_validator(mode="after")
    def _harden_jwt_secret(self):
        secret = self.JWT_SECRET_KEY
        if (
            not secret
            or secret == "super-secret-key-change-in-production"
            or len(secret) < 32
        ):
            raise ValueError(
                "JWT_SECRET_KEY must be a strong random secret of at least 32 characters. "
                "Set it in the .env file before starting the server."
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
