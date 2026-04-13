from langgraph.graph import END, START, StateGraph

from .nodes import (
    search_arxiv,
    search_openalex,
    search_semantic_scholar,
)
from database.ops import dedup_papers, save_to_db
from .state import PaperSearchState


def build_literature_search_graph():
    builder = StateGraph(PaperSearchState)

    builder.add_node("arxiv", search_arxiv)
    builder.add_node("semantic_scholar", search_semantic_scholar)
    builder.add_node("openalex", search_openalex)
    builder.add_node("dedup_papers", dedup_papers)
    builder.add_node("save_to_db", save_to_db)

    builder.add_edge(START, "arxiv")
    builder.add_edge(START, "semantic_scholar")
    builder.add_edge(START, "openalex")
    builder.add_edge("arxiv", "dedup_papers")
    builder.add_edge("semantic_scholar", "dedup_papers")
    builder.add_edge("openalex", "dedup_papers")
    builder.add_edge("dedup_papers", "save_to_db")
    builder.add_edge("save_to_db", END)

    return builder.compile()


def _get_graph():
    """Lazily compiled graph singleton."""
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_literature_search_graph()
    return _compiled_graph


_compiled_graph = None
