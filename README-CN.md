# AutoResearch · ProblemSpace（问题空间探索）

> **目标**：在程序分析领域系统性地发现高价值、低覆盖的研究 idea，将 idea 发现过程视为一个**搜索问题**，而非灵感问题。

核心思路：将 **fuzzing 方法论**迁移到研究 idea 的生成过程中。
论文 / 方法 = seed · 问题空间分析 = coverage 建模 · idea 变体 = mutation · 新颖性 + 可行性 = oracle。

---

## 项目结构

```
ProblemSpace/
├── problem-space.md          # 方法论与设计笔记
├── main.py                   # 命令行入口
├── requirements.txt
├── papers.db                 # SQLite 文献库（已加入 .gitignore）
│
└── literature_search/        # 子模块 1：文献检索
    ├── state.py              # PaperRecord、PaperSearchState 数据定义
    ├── nodes.py              # arXiv / Semantic Scholar / OpenAlex 检索节点
    ├── graph.py              # LangGraph 检索图
    ├── storage.py            # SQLite 持久化 + 去重
    └── __init__.py
```

### 规划中的子模块

| 模块 | 功能 |
|---|---|
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

# 搜索文献并保存到 papers.db
python main.py "program analysis" "static analysis" --max 30

# 导出为 JSON 方便临时查看
python main.py "fuzzing seed generation" --max 20 --output results.json
```

### 在代码中调用

```python
from literature_search import search, load_papers, update_status

# 执行检索图：arXiv → Semantic Scholar → OpenAlex → 写入 SQLite
papers = search(["program analysis", "taint analysis"], max_results_per_source=30)

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

## Semantic Scholar API Key

免费 tier 有速率限制（HTTP 429）。可在 <https://www.semanticscholar.org/product/api> 申请免费 key，通过环境变量注入：

```bash
export S2_API_KEY="<your_key>"
```
