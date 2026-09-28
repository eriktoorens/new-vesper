"""Connections, migrations and transactions."""

import re
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from importlib import resources
from pathlib import Path

_MIGRATION_NAME = re.compile(r"(\d{4})_[a-z0-9_]+\.sql")


def connect(path: str | Path = ":memory:") -> sqlite3.Connection:
    """Open a connection in autocommit mode; use ``atomic`` for transactions."""
    conn = sqlite3.connect(path, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    if str(path) != ":memory:":
        conn.execute("PRAGMA journal_mode = WAL")
    return conn


@contextmanager
def atomic(conn: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    """Run a block in a transaction (a savepoint when nested). All or nothing."""
    # SQLite resolves a repeated savepoint name to the innermost one.
    conn.execute("SAVEPOINT atomic")
    try:
        yield conn
    except BaseException:
        conn.execute("ROLLBACK TO atomic")
        conn.execute("RELEASE atomic")
        raise
    conn.execute("RELEASE atomic")


def available_migrations() -> list[tuple[int, str, str]]:
    """Return (version, filename, sql) for every packaged migration, in order."""
    found = []
    for entry in resources.files("new_vesper.state.migrations").iterdir():
        match = _MIGRATION_NAME.fullmatch(entry.name)
        if match:
            found.append((int(match.group(1)), entry.name, entry.read_text(encoding="utf-8")))
    found.sort()
    versions = [version for version, _, _ in found]
    if versions != list(range(1, len(versions) + 1)):
        raise RuntimeError(f"migrations must be numbered 1..n without gaps, got {versions}")
    return found


def applied_versions(conn: sqlite3.Connection) -> set[int]:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations ("
        " version INTEGER PRIMARY KEY, name TEXT NOT NULL,"
        " applied_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')))"
    )
    return {row[0] for row in conn.execute("SELECT version FROM schema_migrations")}


def migrate(conn: sqlite3.Connection) -> list[int]:
    """Apply pending migrations, each in its own transaction. Returns versions applied."""
    done = applied_versions(conn)
    applied = []
    for version, name, sql in available_migrations():
        if version in done:
            continue
        try:
            conn.executescript(f"BEGIN;\n{sql}\n;")
            conn.execute(
                "INSERT INTO schema_migrations (version, name) VALUES (?, ?)", (version, name)
            )
            conn.execute("COMMIT")
        except BaseException:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            raise
        applied.append(version)
    return applied


def open_database(path: str | Path = ":memory:") -> sqlite3.Connection:
    """Connect and bring the schema up to date."""
    conn = connect(path)
    migrate(conn)
    return conn
