from __future__ import annotations

import os
import time
import requests
import arxiv
from dotenv import load_dotenv

load_dotenv()  # loads .env from project root (no-op if file absent)

from .state import PaperRecord, PaperSearchState


# ── arXiv ──────────────────────────────────────────────────────────────────

def search_arxiv(state: PaperSearchState) -> dict:
    query = " ".join(state["keywords"])
    limit = state.get("max_results_per_source", 20)
    papers: list[PaperRecord] = []
    errors: list[str] = []

    print(f"[arXiv] Searching: '{query}' (max {limit}) ...")
    try:
        client = arxiv.Client()
        search = arxiv.Search(
            query=query,
            max_results=limit,
            sort_by=arxiv.SortCriterion.Relevance,
        )
        for r in client.results(search):
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
        print(f"[arXiv] Done — {len(papers)} papers retrieved.")
    except Exception as exc:
        errors.append(f"arXiv: {exc}")
        print(f"[arXiv] Error: {exc}")

    return {"papers": papers, "errors": errors}


# ── Semantic Scholar ────────────────────────────────────────────────────────

def search_semantic_scholar(state: PaperSearchState) -> dict:
    query = " ".join(state["keywords"])
    limit = state.get("max_results_per_source", 20)
    papers: list[PaperRecord] = []
    errors: list[str] = []

    fields = "title,authors,abstract,year,externalIds,openAccessPdf,citationCount,venue,url"
    headers = {}
    if api_key := os.getenv("S2_API_KEY"):
        headers["x-api-key"] = api_key

    print(f"[Semantic Scholar] Searching: '{query}' (max {limit}) ...")
    resp = None
    for attempt in range(1, 4):          # up to 3 attempts
        wait = 3 ** attempt              # 3s, 9s, 27s
        try:
            resp = requests.get(
                "https://api.semanticscholar.org/graph/v1/paper/search",
                params={"query": query, "limit": limit, "fields": fields},
                headers=headers,
                timeout=30,
            )
            if resp.status_code == 429:
                print(f"[Semantic Scholar] Rate-limited (429), retrying in {wait}s (attempt {attempt}/3) ...")
                time.sleep(wait)
                continue
            resp.raise_for_status()
            break
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as exc:
            print(f"[Semantic Scholar] Network error: {exc}. Retrying in {wait}s (attempt {attempt}/3) ...")
            time.sleep(wait)
        except Exception:
            if attempt == 3:
                raise
    try:
        for item in (resp.json().get("data", []) if resp and resp.ok else []):
            pdf_url = (item.get("openAccessPdf") or {}).get("url")
            doi = (item.get("externalIds") or {}).get("DOI")
            papers.append(PaperRecord(
                title=item.get("title", ""),
                authors=[a["name"] for a in item.get("authors", [])],
                abstract=item.get("abstract"),
                year=item.get("year"),
                source="semantic_scholar",
                url=item.get("url") or f"https://www.semanticscholar.org/paper/{item['paperId']}",
                pdf_url=pdf_url,
                doi=doi,
                citation_count=item.get("citationCount"),
                venue=item.get("venue"),
                status="pending",
            ))
        print(f"[Semantic Scholar] Done — {len(papers)} papers retrieved.")
    except Exception as exc:
        errors.append(f"Semantic Scholar: {exc}")
        print(f"[Semantic Scholar] Error: {exc}")

    return {"papers": papers, "errors": errors}


# ── OpenAlex ────────────────────────────────────────────────────────────────

def _reconstruct_abstract(inverted_index: dict | None) -> str | None:
    """OpenAlex stores abstract as an inverted index; reconstruct it."""
    if not inverted_index:
        return None
    words: dict[int, str] = {}
    for word, positions in inverted_index.items():
        for pos in positions:
            words[pos] = word
    return " ".join(words[i] for i in sorted(words))


def search_openalex(state: PaperSearchState) -> dict:
    query = " ".join(state["keywords"])
    limit = state.get("max_results_per_source", 20)
    papers: list[PaperRecord] = []
    errors: list[str] = []

    print(f"[OpenAlex] Searching: '{query}' (max {limit}) ...")
    select_fields = ",".join([
        "title", "authorships", "abstract_inverted_index",
        "publication_year", "doi", "open_access",
        "cited_by_count", "primary_location", "id",
    ])
    try:
        resp = requests.get(
            "https://api.openalex.org/works",
            params={"search": query, "per-page": limit, "select": select_fields},
            headers={"User-Agent": "LiteratureSearchTool/1.0 (research)"},
            timeout=30,
        )
        resp.raise_for_status()
        for item in resp.json().get("results", []):
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
                url=item.get("id", ""),
                pdf_url=pdf_url,
                doi=item.get("doi"),
                citation_count=item.get("cited_by_count"),
                venue=venue,
                status="pending",
            ))
        print(f"[OpenAlex] Done — {len(papers)} papers retrieved.")
    except Exception as exc:
        errors.append(f"OpenAlex: {exc}")
        print(f"[OpenAlex] Error: {exc}")

    return {"papers": papers, "errors": errors}
