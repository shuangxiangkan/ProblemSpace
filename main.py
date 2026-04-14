#!/usr/bin/env python3
"""
Usage (keyword mode):
    python main.py "fault tolerance" "static analysis"
    python main.py "fuzzing seed generation" --max 10 --output results.json

Usage (describe mode — uses LLM to extract keywords first):
    python main.py --describe "I want papers about fuzzing-based seed generation for program analysis"
    python main.py --describe "mutation testing for concurrent programs" --max 15 --output results.json
"""

import argparse
import json
import logging
from pathlib import Path

from literature_search import search

logging.basicConfig(level=logging.INFO, format="%(message)s")
logging.getLogger("arxiv").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Search academic literature.")

    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("keywords", nargs="*", metavar="KEYWORD",
                      help="Explicit search keywords (keyword mode)")
    mode.add_argument("--describe", metavar="TEXT",
                      help="Natural-language description; LLM extracts keywords (describe mode)")

    parser.add_argument("--max", type=int, default=20, dest="max_results",
                        help="Max results per source (default: 20)")
    parser.add_argument("--output", type=str, default=None,
                        help="Save results to JSON file")
    args = parser.parse_args()

    if args.describe:
        # LLM-assisted flow: problem_analysis → merge → literature_search
        from research import build_research_graph, MainResearchState

        logger.info("Analyzing query with LLM: '%s'", args.describe)
        pipeline = build_research_graph()
        result = pipeline.invoke(MainResearchState(
            query_description=args.describe,
            max_results_per_source=args.max_results,
            required_keywords=[],
            optional_keywords=[],
            keywords=[],
            papers=[],
            errors=[],
        ))
        papers = result["papers"]
        for err in result.get("errors", []):
            logger.warning("%s", err)
    else:
        if not args.keywords:
            parser.error("Provide at least one keyword, or use --describe.")
        logger.info("Searching: %s (max %d per source) ...", args.keywords, args.max_results)
        papers = search(args.keywords, max_results_per_source=args.max_results)

    logger.info("Found %d papers total.", len(papers))

    if args.output:
        Path(args.output).write_text(
            json.dumps(papers, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        logger.info("Saved to %s", args.output)


if __name__ == "__main__":
    main()
