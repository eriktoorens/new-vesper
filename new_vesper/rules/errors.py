"""Validation errors raised by the rules engine."""

from enum import Enum


class RulesError(ValueError):
    """A request broke the rules. The message is safe to show the DM model."""


def require_int(value: object, name: str) -> int:
    """Return ``value`` if it is a real int (not a bool, float or string)."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise RulesError(f"{name} must be an integer, got {type(value).__name__}")
    return value


def require_range(value: object, name: str, low: int, high: int) -> int:
    """Return ``value`` if it is an int within ``low..high`` inclusive."""
    number = require_int(value, name)
    if not low <= number <= high:
        raise RulesError(f"{name} must be between {low} and {high}, got {number}")
    return number


def parse_enum[E: Enum](enum_type: type[E], value: object, name: str) -> E:
    """Parse an enum member from itself or its exact string value.

    Only exact matches are accepted (after trimming and lower-casing), so a
    string carrying extra text is rejected rather than guessed at.
    """
    if isinstance(value, enum_type):
        return value
    if not isinstance(value, str):
        raise RulesError(f"{name} must be a string, got {type(value).__name__}")
    key = value.strip().lower()
    for member in enum_type:
        if member.value == key:
            return member
    allowed = ", ".join(str(member.value) for member in enum_type)
    raise RulesError(f"unknown {name} {value[:40]!r}; allowed: {allowed}")
