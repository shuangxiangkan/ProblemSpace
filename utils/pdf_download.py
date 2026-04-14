from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import urljoin

import requests

from literature_search.state import PaperRecord


def _slugify(text: str) -> str:
    slug = re.sub(r"[^\w\-]+", "_", text).strip("_")
    return slug[:80] or "paper"


def _normalize_doi(doi: str | None) -> str | None:
    if not doi:
        return None
    normalized = doi.strip()
    normalized = re.sub(r"^https?://(dx\.)?doi\.org/", "", normalized, flags=re.IGNORECASE)
    return normalized or None


def _download_pdf(url: str, file_path: Path) -> None:
    response = requests.get(
        url,
        timeout=60,
        stream=True,
        headers={
            "User-Agent": "ProblemSpacePDFDownloader/1.0",
            "Accept": "application/pdf,application/octet-stream;q=0.9,*/*;q=0.8",
        },
        allow_redirects=True,
    )
    response.raise_for_status()
    content_type = (response.headers.get("content-type") or "").lower()
    if "pdf" not in content_type and not str(response.url).lower().endswith(".pdf"):
        raise ValueError(f"URL did not return a PDF response: {url}")

    with file_path.open("wb") as handle:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                handle.write(chunk)


def _extract_pdf_url_from_html(html: str, base_url: str) -> str | None:
    meta_match = re.search(
        r'<meta[^>]+name=["\']citation_pdf_url["\'][^>]+content=["\']([^"\']+)["\']',
        html,
        flags=re.IGNORECASE,
    )
    if meta_match:
        return urljoin(base_url, meta_match.group(1))

    href_match = re.search(
        r'href=["\']([^"\']+\.pdf(?:\?[^"\']*)?)["\']',
        html,
        flags=re.IGNORECASE,
    )
    if href_match:
        return urljoin(base_url, href_match.group(1))

    return None


def _resolve_pdf_url_from_doi(doi: str) -> str | None:
    doi_url = f"https://doi.org/{doi}"

    try:
        response = requests.get(
            doi_url,
            timeout=30,
            stream=True,
            headers={
                "User-Agent": "ProblemSpacePDFDownloader/1.0",
                "Accept": "application/pdf",
            },
            allow_redirects=True,
        )
        response.raise_for_status()
        content_type = (response.headers.get("content-type") or "").lower()
        if "pdf" in content_type or str(response.url).lower().endswith(".pdf"):
            response.close()
            return str(response.url)
        response.close()
    except Exception:
        pass

    try:
        response = requests.get(
            doi_url,
            timeout=30,
            headers={"User-Agent": "ProblemSpacePDFDownloader/1.0"},
            allow_redirects=True,
        )
        response.raise_for_status()
        return _extract_pdf_url_from_html(response.text, str(response.url))
    except Exception:
        return None


def download_paper_pdfs(run_dir: str | Path, papers: list[PaperRecord]) -> list[dict]:
    run_path = Path(run_dir)
    pdf_dir = run_path / "pdfs"
    pdf_dir.mkdir(parents=True, exist_ok=True)

    manifest: list[dict] = []

    for index, paper in enumerate(papers, start=1):
        pdf_url = paper.get("pdf_url")
        doi = _normalize_doi(paper.get("doi"))
        base_name = _slugify(paper.get("title", "paper"))
        file_name = f"{index:03d}_{base_name}.pdf"
        file_path = pdf_dir / file_name

        record = {
            "title": paper.get("title", ""),
            "source": paper.get("source", ""),
            "url": paper.get("url", ""),
            "doi": paper.get("doi"),
            "pdf_url": pdf_url,
            "file_path": str(file_path),
            "status": "pending",
        }

        if not pdf_url:
            resolved_pdf_url = _resolve_pdf_url_from_doi(doi) if doi else None
            if resolved_pdf_url:
                pdf_url = resolved_pdf_url
                record["pdf_url"] = resolved_pdf_url
                record["resolved_via"] = "doi"
            else:
                record["status"] = "skipped_no_pdf_url"
                manifest.append(record)
                continue

        try:
            _download_pdf(pdf_url, file_path)
            record["status"] = "downloaded"
        except Exception as exc:
            record["status"] = "failed"
            record["error"] = str(exc)
            if file_path.exists():
                file_path.unlink()

        manifest.append(record)

    return manifest


def save_pdf_failures(run_dir: str | Path, manifest: list[dict]) -> Path:
    run_path = Path(run_dir)
    failures = [
        item for item in manifest
        if item["status"] in {"failed", "skipped_no_pdf_url"}
    ]
    file_path = run_path / "pdf_download_failures.json"
    file_path.write_text(
        json.dumps(failures, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return file_path