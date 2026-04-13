"""SQLite-backed paper storage.

Schema
------
papers
  id            INTEGER PRIMARY KEY AUTOINCREMENT
  dedup_key     TEXT UNIQUE          -- doi if available, else sha1(title.lower())
  title         TEXT
  authors       TEXT                 -- JSON array
  abstract      TEXT
  year          INTEGER
  source        TEXT
  url           TEXT
  pdf_url       TEXT
  doi           TEXT
  citation_count INTEGER
  venue         TEXT
  status        TEXT DEFAULT 'pending'   -- pending | classified | analyzed
  search_query  TEXT                 -- what query found this paper
  created_at    TEXT DEFAULT (datetime('now'))
  updated_at    TEXT DEFAULT (datetime('now'))
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

from .state import PaperRecord

DEFAULT_DB = Path(__file__).parent.parent / "papers.db"


def dedup_key(paper: PaperRecord) -> str:
    """Return a dedup key: DOI (normalized) or sha1(title)."""
    if paper.get("doi"):
        return paper["doi"].strip().lower()
    return hashlib.sha1(paper["title"].strip().lower().encode()).hexdigest()


def get_connection(db_path: Path = DEFAULT_DB) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    _ensure_schema(conn)
    return conn


def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS papers (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            dedup_key      TEXT    UNIQUE,
            title          TEXT    NOT NULL,
            authors        TEXT,
            abstract       TEXT,
            year           INTEGER,
            source         TEXT,
            url            TEXT,
            pdf_url        TEXT,
            doi            TEXT,
            citation_count INTEGER,
            venue          TEXT,
            status         TEXT    NOT NULL DEFAULT 'pending',
            search_query   TEXT,
            created_at     TEXT    NOT NULL DEFAULT (datetime('now')),
            updated_at     TEXT    NOT NULL DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_papers_status ON papers(status);
        CREATE INDEX IF NOT EXISTS idx_papers_year   ON papers(year);
    """)
    conn.commit()


def save_papers(
    papers: list[PaperRecord],
    search_query: str = "",
    db_path: Path = DEFAULT_DB,
) -> tuple[int, int]:
    """Insert papers, skip duplicates. Returns (inserted, skipped)."""
    inserted = skipped = 0
    with get_connection(db_path) as conn:
        for p in papers:
            key = dedup_key(p)
            try:
                conn.execute(
                    """
                    INSERT INTO papers
                        (dedup_key, title, authors, abstract, year, source,
                         url, pdf_url, doi, citation_count, venue, status, search_query)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        key,
                        p.get("title", ""),
                        json.dumps(p.get("authors", []), ensure_ascii=False),
                        p.get("abstract"),
                        p.get("year"),
                        p.get("source", ""),
                        p.get("url", ""),
                        p.get("pdf_url"),
                        p.get("doi"),
                        p.get("citation_count"),
                        p.get("venue"),
                        p.get("status", "pending"),
                        search_query,
                    ),
                )
                inserted += 1
            except sqlite3.IntegrityError:
                skipped += 1
        conn.commit()
    return inserted, skipped


def load_papers(
    status: str | None = None,
    db_path: Path = DEFAULT_DB,
) -> list[PaperRecord]:
    """Load papers from DB, optionally filtered by status."""
    with get_connection(db_path) as conn:
        if status:
            rows = conn.execute(
                "SELECT * FROM papers WHERE status = ? ORDER BY year DESC", (status,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM papers ORDER BY year DESC"
            ).fetchall()

    return [_row_to_paper(r) for r in rows]


def update_status(dedup_key: str, status: str, db_path: Path = DEFAULT_DB) -> None:
    with get_connection(db_path) as conn:
        conn.execute(
            "UPDATE papers SET status=?, updated_at=datetime('now') WHERE dedup_key=?",
            (status, dedup_key),
        )
        conn.commit()


def _row_to_paper(row: sqlite3.Row) -> PaperRecord:
    return PaperRecord(
        title=row["title"],
        authors=json.loads(row["authors"] or "[]"),
        abstract=row["abstract"],
        year=row["year"],
        source=row["source"],
        url=row["url"],
        pdf_url=row["pdf_url"],
        doi=row["doi"],
        citation_count=row["citation_count"],
        venue=row["venue"],
        status=row["status"],
    )
