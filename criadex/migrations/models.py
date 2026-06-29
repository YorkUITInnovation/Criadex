from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class MigrationRecord(BaseModel):
    """Represents a migration record in the database."""

    id: Optional[int] = None
    migration_name: str
    applied_at: datetime
    checksum: Optional[str] = None


class MigrationFile:
    """Represents a migration SQL file."""

    def __init__(self, name: str, path: str, version: int):
        self.name = name
        self.path = path
        self.version = version

    def __lt__(self, other):
        return self.version < other.version

    def __repr__(self):
        return f"MigrationFile(name={self.name}, version={self.version})"
