from alembic import context
from sqlalchemy import text

from vmarket_ai.database import Base, create_db_engine
from vmarket_ai.ingestion import models as _document_models  # noqa: F401
from vmarket_ai.settings import load_settings

config = context.config
settings = config.attributes.get("settings") or load_settings()
engine = create_db_engine(settings, migration=True)

with engine.connect() as connection:
    postgres = connection.dialect.name == "postgresql"
    if postgres:
        connection.execute(text("CREATE SCHEMA IF NOT EXISTS ai"))
        connection.commit()
    context.configure(
        connection=connection,
        target_metadata=Base.metadata,
        version_table_schema="ai" if postgres else None,
        include_schemas=postgres,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()
engine.dispose()
