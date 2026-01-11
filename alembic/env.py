import os
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

from dotenv import load_dotenv

# Load .env from repo root (bulletproof)
ENV_PATH = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(ENV_PATH)

# Alembic Config object
config = context.config

# Configure logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import Base + models so metadata is populated
from app.db import Base  # noqa: E402
import app.models        # noqa: E402

target_metadata = Base.metadata

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError(f"DATABASE_URL is not set (expected in {ENV_PATH})")

config.set_main_option("sqlalchemy.url", DATABASE_URL)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section) or {},
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
