"""Database package — paper storage, path generation, graph nodes."""

from database.store import (
    DEFAULT_DB,
    DB_SAVE_DIR,
    get_connection,
    load_papers,
    make_db_path,
    save_papers,
    update_status,
)

# nodes imported lazily to avoid circular import with literature_search


def __getattr__(name: str):
    if name == "save_to_db":
        from database import ops
        return getattr(ops, name)
    raise AttributeError(f"module 'database' has no attribute {name!r}")


__all__ = [
    "DEFAULT_DB",
    "DB_SAVE_DIR",
    "get_connection",
    "load_papers",
    "make_db_path",
    "save_papers",
    "save_to_db",
    "update_status",
]
