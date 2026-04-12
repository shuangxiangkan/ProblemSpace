from __future__ import annotations
from typing import TypedDict


class KeywordAnalysisState(TypedDict):
    query_description: str
    required_keywords: list[str]
    optional_keywords: list[str]
