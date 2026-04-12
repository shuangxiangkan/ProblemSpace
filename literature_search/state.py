from __future__ import annotations

import operator
from typing import Annotated, TypedDict


class PaperRecord(TypedDict):
    title: str
    authors: list[str]
    abstract: str | None
    year: int | None
    source: str                 # "arxiv" | "semantic_scholar" | "openalex"
    url: str
    pdf_url: str | None
    doi: str | None
    citation_count: int | None
    venue: str | None
    status: str                 # "pending" | "classified" | "analyzed"


class PaperSearchState(TypedDict):
    keywords: list[str]
    max_results_per_source: int
    papers: Annotated[list[PaperRecord], operator.add]
    errors: Annotated[list[str], operator.add]
