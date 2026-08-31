"""
RAG Database Migration Runner
==============================
Applies the RAG module's additive migrations to the PostgreSQL database.

Usage:
    python src/ertmac/rag/database/migrate.py

Environment:
    DATABASE_URL — existing PostgreSQL connection string (from root .env)

This script is ADDITIVE ONLY — it never modifies or drops existing tables.
"""

import logging
import os
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("ertmac.rag.migrate")

MIGRATIONS_DIR = Path(__file__).parent / "migrations"
MIGRATION_FILES = sorted(MIGRATIONS_DIR.glob("*.sql"))


def run_migrations(database_url: str = None) -> bool:
    """
    Applies all RAG migrations in order.

    Args:
        database_url: PostgreSQL connection string. Defaults to DATABASE_URL env var.

    Returns:
        True if all migrations applied successfully, False otherwise.
    """
    url = database_url or os.getenv("DATABASE_URL", "")
    if not url:
        logger.error(
            "DATABASE_URL is not set. Cannot run migrations. "
            "Set DATABASE_URL in your .env file."
        )
        return False

    try:
        import psycopg2
    except ImportError:
        logger.error(
            "psycopg2 is not installed. Run: pip install psycopg2-binary"
        )
        return False

    try:
        conn = psycopg2.connect(url)
        conn.autocommit = False
        logger.info("Connected to PostgreSQL")
    except Exception as e:
        logger.error(f"Failed to connect to PostgreSQL: {e}")
        return False

    success = True
    applied_count = 0

    for migration_file in MIGRATION_FILES:
        logger.info(f"Applying migration: {migration_file.name}")
        try:
            sql = migration_file.read_text(encoding="utf-8")
            with conn.cursor() as cur:
                cur.execute(sql)
            conn.commit()
            logger.info(f"✓ {migration_file.name} applied successfully")
            applied_count += 1
        except Exception as e:
            conn.rollback()
            logger.error(f"✗ Migration {migration_file.name} failed: {e}")
            success = False
            break

    conn.close()

    if success:
        logger.info(
            f"\n{'='*60}\n"
            f"RAG Migration Complete\n"
            f"Applied: {applied_count} migration(s)\n"
            f"Status: SUCCESS\n"
            f"{'='*60}"
        )
    else:
        logger.error(
            f"\n{'='*60}\n"
            f"RAG Migration FAILED\n"
            f"Applied: {applied_count} migration(s) before failure\n"
            f"{'='*60}"
        )

    return success


if __name__ == "__main__":
    # Load .env from repo root
    try:
        from dotenv import load_dotenv
        repo_root = Path(__file__).resolve().parent.parent.parent.parent.parent
        env_file = repo_root / ".env"
        if env_file.exists():
            load_dotenv(env_file)
            logger.info(f"Loaded .env from {env_file}")
    except ImportError:
        pass

    ok = run_migrations()
    sys.exit(0 if ok else 1)
