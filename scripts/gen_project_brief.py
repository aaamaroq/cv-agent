#!/usr/bin/env python
"""Derive docs/PROJECT.md from the repo's own structure.

The chatbot treats this file as a second source of truth (see
cv_chat/prompts.py). To keep it honest, every line is *derived* from files
that exist right now — never hand-written claims about what the project
"will" do. Regenerate it whenever the architecture changes:

    .venv/bin/python scripts/gen_project_brief.py

It parses (it does not import, so it needs no runtime deps):
  - graph.py     → LangGraph node names and edges
  - server.py    → HTTP endpoints
  - ADR/*.md     → decision records (title, status, date)
  - requirements.txt → declared stack
  - docs/deployment-continuation.md → deployment summary bullets

Deliberately excludes volatile signals (timestamps, git log) so the file is
byte-stable for a given repo state and does not dirty the tree on every commit.
"""

import argparse
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "src" / "cv_chat"
ADR_DIR = REPO_ROOT / "ADR"
DOCS = REPO_ROOT / "docs"
OUT = DOCS / "PROJECT.md"
DEPLOYMENT_PATH = DOCS / "deployment-continuation.md"
DEPLOYMENT_HEADING = "## Deployment summary"

NODE_RE = re.compile(r'builder\.add_node\("([^"]+)"')
EDGE_RE = re.compile(r'builder\.add_edge\((START|END|"[^"]+"),\s*(START|END|"[^"]+")\)')
COND_RE = re.compile(r'builder\.add_conditional_edges\("([^"]+)",\s*(\w+)')
ROUTE_MAP = {"route_input": "input_guardrail", "route_output": "output_guardrail"}
ENDPOINT_RE = re.compile(r'@app\.(get|post|put|delete)\("([^"]+)"')
ENV_RE = re.compile(r'os\.getenv\(\s*"([^"]+)",\s*"([^"]*)"')


def _clean(name: str) -> str:
    return name.strip('"')


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def parse_nodes(graph_src: str) -> list[str]:
    return NODE_RE.findall(graph_src)


def parse_edges(graph_src: str) -> list[str]:
    lines = []
    for src, dst in EDGE_RE.findall(graph_src):
        lines.append(f"- {_clean(src)} → {_clean(dst)}")
    for node, router in COND_RE.findall(graph_src):
        targets = ROUTE_MAP.get(router)
        hint = f" (conditional from `{router}`)" if targets else ""
        lines.append(f"- {node} ⇢ branching{hint}")
    return lines


def parse_endpoints(server_src: str) -> list[str]:
    return [f"- `{method.upper()} {path}`" for method, path in ENDPOINT_RE.findall(server_src)]


def parse_env(config_src: str) -> list[str]:
    return [f"- `{var}` (default `{default}`)" for var, default in ENV_RE.findall(config_src)]


def parse_adrs() -> list[str]:
    rows = []
    for adr in sorted(ADR_DIR.glob("*.md")) if ADR_DIR.is_dir() else []:
        title = adr.read_text(encoding="utf-8").splitlines()[0].lstrip("#").strip()
        status = re.search(r"\*\*Status:\*\*\s*(\w+)", _read(adr))
        date = re.search(r"\*\*Date:\*\*\s*([\d-]+)", _read(adr))
        suffix = " · ".join(
            p.group(1) for p in (status, date) if p
        )
        rows.append(f"- **{title}**" + (f" ({suffix})" if suffix else ""))
    return rows


def parse_stack() -> list[str]:
    req = _read(REPO_ROOT / "requirements.txt")
    libs = []
    for line in req.splitlines():
        name = re.split(r"[<>=!\[]", line.strip())[0].strip()
        if name and not name.startswith("#"):
            libs.append(name)
    return [f"- {lib}" for lib in libs]


def parse_deployment() -> list[str]:
    """Extract the ``## Deployment summary`` section verbatim from the notes.

    Returns the non-empty lines of that section (bullets included) up to the
    next heading, or an empty list when the notes or the section are missing.
    """
    lines = _read(DEPLOYMENT_PATH).splitlines()
    for index, line in enumerate(lines):
        if line.strip() == DEPLOYMENT_HEADING:
            collected = []
            for candidate in lines[index + 1 :]:
                if candidate.startswith("## "):
                    break
                if candidate.strip():
                    collected.append(candidate.rstrip())
            return collected
    return []


def build_brief() -> str:
    graph_src = _read(SRC / "graph.py")
    server_src = _read(SRC / "server.py")
    config_src = _read(SRC / "config.py")

    sections = [
        "# Project Notes (generated — do not edit by hand)",
        "",
        "> Derived from the live repo by `scripts/gen_project_brief.py`. These "
        "are facts about what this project *is*, not what it plans to be.",
        "",
        "## What this project is",
        "",
        "An AI-powered portfolio chatbot: a LangGraph agent that answers "
        "recruiters' questions about Adrián Amaro's CV. It calls LLMs through "
        "the OpenRouter gateway and wraps the main model with input and output "
        "guardrails using a separately configurable classifier model. "
        "The assistant you "
        "are reading lives inside this repository.",
        "",
        "## AI-engineering signals in this repo",
        "",
        "- Multi-node LLM orchestration with LangGraph (a compiled agent "
        "subgraph + conditional routing; browser-supplied history keeps each "
        "request stateless).",
        "- Layered input/output guardrails with a separate classifier model "
        "(structured JSON output, fail-open) — see the ADR below.",
        "- Adversarial robustness: prompt-injection and leading-question "
        "handling, verified by an evaluation harness (`scripts/guardrail_probe.py`).",
        "- Token streaming over Server-Sent Events from FastAPI to a React UI.",
        "- OpenRouter serving with independently configurable answer and "
        "guardrail model IDs.",
        "",
        "## Graph",
        "",
        f"**Nodes** ({', '.join(parse_nodes(graph_src))}):",
        "",
        *(f"- `{n}`" for n in parse_nodes(graph_src)),
        "",
        "**Edges:**",
        "",
        *(parse_edges(graph_src) or ["- (none parsed)"]),
        "",
        "## HTTP API",
        "",
        *(parse_endpoints(server_src) or ["- (none parsed)"]),
        "",
        "## Configuration",
        "",
        *(parse_env(config_src) or ["- (none parsed)"]),
        "",
        "## Stack",
        "",
        *(parse_stack() or ["- (none declared)"]),
        "",
        "## Deployment",
        "",
        *(parse_deployment() or ["- (none parsed)"]),
        "",
        "## Decision records",
        "",
        *(parse_adrs() or ["- (none)"]),
        "",
    ]
    return "\n".join(sections)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--stdout", action="store_true", help="print instead of writing docs/PROJECT.md"
    )
    args = parser.parse_args()
    brief = build_brief()
    if args.stdout:
        print(brief)
        return
    DOCS.mkdir(exist_ok=True)
    if OUT.is_file() and OUT.read_text(encoding="utf-8") == brief:
        print(f"{OUT.relative_to(REPO_ROOT)} unchanged")
        return
    OUT.write_text(brief, encoding="utf-8")
    print(f"wrote {OUT.relative_to(REPO_ROOT)} ({len(brief.splitlines())} lines)")


if __name__ == "__main__":
    sys.exit(main())
