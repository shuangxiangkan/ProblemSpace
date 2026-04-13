import hashlib
import logging

from langgraph.graph import END, START, StateGraph

from .nodes import search_arxiv, search_openalex, search_semantic_scholar
from .state import PaperSearchState
from .storage import save_papers

logger = logging.getLogger(__name__)


def _paper_dedup_key(paper: dict) -> str:
    doi = (paper.get("doi") or "").strip().lower()
    if doi:
        return doi
    return hashlib.sha1(paper.get("title", "").strip().lower().encode()).hexdigest()


def _dedup_papers(state: PaperSearchState) -> dict:
    deduped: list[dict] = []
    seen: set[str] = set()

    for paper in state["raw_papers"]:
        key = _paper_dedup_key(paper)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(paper)

    removed = len(state["raw_papers"]) - len(deduped)
    if removed:
        logger.info("[Dedup] Removed %d cross-source duplicates.", removed)

    return {"papers": deduped}


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
    builder.add_node("dedup_papers", _dedup_papers)
    builder.add_node("save_to_db", _save_to_db)

    builder.add_edge(START, "arxiv")
    builder.add_edge(START, "semantic_scholar")
    builder.add_edge(START, "openalex")
    builder.add_edge("arxiv", "dedup_papers")
    builder.add_edge("semantic_scholar", "dedup_papers")
    builder.add_edge("openalex", "dedup_papers")
    builder.add_edge("dedup_papers", "save_to_db")
    builder.add_edge("save_to_db", END)

    return builder.compile()


# Alias for use as a subgraph in the main research pipeline
build_literature_search_graph = build_graph

graph = build_graph()
