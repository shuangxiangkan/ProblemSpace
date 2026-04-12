import logging

from langgraph.graph import END, StateGraph

from .nodes import search_arxiv, search_openalex, search_semantic_scholar
from .state import PaperSearchState
from .storage import save_papers

logger = logging.getLogger(__name__)


def _save_to_db(state: PaperSearchState) -> dict:
    query = " ".join(state["keywords"])
    total = len(state["papers"])
    logger.info("[DB] Saving %d papers (query: '%s') ...", total, query)
    inserted, skipped = save_papers(state["papers"], search_query=query)
    logger.info("[DB] Done — inserted=%d, skipped(dup)=%d.", inserted, skipped)
    return {}


def build_graph():
    builder = StateGraph(PaperSearchState)

    builder.add_node("arxiv", search_arxiv)
    builder.add_node("semantic_scholar", search_semantic_scholar)
    builder.add_node("openalex", search_openalex)
    builder.add_node("save_to_db", _save_to_db)

    builder.set_entry_point("arxiv")
    builder.add_edge("arxiv", "semantic_scholar")
    builder.add_edge("semantic_scholar", "openalex")
    builder.add_edge("openalex", "save_to_db")
    builder.add_edge("save_to_db", END)

    return builder.compile()


# Alias for use as a subgraph in the main research pipeline
build_literature_search_graph = build_graph

graph = build_graph()
