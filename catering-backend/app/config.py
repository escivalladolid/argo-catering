from pydantic import model_validator
from pydantic_settings import BaseSettings
from functools import lru_cache
import os


class Settings(BaseSettings):
    # Database - MUST be set via environment variable in production
    DATABASE_URL: str

    # JWT - MUST be set via environment variable in production (min 32 chars)
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_MINUTES: int = 1440
    JWT_ISSUER: str = "catering-api"
    JWT_AUDIENCE: str = "catering-app"

    # Public portal organization - MUST be set in production if multiple orgs
    PUBLIC_ORGANIZATION_ID: str | None = None

    # Public base URL for email links - MUST be set in production
    PUBLIC_BASE_URL: str

    # CORS allowed origins - comma-separated list
    CORS_ALLOWED_ORIGINS: str = "*"

    # SMTP for all service emails (Gmail address + App Password in production).
    # If these are left unset, emails are skipped with a log warning.
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_NAME: str = "ARGO Catering"

    # Brevo HTTPS email API — works on Render free tier (which blocks SMTP
    # egress). When set, it takes priority over SMTP for all service emails.
    BREVO_API_KEY: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

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

    @model_validator(mode="after")
    def _validate_public_base_url(self):
        if self.PUBLIC_BASE_URL and self.PUBLIC_BASE_URL.startswith("http://127.0.0.1"):
            raise ValueError(
                "PUBLIC_BASE_URL must not be localhost in production. "
                "Set it to your deployed frontend URL (e.g., https://your-app.vercel.app)."
            )
        return self

    @model_validator(mode="after")
    def _validate_database_url(self):
        if self.DATABASE_URL and "localhost" in self.DATABASE_URL:
            raise ValueError(
                "DATABASE_URL must not use localhost in production. "
                "Use the Render PostgreSQL connection string."
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()