import os
import socket
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from pydantic import SecretStr

from vmarket_ai.settings import Settings


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch):
    for key in list(os.environ):
        if key.startswith("AI_") or key == "OPENROUTER_API":
            monkeypatch.delenv(key)
    original = socket.socket.connect

    def connect(sock, address):
        if isinstance(address, tuple) and address[0] not in {"127.0.0.1", "::1", "localhost"}:
            raise AssertionError("External network disabled in tests")
        return original(sock, address)

    monkeypatch.setattr(socket.socket, "connect", connect)


@pytest.fixture
def settings(tmp_path: Path):
    return Settings(
        _env_file=None, database_url=SecretStr(f"sqlite+pysqlite:///{tmp_path / 'ai.db'}")
    )


def migrate(settings: Settings, revision: str = "head") -> None:
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    config.attributes["settings"] = settings
    command.upgrade(config, revision)


@pytest.fixture
def migrated(settings):
    migrate(settings)
    return settings
