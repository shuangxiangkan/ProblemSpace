import logging

from .graph import build_literature_search_graph, _get_graph
from .state import PaperRecord, PaperSearchState
from utils import create_results_run_dir

logger = logging.getLogger(__name__)

__all__ = [
    "search", "build_literature_search_graph",
    "PaperRecord", "PaperSearchState",
]


def search(
    keywords: list[str],
    max_results_per_source: int = 20,
    query_description: str | None = None,
) -> list[PaperRecord]:
    """Search, dedup, filter, and return literature results."""
    resolved_query = query_description or " ".join(keywords)
    results_run_dir = create_results_run_dir(resolved_query, keywords)

    result = _get_graph().invoke({
        "query_description": resolved_query,
        "results_save_dir": str(results_run_dir),
        "keywords": keywords,
        "max_results_per_source": max_results_per_source,
        "raw_papers": [],
        "papers": [],
        "errors": [],
    })

    for err in result.get("errors", []):
        logger.warning("%s", err)

    return result["papers"]
