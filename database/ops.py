"""Graph-node functions for database-related operations."""

from __future__ import annotations

import logging

from literature_search.state import PaperSearchState

logger = logging.getLogger(__name__)


def save_to_db(state: PaperSearchState) -> dict:
    """Persist deduplicated papers to a per-run SQLite database."""
    from database.store import save_papers
    from database.store import make_db_path

    db_path = make_db_path(state["keywords"])
    query = " ".join(state["keywords"])
    total = len(state["papers"])
    logger.info("[DB] Saving %d papers to %s ...", total, db_path)
    inserted, skipped = save_papers(state["papers"], search_query=query, db_path=db_path)
    logger.info("[DB] Done — inserted=%d, skipped(dup)=%d.", inserted, skipped)
    return {}
