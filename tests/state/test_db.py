import sqlite3
from pathlib import Path

import pytest

from new_vesper.state import db as dbmod
from new_vesper.state.db import atomic, available_migrations, connect, migrate, open_database


def test_migrations_numbered_without_gaps() -> None:
    versions = [v for v, _, _ in available_migrations()]
    assert versions == list(range(1, len(versions) + 1))


def test_migrate_is_idempotent(tmp_path: Path) -> None:
    path = tmp_path / "vesper.db"
    conn = connect(path)
    assert migrate(conn) == [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]
    assert migrate(conn) == []
    conn.close()
    conn = connect(path)
    assert migrate(conn) == []
    assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"


def test_foreign_keys_enforced() -> None:
    conn = open_database()
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO locations (id, region_id, name) VALUES ('x', 'nowhere', 'X')")


def test_failed_migration_rolls_back(monkeypatch: pytest.MonkeyPatch) -> None:
    good = available_migrations()
    bad = (len(good) + 1, "9999_bad.sql", "CREATE TABLE half_done (id INTEGER); SELECT nope();")
    monkeypatch.setattr(dbmod, "available_migrations", lambda: [*good, bad])
    conn = connect()
    with pytest.raises(sqlite3.OperationalError):
        migrate(conn)
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert "half_done" not in tables
    assert "players" in tables  # earlier migrations stay applied
    assert not conn.in_transaction


def test_atomic_rolls_back_and_nests() -> None:
    conn = open_database()
    with atomic(conn):
        conn.execute("INSERT INTO regions (id, name, light) VALUES ('a', 'A', 5)")
        with pytest.raises(RuntimeError), atomic(conn):
            conn.execute("INSERT INTO regions (id, name, light) VALUES ('b', 'B', 5)")
            raise RuntimeError
    with pytest.raises(RuntimeError), atomic(conn):
        conn.execute("INSERT INTO regions (id, name, light) VALUES ('c', 'C', 5)")
        raise RuntimeError
    assert [r[0] for r in conn.execute("SELECT id FROM regions")] == ["a"]
    assert not conn.in_transaction
