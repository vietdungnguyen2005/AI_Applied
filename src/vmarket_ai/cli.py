import argparse
import asyncio
import json
import sys
from pathlib import Path

import uvicorn
from alembic import command
from alembic.config import Config
from sqlalchemy.exc import SQLAlchemyError

from vmarket_ai.contracts import ChatRequest, EmbeddingRequest, Message
from vmarket_ai.observability import configure_logging
from vmarket_ai.providers.fake import FakeChatModel, FakeEmbeddingProvider
from vmarket_ai.settings import ConfigurationError, load_settings


async def fake_check() -> None:
    chat = await FakeChatModel().complete(
        ChatRequest(messages=(Message(role="user", content="demo"),))
    )
    embedding = await FakeEmbeddingProvider().embed(EmbeddingRequest(texts=("synthetic demo",)))
    print(
        json.dumps(
            {
                "provider_mode": "fake",
                "chat": chat.text,
                "embedding_dimensions": embedding.dimensions,
                "external_calls": 0,
            }
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Local AI service and isolated storage maintenance"
    )
    parser.add_argument("action", choices=["serve", "migrate", "fake-check", "runs-maintain"])
    args = parser.parse_args()
    configure_logging()
    try:
        settings = load_settings()
        if args.action == "migrate":
            path = Path.cwd() / "alembic.ini"
            if not path.is_file():
                raise ConfigurationError("Run migrations from the repository or container app root")
            config = Config(str(path))
            config.attributes["settings"] = settings
            command.upgrade(config, "head")
            print('{"event":"migration_complete","scope":"AI-owned database"}')
        elif args.action == "fake-check":
            asyncio.run(fake_check())
        elif args.action == "runs-maintain":
            from vmarket_ai.database import create_db_engine
            from vmarket_ai.runs.store import RunStore

            if settings.migration_database_url is None:
                raise ConfigurationError(
                    "Run maintenance requires the explicit AI owner credential"
                )
            engine = create_db_engine(settings, migration=True)
            try:
                print(
                    json.dumps(
                        {
                            "event": "runs_maintenance",
                            "scope": "AI-owned database",
                            **RunStore(engine).maintain(),
                        }
                    )
                )
            finally:
                engine.dispose()
        else:
            uvicorn.run(
                "vmarket_ai.app:create_app",
                factory=True,
                host=settings.bind_host,
                port=settings.port,
                access_log=False,
                log_level="warning",
            )
    except (ConfigurationError, SQLAlchemyError):
        print(
            '{"event":"startup_failed","message":"Check AI config/database; values redacted"}',
            file=sys.stderr,
        )
        raise SystemExit(1) from None
