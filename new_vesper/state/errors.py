"""Errors raised by the state layer."""


class StateError(ValueError):
    """A write was refused. The message is safe to show the DM model."""


class NotFoundError(StateError):
    """The referenced row does not exist."""


class StaleStateError(StateError):
    """The row changed since it was read; re-read and try again."""
