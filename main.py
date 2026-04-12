#!/usr/bin/env python3
"""
Usage:
    python main.py "fault tolerance" "static analysis"
    python main.py "fuzzing seed generation" --max 10 --output results.json
"""

import argparse
import json
import sys
from pathlib import Path

from literature_search import search


def main():
    parser = argparse.ArgumentParser(description="Search academic literature.")
    parser.add_argument("keywords", nargs="+", help="Search keywords")
    parser.add_argument("--max", type=int, default=20, dest="max_results",
                        help="Max results per source (default: 20)")
    parser.add_argument("--output", type=str, default=None,
                        help="Save results to JSON file")
    args = parser.parse_args()

    print(f"Searching: {args.keywords} (max {args.max_results} per source) ...")
    papers = search(args.keywords, max_results_per_source=args.max_results)
    print(f"Found {len(papers)} papers total.\n")

    if args.output:
        Path(args.output).write_text(
            json.dumps(papers, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print(f"Saved to {args.output}")
    else:
        print(json.dumps(papers, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
