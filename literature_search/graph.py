from langgraph.graph import END, START, StateGraph

from .nodes import (
    dedup_papers,
    download_pdfs,
    filter_papers,
    search_arxiv,
    search_openalex,
    search_semantic_scholar,
)
from database.ops import save_to_db
from .state import PaperSearchState


def build_literature_search_graph():
    builder = StateGraph(PaperSearchState)

    builder.add_node("arxiv", search_arxiv)
    builder.add_node("semantic_scholar", search_semantic_scholar)
    builder.add_node("openalex", search_openalex)
    builder.add_node("dedup_papers", dedup_papers)
    builder.add_node("filter_papers", filter_papers)
    builder.add_node("save_to_db", save_to_db)
    builder.add_node("download_pdfs", download_pdfs)

    builder.add_edge(START, "arxiv")
    builder.add_edge(START, "semantic_scholar")
    builder.add_edge(START, "openalex")
    builder.add_edge("arxiv", "dedup_papers")
    builder.add_edge("semantic_scholar", "dedup_papers")
    builder.add_edge("openalex", "dedup_papers")
    builder.add_edge("dedup_papers", "filter_papers")
    builder.add_edge("filter_papers", "save_to_db")
    builder.add_edge("save_to_db", "download_pdfs")
    builder.add_edge("download_pdfs", END)

    return builder.compile()


def _get_graph():
    """Lazily compiled graph singleton."""
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_literature_search_graph()
    return _compiled_graph


_compiled_graph = None
