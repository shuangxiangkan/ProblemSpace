from __future__ import annotations

import hashlib
import logging
import os
import time

import arxiv
import requests
from dotenv import load_dotenv
from pydantic import BaseModel, Field

from models import get_llm
from .state import PaperRecord, PaperSearchState

load_dotenv()
logger = logging.getLogger(__name__)


# ── arXiv ──────────────────────────────────────────────────────────────────

def search_arxiv(state: PaperSearchState) -> dict:
    keywords = state["keywords"]
    limit = state.get("max_results_per_source", 20)
    seen: set[str] = set()
    papers: list[PaperRecord] = []
    errors: list[str] = []

    client = arxiv.Client()
    for kw in keywords:
        logger.info("[arXiv] Searching: '%s' (max %d) ...", kw, limit)
        try:
            search = arxiv.Search(
                query=kw,
                max_results=limit,
                sort_by=arxiv.SortCriterion.Relevance,
            )
            count = 0
            for r in client.results(search):
                key = r.entry_id
                if key in seen:
                    continue
                seen.add(key)
                count += 1
                papers.append(PaperRecord(
                    title=r.title,
                    authors=[a.name for a in r.authors],
                    abstract=r.summary,
                    year=r.published.year if r.published else None,
                    source="arxiv",
                    url=r.entry_id,
                    pdf_url=r.pdf_url,
                    doi=r.doi,
                    citation_count=None,
                    venue=r.journal_ref,
                    status="pending",
                ))
            logger.info("[arXiv] '%s' — %d papers.", kw, count)
        except Exception as exc:
            errors.append(f"arXiv[{kw}]: {exc}")
            logger.error("[arXiv] '%s' error: %s", kw, exc)

    logger.info("[arXiv] Done — %d total (after dedup).", len(papers))
    return {"raw_papers": papers, "errors": errors}


# ── Semantic Scholar ────────────────────────────────────────────────────────

def _s2_fetch(query: str, limit: int, fields: str, headers: dict) -> list[dict]:
    """Fetch from Semantic Scholar with exponential-backoff retry."""
    for attempt in range(1, 4):
        wait = 3 ** attempt
        try:
            resp = requests.get(
                "https://api.semanticscholar.org/graph/v1/paper/search",
                params={"query": query, "limit": limit, "fields": fields},
                headers=headers,
                timeout=30,
            )
            if resp.status_code == 429:
                logger.warning(
                    "[Semantic Scholar] Rate-limited (429), retrying in %ds (attempt %d/3).", wait, attempt
                )
                time.sleep(wait)
                continue
            resp.raise_for_status()
            return resp.json().get("data", [])
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as exc:
            logger.warning(
                "[Semantic Scholar] Network error: %s. Retrying in %ds (attempt %d/3).", exc, wait, attempt
            )
            time.sleep(wait)
    logger.error("[Semantic Scholar] All retries exhausted.")
    return []


def search_semantic_scholar(state: PaperSearchState) -> dict:
    keywords = state["keywords"]
    limit = state.get("max_results_per_source", 20)
    seen: set[str] = set()
    papers: list[PaperRecord] = []
    errors: list[str] = []

    fields = "title,authors,abstract,year,externalIds,openAccessPdf,citationCount,venue,url"
    headers: dict[str, str] = {}
    if api_key := os.getenv("S2_API_KEY"):
        headers["x-api-key"] = api_key

    for kw in keywords:
        logger.info("[Semantic Scholar] Searching: '%s' (max %d) ...", kw, limit)
        try:
            items = _s2_fetch(kw, limit, fields, headers)
            count = 0
            for item in items:
                key = item.get("paperId", "")
                if key in seen:
                    continue
                seen.add(key)
                count += 1
                pdf_url = (item.get("openAccessPdf") or {}).get("url")
                doi = (item.get("externalIds") or {}).get("DOI")
                papers.append(PaperRecord(
                    title=item.get("title", ""),
                    authors=[a["name"] for a in item.get("authors", [])],
                    abstract=item.get("abstract"),
                    year=item.get("year"),
                    source="semantic_scholar",
                    url=item.get("url") or f"https://www.semanticscholar.org/paper/{key}",
                    pdf_url=pdf_url,
                    doi=doi,
                    citation_count=item.get("citationCount"),
                    venue=item.get("venue"),
                    status="pending",
                ))
            logger.info("[Semantic Scholar] '%s' — %d papers.", kw, count)
        except Exception as exc:
            errors.append(f"Semantic Scholar[{kw}]: {exc}")
            logger.error("[Semantic Scholar] '%s' error: %s", kw, exc)

    logger.info("[Semantic Scholar] Done — %d total (after dedup).", len(papers))
    return {"raw_papers": papers, "errors": errors}


# ── OpenAlex ────────────────────────────────────────────────────────────────

def _reconstruct_abstract(inverted_index: dict | None) -> str | None:
    if not inverted_index:
        return None
    words: dict[int, str] = {}
    for word, positions in inverted_index.items():
        for pos in positions:
            words[pos] = word
    return " ".join(words[i] for i in sorted(words))


