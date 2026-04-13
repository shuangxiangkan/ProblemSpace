#!/usr/bin/env python3

from __future__ import annotations

import argparse
import html
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_GRAPH_DIR = PROJECT_ROOT / "visualization"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from literature_search.graph import build_graph as build_literature_search_graph
from problem_analysis.graph import build_problem_analysis_graph
from research.graph import build_research_graph

GRAPH_BUILDERS = {
    "problem_analysis": build_problem_analysis_graph,
    "literature_search": build_literature_search_graph,
    "research": build_research_graph,
}

TEXT_FORMATS = {"ascii", "mermaid", "html"}


def _should_expand_subgraphs(graph_name: str, expand_subgraphs: bool | None) -> bool:
    if expand_subgraphs is not None:
        return expand_subgraphs
    return graph_name == "research"


def _build_html_document(graph_name: str, mermaid_source: str) -> str:
    escaped_source = html.escape(mermaid_source)
    return f"""<!DOCTYPE html>
<html lang=\"en\">
<head>
    <meta charset=\"utf-8\">
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
    <title>{graph_name} graph</title>
    <style>
        body {{
            margin: 0;
            padding: 32px;
            font-family: ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            background: #f7f8fc;
            color: #1f2937;
        }}
        .card {{
            max-width: 1200px;
            margin: 0 auto;
            background: #ffffff;
            border-radius: 16px;
            padding: 24px;
            box-shadow: 0 12px 40px rgba(15, 23, 42, 0.08);
        }}
        h1 {{
            margin-top: 0;
            font-size: 24px;
        }}
        .mermaid {{
            overflow-x: auto;
        }}
    </style>
    <script type=\"module\">
        import mermaid from \"https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs\";
        mermaid.initialize({{ startOnLoad: true, securityLevel: "loose" }});
    </script>
</head>
<body>
    <div class=\"card\">
        <h1>{graph_name}</h1>
        <pre class=\"mermaid\">{escaped_source}</pre>
    </div>
</body>
</html>
"""


def _default_suffix(output_format: str) -> str:
    return {
        "ascii": ".txt",
        "mermaid": ".mmd",
        "html": ".html",
        "png": ".png",
    }[output_format]


def render_graph(
    graph_name: str,
    output_format: str = "mermaid",
    expand_subgraphs: bool | None = None,
) -> str | bytes:
    graph = GRAPH_BUILDERS[graph_name]().get_graph(
        xray=_should_expand_subgraphs(graph_name, expand_subgraphs)
    )
    if output_format == "ascii":
        try:
            return graph.draw_ascii()
        except ImportError as exc:
            raise SystemExit(
                "ASCII rendering requires the optional dependency 'grandalf'. "
                "Install it with: pip install grandalf"
            ) from exc
    if output_format == "mermaid":
        return graph.draw_mermaid()
    if output_format == "html":
        return _build_html_document(graph_name, graph.draw_mermaid())
    if output_format == "png":
        return graph.draw_mermaid_png()
    raise ValueError(f"Unsupported output format: {output_format}")


def write_graph(
    graph_name: str,
    output_path: Path,
    output_format: str = "mermaid",
    expand_subgraphs: bool | None = None,
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    rendered = render_graph(
        graph_name,
        output_format=output_format,
        expand_subgraphs=expand_subgraphs,
    )
    if output_format in TEXT_FORMATS:
        output_path.write_text(rendered, encoding="utf-8")
    else:
        output_path.write_bytes(rendered)
    return output_path


def write_project_graphs(
    output_dir: Path = DEFAULT_GRAPH_DIR,
    graph_names: list[str] | None = None,
    output_formats: list[str] | None = None,
    expand_subgraphs: bool | None = None,
) -> list[Path]:
    selected_graphs = graph_names or sorted(GRAPH_BUILDERS)
    selected_formats = output_formats or ["mermaid"]
    paths: list[Path] = []

    for graph_name in selected_graphs:
        for output_format in selected_formats:
            output_path = output_dir / f"{graph_name}{_default_suffix(output_format)}"
            paths.append(
                write_graph(
                    graph_name,
                    output_path,
                    output_format=output_format,
                    expand_subgraphs=expand_subgraphs,
                )
            )

    return paths


def main() -> None:
    parser = argparse.ArgumentParser(description="Render LangGraph structure for this project.")
    parser.add_argument(
        "graph_name",
        nargs="?",
        choices=sorted(GRAPH_BUILDERS),
        help="Which graph to inspect. Omit to export all graphs.",
    )
    parser.add_argument(
        "--format",
        choices=["ascii", "mermaid", "html", "png"],
        default="mermaid",
        help="Output format",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional file path to save a single rendered graph",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_GRAPH_DIR,
        help="Directory used when exporting all graphs",
    )
    parser.add_argument(
        "--xray",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Expand subgraphs in the rendered output. Defaults to enabled for research.",
    )
    args = parser.parse_args()

    if args.graph_name:
        rendered = render_graph(
            args.graph_name,
            output_format=args.format,
            expand_subgraphs=args.xray,
        )
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            if args.format in TEXT_FORMATS:
                args.output.write_text(rendered, encoding="utf-8")
            else:
                args.output.write_bytes(rendered)
            print(f"Saved {args.graph_name} graph to {args.output}")
            return
        if args.format == "png":
            output_path = args.output_dir / f"{args.graph_name}{_default_suffix(args.format)}"
            write_graph(
                args.graph_name,
                output_path,
                output_format=args.format,
                expand_subgraphs=args.xray,
            )
            print(f"Saved {args.graph_name} graph to {output_path}")
            return
        print(rendered)
        return

    paths = write_project_graphs(
        output_dir=args.output_dir,
        output_formats=[args.format],
        expand_subgraphs=args.xray,
    )
    for path in paths:
        print(path)


if __name__ == "__main__":
    main()
