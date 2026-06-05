import os
import uuid

import aiomysql
import pytest

from app.core import config
from criadex.migrations.runner import MigrationRunner


async def _create_test_pool() -> aiomysql.Pool:
    host = os.environ.get("MYSQL_HOST", "127.0.0.1")
    db_name = (
        "criadex_test"
        if os.environ.get("APP_API_MODE", "TESTING") == "TESTING"
        else os.environ.get("MYSQL_DATABASE", "criadex")
    )
    return await aiomysql.create_pool(
        host=host,
        port=config.MYSQL_CREDENTIALS.port,
        user=config.MYSQL_CREDENTIALS.username,
        password=config.MYSQL_CREDENTIALS.password,
        db=db_name,
        autocommit=True,
        minsize=1,
        maxsize=2,
    )


@pytest.mark.asyncio
async def test_migration_runner_applies_pending_migration(db_connection) -> None:
    pool = await _create_test_pool()

    try:
        runner = MigrationRunner(pool)
        first_run = await runner.run_pending()
        assert first_run == [] or "groups_drop_model_foreign_keys" in first_run

        second_run = await runner.run_pending()
        assert second_run == []

        status = await runner.status()
        assert "groups_drop_model_foreign_keys" in status["applied"]
        assert status["pending"] == []
    finally:
        pool.close()
        await pool.wait_closed()


@pytest.mark.asyncio
async def test_migration_runner_applies_custom_sql_file(db_connection, tmp_path, monkeypatch) -> None:
    migration_name = f"test_table_{uuid.uuid4().hex[:8]}"
    migration_dir = tmp_path / "migrations"
    migration_dir.mkdir()
    (migration_dir / f"099_{migration_name}.sql").write_text(
        f"CREATE TABLE IF NOT EXISTS `{migration_name}` ("
        f"`id` INT AUTO_INCREMENT PRIMARY KEY"
        f") ENGINE=InnoDB;",
        encoding="utf-8",
    )

    pool = await _create_test_pool()

    monkeypatch.setattr(MigrationRunner, "MIGRATIONS_DIR", migration_dir)

    try:
        runner = MigrationRunner(pool)
        applied = await runner.run_pending()
        assert migration_name in applied

        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(f"DROP TABLE IF EXISTS `{migration_name}`")
    finally:
        pool.close()
        await pool.wait_closed()