def search_openalex(state: PaperSearchState) -> dict:
    keywords = state["keywords"]
    limit = state.get("max_results_per_source", 20)
    seen: set[str] = set()
    papers: list[PaperRecord] = []
    errors: list[str] = []

    select_fields = ",".join([
        "title", "authorships", "abstract_inverted_index",
        "publication_year", "doi", "open_access",
        "cited_by_count", "primary_location", "id",
    ])

    for kw in keywords:
        logger.info("[OpenAlex] Searching: '%s' (max %d) ...", kw, limit)
        try:
            resp = requests.get(
                "https://api.openalex.org/works",
                params={"search": kw, "per-page": limit, "select": select_fields},
                headers={"User-Agent": "LiteratureSearchTool/1.0 (research)"},
                timeout=30,
            )
            resp.raise_for_status()
            count = 0
            for item in resp.json().get("results", []):
                key = item.get("id", "")
                if key in seen:
                    continue
                seen.add(key)
                count += 1
                oa = item.get("open_access") or {}
                pdf_url = oa.get("oa_url") if oa.get("is_oa") else None
                authors = [
                    a["author"]["display_name"]
                    for a in item.get("authorships", [])
                    if a.get("author")
                ]
                loc = item.get("primary_location") or {}
                venue = (loc.get("source") or {}).get("display_name")
                papers.append(PaperRecord(
                    title=item.get("title", ""),
                    authors=authors,
                    abstract=_reconstruct_abstract(item.get("abstract_inverted_index")),
                    year=item.get("publication_year"),
                    source="openalex",
                    url=key,
                    pdf_url=pdf_url,
                    doi=item.get("doi"),
                    citation_count=item.get("cited_by_count"),
                    venue=venue,
                    status="pending",
                ))
            logger.info("[OpenAlex] '%s' — %d papers.", kw, count)
        except Exception as exc:
            errors.append(f"OpenAlex[{kw}]: {exc}")
            logger.error("[OpenAlex] '%s' error: %s", kw, exc)

    logger.info("[OpenAlex] Done — %d total (after dedup).", len(papers))
    return {"raw_papers": papers, "errors": errors}


# ── Dedup ──────────────────────────────────────────────────────────────────


def dedup_papers(state: PaperSearchState) -> dict:
    """Remove cross-source duplicates from raw_papers."""
    deduped: list[PaperRecord] = []
    seen: set[str] = set()

    for paper in state["raw_papers"]:
        if paper.get("doi"):
            key = paper["doi"].strip().lower()
        else:
            key = hashlib.sha1(paper["title"].strip().lower().encode()).hexdigest()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(paper)

    removed = len(state["raw_papers"]) - len(deduped)
    if removed:
        logger.info("[Dedup] Removed %d cross-source duplicates.", removed)

    return {"papers": deduped}


# ── Relevance Filter ───────────────────────────────────────────────────────

_FILTER_BATCH_SIZE = 8


class PaperKeepSelection(BaseModel):
    keep_indices: list[int] = Field(
        description="0-based indices of papers that should be kept in the current batch."
    )


def _format_paper_batch(papers: list[PaperRecord]) -> str:
    chunks: list[str] = []
    for index, paper in enumerate(papers):
        chunks.append(
            "\n".join([
                f"Paper #{index}",
                f"Title: {paper.get('title', '').strip()}",
                f"Abstract: {(paper.get('abstract') or '').strip()}",
                f"Venue: {(paper.get('venue') or '').strip()}",
                f"Year: {paper.get('year')}",
                f"Source: {paper.get('source', '').strip()}",
            ])
        )
    return "\n\n".join(chunks)


def filter_papers(state: PaperSearchState) -> dict:
    """Keep only papers whose title/abstract are relevant to the original query."""
    papers = state["papers"]
    if not papers:
        return {}

    query_description = state.get("query_description") or " ".join(state.get("keywords", []))
    llm = get_llm("glm", thinking_type="disabled")
    structured_llm = llm.with_structured_output(PaperKeepSelection, method="function_calling")

    filtered: list[PaperRecord] = []
    errors: list[str] = []
    removed = 0

    system_prompt = """You are filtering academic search results for relevance.

Given the original research request and a batch of candidate papers, decide whether each paper should be kept.

Rules:
- Keep a paper only if its title and abstract are clearly relevant to the user's research request.
- Prefer precision over recall: if relevance is weak, indirect, or generic, remove it.
- Judge based on the user's original request, not only keyword overlap.
- If the abstract is missing, use the title and venue, but still be conservative.
- Return only the indices of papers that should be kept.
"""

    for start in range(0, len(papers), _FILTER_BATCH_SIZE):
        batch = papers[start:start + _FILTER_BATCH_SIZE]
        try:
            result: PaperKeepSelection = structured_llm.invoke([
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": (
                        f"Original research request:\n{query_description}\n\n"
                        f"Candidate papers:\n{_format_paper_batch(batch)}"
                    ),
                },
            ])
        except Exception as exc:
            errors.append(f"GLM relevance filter batch[{start}:{start + len(batch)}]: {exc}")
            logger.error("[Filter] batch[%d:%d] failed: %s", start, start + len(batch), exc)
            filtered.extend(batch)
            continue

        keep_indices = {
            index for index in result.keep_indices if 0 <= index < len(batch)
        }
        for index, paper in enumerate(batch):
            if index in keep_indices:
                filtered.append(paper)
            else:
                removed += 1

    if removed:
        logger.info("[Filter] Removed %d low-relevance papers.", removed)
    logger.info("[Filter] Kept %d / %d papers after relevance filtering.", len(filtered), len(papers))

    return {"papers": filtered, "errors": errors}
