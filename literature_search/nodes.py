from __future__ import annotations

import logging
import os
import time

import arxiv
import requests
from dotenv import load_dotenv

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
