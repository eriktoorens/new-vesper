"""Input checks shared by repositories. Everything here raises StateError."""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager

from new_vesper.rules.character import validate_id
from new_vesper.rules.errors import RulesError
from new_vesper.state.errors import NotFoundError, StateError


@contextmanager
def as_state_error() -> Iterator[None]:
    """Report rules violations and constraint failures as StateError."""
    try:
        yield
    except RulesError as exc:
        raise StateError(str(exc)) from exc
    except sqlite3.IntegrityError as exc:
        raise StateError(f"rejected by the database: {exc}") from exc


def slug(value: object, name: str) -> str:
    with as_state_error():
        return validate_id(value, name)


def text(value: object, name: str, max_length: int, *, allow_empty: bool = False) -> str:
    """A bounded string. Stored as data only; never interpreted."""
    if not isinstance(value, str):
        raise StateError(f"{name} must be a string, got {type(value).__name__}")
    if not value.strip() and not allow_empty:
        raise StateError(f"{name} must not be empty")
    if len(value) > max_length:
        raise StateError(f"{name} must be at most {max_length} characters")
    if "\x00" in value:
        raise StateError(f"{name} must not contain NUL characters")
    return value


def row_id(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise StateError(f"{name} must be a positive integer id")
    return value


def flag(value: object, name: str) -> bool:
    if not isinstance(value, bool):
        raise StateError(f"{name} must be true or false")
    return value


def require_row[T](row: T | None, what: str, key: object) -> T:
    if row is None:
        raise NotFoundError(f"no {what} {str(key)[:64]!r}")
    return row
