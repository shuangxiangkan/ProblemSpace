# AutoResearch · ProblemSpace（问题空间探索）

> **目标**：在程序分析领域系统性地发现高价值、低覆盖的研究 idea，将 idea 发现过程视为一个**搜索问题**，而非灵感问题。

核心思路：将 **fuzzing 方法论**迁移到研究 idea 的生成过程中。  
论文 / 方法 = seed · 问题空间分析 = coverage 建模 · idea 变体 = mutation · 新颖性 + 可行性 = oracle。

---

## 项目结构

```
ProblemSpace/
├── main.py                   # 命令行入口
├── requirements.txt
├── papers.db                 # SQLite 文献库（已加入 .gitignore）
├── problem-space.md          # 方法论与设计笔记
│
├── models/                   # LLM 工厂（DeepSeek / OpenAI）
│   └── __init__.py           # get_llm(provider)
│
├── problem_analysis/         # 子模块 1：LLM 关键词提取
│   ├── state.py              # KeywordAnalysisState
│   ├── nodes.py              # analyze_query 节点（DeepSeek 结构化输出）
│   ├── graph.py              # build_problem_analysis_graph()
│   └── __init__.py
│
├── literature_search/        # 子模块 2：文献检索
│   ├── state.py              # PaperRecord、PaperSearchState 数据定义
│   ├── nodes.py              # 检索节点 + 去重 + DeepSeek 相关性过滤 + PDF 下载
│   ├── graph.py              # build_literature_search_graph()
│   ├── storage.py            # SQLite 持久化
│   └── __init__.py
│
└── research/                 # 顶层 pipeline（组合各子模块）
    ├── state.py              # MainResearchState
    ├── graph.py              # build_research_graph()
    └── __init__.py
```

### 规划中的子模块

| 模块 | 功能 |
|---|---|
| `problem_analysis/` | ✅ LLM 从自然语言描述中提取结构化检索关键词 |
| `literature_search/` | ✅ 从 arXiv、Semantic Scholar、OpenAlex 抓取并存储文献 |
| `paper_analysis/` | 🔲 LLM 驱动的文献分类、标签提取、失败模式识别 |
| `idea_generation/` | 🔲 Mutation 算子 — 从盲区和 gap 生成 idea seed |
| `idea_triage/` | 🔲 对 idea 按新颖性 / 可行性 / 可评估性 / 潜在价值打分 |
| `problem_space_map/` | 🔲 构建问题空间的覆盖地图 |

---

## 快速开始

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 复制并填写 API key
cp .env.example .env
```

### describe 模式（推荐）— LLM 自动提取关键词

```bash
# 用自然语言描述研究方向，LLM 自动生成精准的组合关键词
python main.py --describe "dragonfly网络拓扑的容错" --max 10
python main.py --describe "并发程序的变异测试" --max 15 --output results.json
```

### keyword 模式 — 手动指定关键词

```bash
python main.py "dragonfly fault tolerance" "fault-tolerant routing" --max 20
python main.py "fuzzing seed generation" --max 20 --output results.json
```

### 在代码中调用

```python
from literature_search import search, load_papers, update_status

# 执行检索图：arXiv → Semantic Scholar → OpenAlex → 去重 → 相关性过滤 → 写入 SQLite
papers = search(["dragonfly fault tolerance", "fault-tolerant dragonfly"], max_results_per_source=20)

# 从 DB 读取待处理文献，供 LLM 分析
pending = load_papers(status="pending")

# LLM 分类完成后更新状态
update_status(paper["doi"], "classified")
```

### 文献状态流转

```
pending（待处理）  →  classified（已分类）  →  analyzed（已分析）
```

---

## Pipeline（describe 模式）

```
用户自然语言描述
        │
        ▼
  problem_analysis          LLM (DeepSeek) → required_keywords + optional_keywords
        │
        ▼
  merge_keywords            required + optional → 合并关键词列表
        │
        ▼
  literature_search         arXiv → Semantic Scholar → OpenAlex（每个关键词独立搜索，OR 语义）
        │
        ▼
  dedup_papers              跨搜索源去重
        │
        ▼
        filter_papers    使用 DeepSeek 基于原始问题描述和摘要过滤低相关论文
        │
        ▼
  save_to_db                SQLite 去重并持久化
              │
              ▼
        download_pdfs            将过滤后的论文 PDF 下载到 results_save/<run>/pdfs
```

---

## 数据库结构（papers.db）

| 字段 | 说明 |
|---|---|
| `dedup_key` | DOI 或 sha1(title)，唯一约束，防止重复入库 |
| `title / authors / abstract` | 完整元数据 |
| `source` | `arxiv` · `semantic_scholar` · `openalex` |
| `pdf_url` | 开放获取的 PDF 直链（如有） |
| `citation_count` | 来自 Semantic Scholar / OpenAlex |
| `status` | `pending` → `classified` → `analyzed` |
| `search_query` | 检索该文献时使用的关键词 |

推荐使用 [DB Browser for SQLite](https://sqlitebrowser.org/) 或 [TablePlus](https://tableplus.com/) 可视化浏览。

---

## API Keys（.env）

复制 `.env.example` 为 `.env` 并填写：

```
S2_API_KEY=...          # Semantic Scholar — https://www.semanticscholar.org/product/api
DEEPSEEK_API_KEY=...    # DeepSeek — https://platform.deepseek.com/
DEEPSEEK_MODEL=deepseek-chat
DEEPSEEK_BASE_URL=https://api.deepseek.com
OPENAI_API_KEY=...      # OpenAI — https://platform.openai.com/
OPENAI_MODEL=gpt-4o-mini
OPENAI_BASE_URL=https://api.openai.com/v1
LLM_PROVIDER=deepseek   # deepseek | openai
```

`S2_API_KEY` 可选但推荐填写，否则请求会受速率限制（HTTP 429）。  
`DEEPSEEK_API_KEY` 在使用 `--describe` 模式和检索后的相关性过滤步骤中必填。
现在三家模型都统一使用同一套环境变量命名：`*_API_KEY`、`*_MODEL`、`*_BASE_URL`。

