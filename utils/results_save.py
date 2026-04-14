from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

from literature_search.state import PaperRecord


RESULTS_SAVE_DIR = Path(__file__).resolve().parent.parent / "results_save"


def _slugify(text: str) -> str:
    slug = re.sub(r"[^\w\-]+", "_", text).strip("_")
    return slug[:60] or "search"


def create_results_run_dir(query_description: str, keywords: list[str]) -> Path:
    seed = query_description.strip() or "_".join(keywords[:3])
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = RESULTS_SAVE_DIR / f"{_slugify(seed)}_{ts}"
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def save_paper_snapshot(
    run_dir: str | Path,
    stage_name: str,
    papers: list[PaperRecord],
) -> Path:
    run_path = Path(run_dir)
    run_path.mkdir(parents=True, exist_ok=True)
    file_path = run_path / f"{stage_name}.json"
    file_path.write_text(
        json.dumps(papers, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return file_path