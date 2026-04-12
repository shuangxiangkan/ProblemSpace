# AutoResearch · ProblemSpace

> **Goal**: Systematically discover high-value, low-coverage research ideas in the program analysis space — treating idea discovery as a search problem, not an inspiration problem.

The core intuition: apply **fuzzing methodology** to research idea generation.
Papers / methods = seeds · Problem-space analysis = coverage modeling · Idea variants = mutations · Novelty + feasibility = oracle.

---

## Project Structure

```
ProblemSpace/
├── problem-space.md          # Methodology & design notes
├── main.py                   # CLI entry point
├── requirements.txt
├── papers.db                 # SQLite — all retrieved papers (git-ignored)
│
└── literature_search/        # Sub-module 1: Paper retrieval
    ├── state.py              # PaperRecord, PaperSearchState
    ├── nodes.py              # arXiv / Semantic Scholar / OpenAlex nodes
    ├── graph.py              # LangGraph search graph
    ├── storage.py            # SQLite persistence + dedup
    └── __init__.py
```

### Planned sub-modules

| Module | Purpose |
|---|---|
| `literature_search/` | ✅ Fetch & store papers from arXiv, Semantic Scholar, OpenAlex |
| `paper_analysis/` | 🔲 LLM-powered classification, tagging, failure-mode extraction |
| `idea_generation/` | 🔲 Mutation operators — generate idea seeds from gaps & blind spots |
| `idea_triage/` | 🔲 Score ideas on novelty / feasibility / eval-clarity / upside |
| `problem_space_map/` | 🔲 Build coverage map of the design space |

---

## Quick Start

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Search and save to papers.db
python main.py "program analysis" "static analysis" --max 30

# Save to JSON for one-off inspection
python main.py "fuzzing seed generation" --max 20 --output results.json
```

### Load papers in code

```python
from literature_search import search, load_papers, update_status

# Run the search graph: arXiv → Semantic Scholar → OpenAlex → SQLite
papers = search(["program analysis", "taint analysis"], max_results_per_source=30)

# Query DB — fetch all pending papers for LLM analysis
pending = load_papers(status="pending")

# After LLM classifies a paper, update its status
update_status(paper["doi"], "classified")
```

### Paper status lifecycle

```
pending  →  classified  →  analyzed
```

---

## DB Schema (papers.db)

| Column | Description |
|---|---|
| `dedup_key` | DOI or sha1(title) — unique constraint, prevents duplicates |
| `title / authors / abstract` | Full metadata |
| `source` | `arxiv` · `semantic_scholar` · `openalex` |
| `pdf_url` | Direct PDF link if open-access |
| `citation_count` | From Semantic Scholar / OpenAlex |
| `status` | `pending` → `classified` → `analyzed` |
| `search_query` | Which keyword query retrieved this paper |

Browse with [DB Browser for SQLite](https://sqlitebrowser.org/) or [TablePlus](https://tableplus.com/).

---

## Semantic Scholar API Key

Free tier is rate-limited (429). Apply for a free key at <https://www.semanticscholar.org/product/api> and set it as an env variable:

```bash
export S2_API_KEY="<your_key>"
```
