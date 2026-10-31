from decimal import Decimal
from pathlib import Path
from typing import Literal, Self

from pydantic import Field, SecretStr, ValidationError, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url


class ConfigurationError(RuntimeError):
    """Safe configuration failure, never containing original environment values."""


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="AI_", env_file=".env", extra="ignore", populate_by_name=True
    )

    mode: Literal["standalone", "integrated"] = "standalone"
    bind_host: str = "127.0.0.1"
    port: int = Field(default=8090, ge=1024, le=65535)
    private_container: bool = False
    provider_mode: Literal["fake", "live"] = "fake"
    database_url: SecretStr = Field(
        default=SecretStr("sqlite+pysqlite:///.local/ai.db"), repr=False
    )
    migration_database_url: SecretStr | None = Field(default=None, repr=False)
    openrouter_api: SecretStr | None = Field(
        default=None, validation_alias="OPENROUTER_API", repr=False
    )
    live_enabled: bool = False
    live_model: Literal["openrouter/free"] = "openrouter/free"
    live_request_usd: Decimal = Field(default=Decimal("0"), ge=0, le=1)
    live_daily_usd: Decimal = Field(default=Decimal("0"), ge=0, le=10)
    live_daily_requests: int = Field(default=10, ge=1, le=100)
    provider_timeout_seconds: float = Field(default=5, gt=0, le=8)
    request_deadline_seconds: float = Field(default=8, gt=0, le=30)
    qa_enabled: bool = False
    qa_embedding_mode: Literal["fake", "local"] = "fake"
    qa_model_bundle: Path | None = None

    @model_validator(mode="after")
    def boundaries(self) -> Self:
        if self.qa_enabled:
            if self.private_container or self.bind_host not in {"127.0.0.1", "::1", "localhost"}:
                raise ValueError("Standalone QA requires a host loopback listener")
            if make_url(self.database_url.get_secret_value()).drivername != "postgresql+psycopg":
                raise ValueError("QA requires separate AI PostgreSQL")
            if self.qa_embedding_mode == "local" and self.qa_model_bundle is None:
                raise ValueError("Local QA embeddings require a pinned bundle")
        if self.mode != "standalone":
            raise ValueError("Integrated authentication is not implemented in P03")
        if self.bind_host not in {"127.0.0.1", "::1", "localhost"} and not (
            self.private_container and self.bind_host == "0.0.0.0"
        ):
            raise ValueError("Standalone requires loopback or explicit private-container mode")
        for secret in (self.database_url, self.migration_database_url):
            if secret is None:
                continue
            url = make_url(secret.get_secret_value())
            if url.drivername not in {"sqlite+pysqlite", "postgresql+psycopg"}:
                raise ValueError("Only AI SQLite or PostgreSQL drivers are supported")
            if url.drivername == "postgresql+psycopg" and url.database not in {
                "vmarket_ai",
                "vmarket_ai_test",
            }:
                raise ValueError(
                    "Database must be dedicated to AI, never V-Market business storage"
                )
        if self.provider_mode == "live":
            if not self.live_enabled or not self.openrouter_api:
                raise ValueError("Live mode requires explicit opt-in and an API key")
            if not self.openrouter_api.get_secret_value().strip():
                raise ValueError("Live API key must not be empty")
            if not 0 < self.live_request_usd <= self.live_daily_usd:
                raise ValueError("Live mode requires finite positive request and daily budgets")
        elif self.live_enabled:
            raise ValueError("Live opt-in must match provider_mode=live")
        return self


def load_settings() -> Settings:
    try:
        return Settings()
    except (ValidationError, ValueError, OSError):
        raise ConfigurationError(
            "Invalid AI configuration; check the documented AI_* settings"
        ) from None
