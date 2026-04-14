# AutoResearch · ProblemSpace

> **Goal**: Systematically discover high-value, low-coverage research ideas in the program analysis space — treating idea discovery as a search problem, not an inspiration problem.

The core intuition: apply **fuzzing methodology** to research idea generation.  
Papers / methods = seeds · Problem-space analysis = coverage modeling · Idea variants = mutations · Novelty + feasibility = oracle.

---

## Project Structure

```
ProblemSpace/
├── main.py                   # CLI entry point
├── requirements.txt
├── papers.db                 # SQLite — all retrieved papers (git-ignored)
├── problem-space.md          # Methodology & design notes
│
├── models/                   # LLM factory (DeepSeek / OpenAI / GLM)
│   └── __init__.py           # get_llm(provider)
│
├── problem_analysis/         # Sub-module 1: LLM keyword extraction
│   ├── state.py              # KeywordAnalysisState
│   ├── nodes.py              # analyze_query node (DeepSeek structured output)
│   ├── graph.py              # build_problem_analysis_graph()
│   └── __init__.py
│
├── literature_search/        # Sub-module 2: Paper retrieval
│   ├── state.py              # PaperRecord, PaperSearchState
│   ├── nodes.py              # search nodes + dedup + GLM relevance filter
│   ├── graph.py              # build_literature_search_graph()
│   ├── storage.py            # SQLite persistence + dedup
│   └── __init__.py
│
└── research/                 # Top-level pipeline (combines sub-modules)
    ├── state.py              # MainResearchState
    ├── graph.py              # build_research_graph()
    └── __init__.py
```

### Planned sub-modules

| Module | Purpose |
|---|---|
| `problem_analysis/` | ✅ LLM extracts structured search keywords from a natural-language topic description |
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

# Copy and fill in API keys
cp .env.example .env
```

### Describe mode (recommended) — LLM extracts keywords automatically

```bash
# Describe your topic in natural language; the LLM generates precise compound keywords
python main.py --describe "fault tolerance in dragonfly network topology" --max 10
python main.py --describe "mutation testing for concurrent programs" --max 15 --output results.json
```

### Keyword mode — explicit keywords

```bash
python main.py "dragonfly fault tolerance" "fault-tolerant routing" --max 20
python main.py "fuzzing seed generation" --max 20 --output results.json
```

### Load papers in code

```python
from literature_search import search, load_papers, update_status

# Run the search graph: arXiv / Semantic Scholar / OpenAlex → dedup → relevance filter → SQLite
papers = search(["dragonfly fault tolerance", "fault-tolerant dragonfly"], max_results_per_source=20)

# Query DB — fetch all pending papers for LLM analysis
pending = load_papers(status="pending")

# After LLM classifies a paper, update its status
update_status(paper["doi"], "classified")
```

### View LangGraph structure

```bash
source .venv/bin/activate

# View the top-level pipeline as ASCII
python utils/show_graph.py research --format ascii

# View the literature search subgraph as Mermaid
python utils/show_graph.py literature_search --format mermaid

# View the fully expanded top-level research graph
python utils/show_graph.py research --format mermaid

# Save Mermaid output to a file
python utils/show_graph.py literature_search --format mermaid --output literature_search.mmd

# Export a directly viewable HTML file
python utils/show_graph.py literature_search --format html --output literature_search.html

# Export a PNG image
python utils/show_graph.py literature_search --format png --output literature_search.png

# Export all graphs to the visualization directory
python utils/show_graph.py

# Disable subgraph expansion explicitly
python utils/show_graph.py research --format mermaid --no-xray
```

`main.py` now exports PNG graph files to `visualization/` by default.
Use `--graph-format mermaid` or `--graph-format html png` to change or extend the exported formats, or `--no-graph-output` to disable this behavior.
The exported `research` graph expands its subgraphs by default so the top-level pipeline shows the full flow.

### Paper status lifecycle

```
pending  →  classified  →  analyzed
```

---

## Pipeline (describe mode)

```
user description (natural language)
        │
        ▼
  problem_analysis          LLM (DeepSeek) → required_keywords + optional_keywords
        │
        ▼
  merge_keywords            required + optional → single keyword list
        │
        ▼
  literature_search         arXiv / Semantic Scholar / OpenAlex (parallel per-keyword OR search)
        │
        ▼
  dedup_papers              Cross-source dedup before persistence
        │
        ▼
  filter_papers    GLM-4.7-FlashX filters out off-topic papers using title/abstract
        │
        ▼
  save_to_db                SQLite dedup & persist
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

## API Keys (.env)

Copy `.env.example` to `.env` and fill in your keys:

```
S2_API_KEY=...          # Semantic Scholar — apply at https://www.semanticscholar.org/product/api
DEEPSEEK_API_KEY=...    # DeepSeek — https://platform.deepseek.com/
DEEPSEEK_MODEL=deepseek-chat
DEEPSEEK_BASE_URL=https://api.deepseek.com
OPENAI_API_KEY=...      # OpenAI — https://platform.openai.com/
OPENAI_MODEL=gpt-4o-mini
OPENAI_BASE_URL=https://api.openai.com/v1
GLM_API_KEY=...         # Zhipu GLM — used for post-search relevance filtering
GLM_MODEL=GLM-4.7-FlashX
GLM_BASE_URL=https://open.bigmodel.cn/api/paas/v4/
LLM_PROVIDER=deepseek   # deepseek | openai | glm
```

`S2_API_KEY` is optional but recommended — without it requests are rate-limited (HTTP 429).  
`DEEPSEEK_API_KEY` is required for `--describe` mode.
`GLM_API_KEY` is required for the post-search relevance filtering step.
All model providers now use the same env naming scheme: `*_API_KEY`, `*_MODEL`, `*_BASE_URL`.

