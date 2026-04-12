import logging

from .graph import build_literature_search_graph, graph
from .state import PaperRecord, PaperSearchState
from .storage import load_papers, save_papers, update_status

logger = logging.getLogger(__name__)

__all__ = [
    "search", "graph", "build_literature_search_graph",
    "PaperRecord", "PaperSearchState",
    "load_papers", "save_papers", "update_status",
]


def search(keywords: list[str], max_results_per_source: int = 20) -> list[PaperRecord]:
    """Search arXiv → Semantic Scholar → OpenAlex and return merged results."""
    result = graph.invoke({
        "keywords": keywords,
        "max_results_per_source": max_results_per_source,
        "papers": [],
        "errors": [],
    })

    for err in result.get("errors", []):
        logger.warning("%s", err)

    return result["papers"]
