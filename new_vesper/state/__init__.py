"""State: SQLite schema, migrations and repositories.

Repositories are plain functions over a ``sqlite3.Connection``. Every
function that writes state also appends to the event log in the same
transaction, so a write without its event can never be committed.
"""
