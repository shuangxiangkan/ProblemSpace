from __future__ import annotations

import logging

from pydantic import BaseModel, Field

from models import get_llm
from prompts import load_prompt
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


_SYSTEM_PROMPT = load_prompt("keyword_analysis_system.txt")


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
