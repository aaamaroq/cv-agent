# AGENTS.md — how to work on this repo

Guidance for AI coding agents (and humans) making changes here. Read this
before touching code.

## What this project is

A LangGraph agent that answers recruiters' questions about Adrián Amaro's CV,
with a local Ollama LLM wrapped in input/output guardrails, served by FastAPI
with a React/Tailwind UI. See `README.md` and `MANIFEST.MD` for the vision and
the phased "vehicle" roadmap (skateboard → ...).

## The one non-obvious rule: keep the project memory honest

`docs/PROJECT.md` is a **second source of truth** the chatbot and its output
guardrail read at runtime (see `src/cv_chat/prompts.py`). It is **generated**,
never hand-edited. Every line is derived from files that exist right now, so
the assistant cannot claim a capability the repo does not actually have.

> **Whenever you change the architecture, you MUST regenerate it:**
>
> ```bash
> .venv/bin/python scripts/gen_project_brief.py
> ```

Concretely, regenerate when you add/remove/rename:

- a LangGraph node or edge (`src/cv_chat/graph.py`)
- an HTTP endpoint (`src/cv_chat/server.py`)
- a config env var (`src/cv_chat/config.py`)
- a dependency (`requirements.txt`)
- an architecture decision record (`ADR/*.md`)

It is safe to run often (idempotent). Treat a stale `docs/PROJECT.md` as a bug.

## Grounding / honesty

- The chatbot may only speak from `cv.md` + `docs/PROJECT.md`. Never invent
  employers, dates, projects, models, or metrics, and **never present a planned
  or aspirational feature as already built** — that is why the brief is derived,
  not written by hand.
- The output guardrail (`src/cv_chat/guardrails.py`) grounds every claim against
  the same sources via `source_of_truth()`. If you tighten the main prompt,
  mirror the intent in the guardrail rubric.

## Architecture decisions

Record meaningful design choices as `ADR/NNNN-title.md` (status, date, context,
decision, consequences, alternatives). The ADRs are injected into the project
memory and are the durable "why" behind the code. Supersede old ADRs rather
than rewriting history.

## Guardrails are load-bearing

`src/cv_chat/guardrails.py` classifies hostile/leading input and reviews
output for overclaims, leaks, and negativity. They are **fail-open**: a broken
classifier must never take the chat down. When you edit guardrail prompts, keep
the few-shot contrast pairs (they calibrate a small classifier far better than
abstract rules do) and run the probe:

```bash
.venv/bin/python scripts/guardrail_probe.py          # full ladder
.venv/bin/python scripts/guardrail_probe.py --list    # cases only
```

Prefer extending `scripts/guardrail_probe.py` with a new case over eyeballing a
change.

## Workflow

- Small, working increments over big leaps (the "vehicle" metaphor in
  `MANIFEST.MD`). Keep an operational product at every step.
- Clean, idiomatic Python; lean on LangChain/LangGraph native features.
- Backend: `PYTHONPATH=src .venv/bin/uvicorn cv_chat.server:app --reload`
- Frontend: `cd web && npm run dev`
- A local Ollama must be reachable at `OLLAMA_HOST` for live runs; unit-style
  graph construction does not need it.
- Offline tests (no LLM, stdlib `unittest`):
  `PYTHONPATH=src .venv/bin/python -m unittest discover -s tests`

## Learned preferences

(Add entries here as conventions settle. None recorded yet beyond the rules above.)
