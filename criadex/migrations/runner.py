import asyncio
import hashlib
import logging
import re
from pathlib import Path
from typing import List

from aiomysql import Pool

from .models import MigrationFile

logger = logging.getLogger(__name__)


class MigrationRunner:
    """
    Apply versioned SQL migrations tracked in schema_migrations.

    Mirrors the Criabot migration runner but uses Criadex's aiomysql pool.
    """

    MIGRATIONS_TABLE = "schema_migrations"
    MIGRATIONS_DIR = Path(__file__).parent.parent.parent / "migrations"

    def __init__(self, pool: Pool):
        self._pool = pool
        self.migrations_dir = self.MIGRATIONS_DIR

    async def _migrations_table_exists(self, cursor) -> bool:
        await cursor.execute(
            """
            SELECT COUNT(*)
            FROM information_schema.tables
            WHERE table_schema = DATABASE()
              AND table_name = %s
            """,
            (self.MIGRATIONS_TABLE,),
        )
        row = await cursor.fetchone()
        return bool(row and row[0] > 0)

    async def initialize(self) -> None:
        """Create the migrations tracking table if it does not exist."""
        async with self._pool.acquire() as conn:
            async with conn.cursor() as cursor:
                if await self._migrations_table_exists(cursor):
                    return

                await cursor.execute(f"""
                    CREATE TABLE `{self.MIGRATIONS_TABLE}` (
                        `id` INT AUTO_INCREMENT PRIMARY KEY,
                        `migration_name` VARCHAR(255) NOT NULL UNIQUE,
                        `applied_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        `checksum` VARCHAR(64) NULL,
                        INDEX `idx_migration_name` (`migration_name`)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """)
        logger.info("Initialized migrations tracking table: %s", self.MIGRATIONS_TABLE)

    def _get_migration_files(self) -> List[MigrationFile]:
        """Scan migrations directory and return sorted migration files."""
        migrations: List[MigrationFile] = []

        if not self.migrations_dir.exists():
            logger.warning("Migrations directory not found: %s", self.migrations_dir)
            return migrations

        pattern = re.compile(r"^(\d+)_(.+)\.sql$")

        for file_path in sorted(self.migrations_dir.glob("*.sql")):
            match = pattern.match(file_path.name)
            if match:
                migrations.append(MigrationFile(
                    name=match.group(2),
                    path=str(file_path),
                    version=int(match.group(1)),
                ))
            else:
                logger.warning("Skipping migration file with invalid name: %s", file_path.name)

        return sorted(migrations)

    @staticmethod
    def _split_sql_statements(sql_content: str) -> List[str]:
        """Split SQL file into executable statements."""
        statements: List[str] = []
        for chunk in sql_content.split(";"):
            statement = chunk.strip()
            if not statement:
                continue
            if all(line.strip().startswith("--") or not line.strip() for line in statement.splitlines()):
                continue
            statements.append(statement)
        return statements

    async def _calculate_checksum(self, file_path: str) -> str:
        def _read_and_hash() -> str:
            with open(file_path, "rb") as file_handle:
                return hashlib.sha256(file_handle.read()).hexdigest()

        return await asyncio.to_thread(_read_and_hash)

    async def _get_applied_migrations(self) -> List[str]:
        async with self._pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    f"SELECT `migration_name` FROM `{self.MIGRATIONS_TABLE}`"
                )
                rows = await cursor.fetchall()
                return [row[0] for row in rows]

    async def _apply_migration(self, migration: MigrationFile) -> None:
        logger.info("Applying migration: %s (version %s)", migration.name, migration.version)

        def _read_sql() -> str:
            with open(migration.path, "r", encoding="utf-8") as file_handle:
                return file_handle.read()

        sql_content = await asyncio.to_thread(_read_sql)
        checksum = await self._calculate_checksum(migration.path)
        statements = self._split_sql_statements(sql_content)

        async with self._pool.acquire() as conn:
            await conn.autocommit(False)
            try:
                async with conn.cursor() as cursor:
                    for statement in statements:
                        await cursor.execute(statement)
                    await cursor.execute(
                        f"""
                        INSERT INTO `{self.MIGRATIONS_TABLE}`
                            (`migration_name`, `applied_at`, `checksum`)
                        VALUES (%s, NOW(), %s)
                        """,
                        (migration.name, checksum),
                    )
                await conn.commit()
            except Exception:
                await conn.rollback()
                raise
            finally:
                await conn.autocommit(True)

        logger.info("Successfully applied migration: %s", migration.name)

    async def run_pending(self) -> List[str]:
        """Run all pending migrations and return applied migration names."""
        await self.initialize()

        applied_migrations = set(await self._get_applied_migrations())
        migration_files = self._get_migration_files()
        applied_names: List[str] = []

        for migration in migration_files:
            if migration.name in applied_migrations:
                logger.debug("Skipping already applied migration: %s", migration.name)
                continue

            await self._apply_migration(migration)
            applied_names.append(migration.name)

        if applied_names:
            logger.info(
                "Applied %s migration(s): %s",
                len(applied_names),
                ", ".join(applied_names),
            )
        else:
            logger.info("No pending migrations to apply")

        return applied_names

    async def status(self) -> dict:
        """Return pending and applied migration names."""
        await self.initialize()

        applied_migrations = set(await self._get_applied_migrations())
        migration_files = self._get_migration_files()

        pending = []
        applied = []

        for migration in migration_files:
            if migration.name in applied_migrations:
                applied.append(migration.name)
            else:
                pending.append(migration.name)

        return {
            "pending": pending,
            "applied": applied,
            "total": len(migration_files),
        }
