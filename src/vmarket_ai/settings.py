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
    provider_mode: Literal["fake", "live", "local"] = "fake"
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
    mapping_enabled: bool = False
    agent_enabled: bool = False
    runs_enabled: bool = False
    gateway_public_keys: dict[str, str] = Field(default_factory=dict, repr=False)
    qa_embedding_mode: Literal["fake", "local"] = "fake"
    qa_model_bundle: Path | None = None
    ollama_model: Literal["qwen3.5:4b-q4_K_M", "qwen3.5:9b-q4_K_M"] = "qwen3.5:4b-q4_K_M"
    ollama_timeout_seconds: float = Field(default=25, gt=0, le=30)
    ollama_context: int = Field(default=4096, ge=2048, le=8192)

    @model_validator(mode="after")
    def boundaries(self) -> Self:
        if self.runs_enabled and (
            self.mode != "integrated"
            or not self.agent_enabled
            or make_url(self.database_url.get_secret_value()).drivername != "postgresql+psycopg"
        ):
            raise ValueError(
                "Durable runs require the integrated signed gateway and dedicated AI PostgreSQL"
            )
        if self.provider_mode == "local" and self.private_container:
            raise ValueError("Local Ollama mode requires host loopback runtime")
        if self.mapping_enabled and self.provider_mode == "live":
            raise ValueError("P08 mapping supports fake/local only; external calls disabled")
        if self.qa_enabled or self.mapping_enabled:
            if self.private_container or self.bind_host not in {"127.0.0.1", "::1", "localhost"}:
                raise ValueError("Standalone QA requires a host loopback listener")
            if make_url(self.database_url.get_secret_value()).drivername != "postgresql+psycopg":
                raise ValueError("QA requires separate AI PostgreSQL")
            if self.qa_embedding_mode == "local" and self.qa_model_bundle is None:
                raise ValueError("Local QA embeddings require a pinned bundle")
        if self.agent_enabled and self.provider_mode == "live":
            raise ValueError("P09 agent supports fake/local only")
        if self.agent_enabled and (
            self.private_container or self.bind_host not in {"127.0.0.1", "localhost", "::1"}
        ):
            raise ValueError("P09 agent requires a host loopback listener")
        if (
            self.agent_enabled
            and self.qa_embedding_mode == "local"
            and self.qa_model_bundle is None
        ):
            raise ValueError("Local knowledge embedding bundle required")
        if self.mode == "integrated":
            import base64
            import re

            if not self.agent_enabled or self.private_container:
                raise ValueError("Integrated mode requires the signed host-loopback gateway")
            if not 1 <= len(self.gateway_public_keys) <= 3 or any(
                not re.fullmatch(r"[A-Za-z0-9_-]{1,32}", kid)
                or len(base64.b64decode(key, validate=True)) != 32
                for kid, key in self.gateway_public_keys.items()
            ):
                raise ValueError("Trusted Ed25519 public keys required")
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
