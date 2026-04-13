import logging

from .graph import build_literature_search_graph, _get_graph
from .state import PaperRecord, PaperSearchState

logger = logging.getLogger(__name__)

__all__ = [
    "search", "build_literature_search_graph",
    "PaperRecord", "PaperSearchState",
]


def search(keywords: list[str], max_results_per_source: int = 20) -> list[PaperRecord]:
    """Search arXiv → Semantic Scholar → OpenAlex and return merged results."""
    result = _get_graph().invoke({
        "keywords": keywords,
        "max_results_per_source": max_results_per_source,
        "raw_papers": [],
        "papers": [],
        "errors": [],
    })

    for err in result.get("errors", []):
        logger.warning("%s", err)

    return result["papers"]
