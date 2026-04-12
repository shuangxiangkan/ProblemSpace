from __future__ import annotations

import logging

from pydantic import BaseModel, Field

from models import get_llm
from problem_analysis.state import KeywordAnalysisState

logger = logging.getLogger(__name__)


class KeywordPlan(BaseModel):
    required_keywords: list[str] = Field(
        description=(
            "2-5 specific, high-precision keywords or phrases that MUST appear in "
            "relevant results. Prefer exact technical terms."
        )
    )
    optional_keywords: list[str] = Field(
        description=(
            "3-8 broader or related terms that improve recall, e.g. synonyms, "
            "related techniques, or adjacent topics."
        )
    )
    reasoning: str = Field(description="One sentence explaining the keyword choices.")


_SYSTEM_PROMPT = """\
You are an expert at constructing academic literature search queries.

Given a research topic, produce a keyword plan with two lists:

required_keywords (2–4 entries):
  - Each entry is a COMPOUND PHRASE that captures the INTERSECTION of the core concepts.
  - Do NOT split the topic into isolated single concepts — that floods results with unrelated papers.
  - Prefer exact technical terms and common variants researchers actually use in titles/abstracts.
  - Example: for "fault tolerance in dragonfly networks", good entries are
      "dragonfly fault tolerance", "fault-tolerant dragonfly network", "dragonfly topology fault"
    Bad entries (too broad, unrelated papers flood in):
      "fault tolerance", "network topology", "high-performance computing"

optional_keywords (3–6 entries):
  - Closely related techniques or synonyms that may appear in relevant papers.
  - Still specific enough to avoid off-topic results — avoid generic terms like
    "network resilience", "data center networks", "high-performance computing" unless
    they are genuinely central to the topic.

Return valid JSON matching the schema."""


def analyze_query(state: KeywordAnalysisState) -> dict:
    description = state["query_description"]
    logger.info("[KeywordAnalysis] Analyzing: '%s'", description)

    llm = get_llm()
    structured_llm = llm.with_structured_output(KeywordPlan, method="function_calling")

    result: KeywordPlan = structured_llm.invoke([
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": f"Research topic: {description}"},
    ])

    logger.info("[KeywordAnalysis] Required  : %s", result.required_keywords)
    logger.info("[KeywordAnalysis] Optional  : %s", result.optional_keywords)
    logger.info("[KeywordAnalysis] Reasoning : %s", result.reasoning)

    return {
        "required_keywords": result.required_keywords,
        "optional_keywords": result.optional_keywords,
    }
