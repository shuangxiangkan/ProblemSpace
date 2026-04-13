"""Top-level state shared across all subgraphs in the research pipeline."""

from __future__ import annotations

import operator
from typing import Annotated, TypedDict

from literature_search.state import PaperRecord


class MainResearchState(TypedDict):
    # ── User input ─────────────────────────────────────────────────────────
    query_description: str          # natural language description of research topic
    max_results_per_source: int

    # ── Step 1: problem_analysis subgraph output ───────────────────────────
    required_keywords: list[str]    # must-include keywords
    optional_keywords: list[str]    # nice-to-have / broadening keywords

    # ── Transition node output ─────────────────────────────────────────────
    keywords: list[str]             # merged list fed into literature_search

    # ── Step 2: literature_search subgraph output ──────────────────────────
    papers: list[PaperRecord]
    errors: Annotated[list[str], operator.add]
