"""Top-level research pipeline graph.

Combines the problem_analysis and literature_search subgraphs:

    [user query]
        │
        ▼
    problem_analysis  ──► merge_keywords
                                │
                                ▼
                      literature_search  ──► END
"""

from __future__ import annotations

from langgraph.graph import END, StateGraph

from problem_analysis import build_problem_analysis_graph
from literature_search import build_literature_search_graph
from research.state import MainResearchState
from utils import create_results_run_dir


def _merge_keywords(state: MainResearchState) -> dict:
    """Combine required + optional keywords into a single list for search."""
    keywords = state.get("required_keywords", []) + state.get("optional_keywords", [])
    results_save_dir = create_results_run_dir(state["query_description"], keywords)
    return {"keywords": keywords, "results_save_dir": str(results_save_dir)}


def build_research_graph():
    builder = StateGraph(MainResearchState)

    builder.add_node("problem_analysis", build_problem_analysis_graph())
    builder.add_node("merge_keywords", _merge_keywords)
    builder.add_node("literature_search", build_literature_search_graph())

    builder.set_entry_point("problem_analysis")
    builder.add_edge("problem_analysis", "merge_keywords")
    builder.add_edge("merge_keywords", "literature_search")
    builder.add_edge("literature_search", END)

    return builder.compile()
