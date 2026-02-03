"""Database connection and initialization for Openbet."""

import sqlite3
from pathlib import Path
from typing import Optional

from openbet.config import get_settings
from openbet.database.models import ALL_TABLES


class Database:
    """Database connection manager."""

    def __init__(self, db_path: Optional[str] = None):
        """Initialize database connection.

        Args:
            db_path: Path to SQLite database file. If None, uses config value.
        """
        settings = get_settings()
        self.db_path = db_path or settings.database_path

        # Ensure database directory exists
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        self._conn: Optional[sqlite3.Connection] = None

    @property
    def conn(self) -> sqlite3.Connection:
        """Get database connection, creating it if needed."""
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path)
            self._conn.row_factory = sqlite3.Row  # Enable column access by name
        return self._conn

    def initialize_schema(self) -> None:
        """Create all tables and indexes if they don't exist."""
        cursor = self.conn.cursor()
        for sql in ALL_TABLES:
            cursor.execute(sql)
        self.conn.commit()

    def close(self) -> None:
        """Close database connection."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


# Singleton instance
_db: Optional[Database] = None


def get_db() -> Database:
    """Get or create database singleton instance."""
    global _db
    if _db is None:
        _db = Database()
        _db.initialize_schema()
    return _db


def close_db() -> None:
    """Close database singleton instance."""
    global _db
    if _db is not None:
        _db.close()
        _db = None
