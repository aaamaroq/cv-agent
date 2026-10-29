# ADR 0002: Derived project memory and a grounded output critic

- **Status:** Accepted
- **Date:** 2026-10-14

## Context

Adrián's target role is **AI engineer**, but `cv.md` reads as a Java/backend
CV. The Phase 1 chatbot was grounded only in the CV, so it undersold the most
credible AI signal in the whole portfolio: **the repository itself** (a
LangGraph agent with layered guardrails, a classifier model, local inference
and SSE streaming). Two problems:

1. The assistant could not talk about this project as evidence, because the
   project was not in its source of truth.
2. The output guardrail (`check_output`) saw only `question + answer`, never
   the CV. It could catch negative framing and prompt leaks, but had **nothing
   to fact-check against** — it could not tell a real claim from an invention.

Any fix also has to survive the project **changing constantly**. A hand-written
"about the project" paragraph rots the moment the graph or stack moves, and a
stale claim is a lie — exactly what the guardrails exist to prevent.

## Decision

Two coupled changes:

### 1. `docs/PROJECT.md` — a second source of truth, *derived*, not authored

A script (`scripts/gen_project_brief.py`) generates the file by parsing files
that exist right now:

- `graph.py` → node names and edges (regex, no import)
- `server.py` → HTTP endpoints
- `config.py` → env vars and defaults
- `requirements.txt` → declared stack
- `ADR/*.md` → decision titles, status, date
- `git log --oneline` → recent history

It is regenerated on architecture change (the rule lives in `AGENTS.md`) and,
because the graph is built once at process start (`server.py`), a redeploy
refreshes it. Only what exists is ever written — no aspirational lines.
`prompts.source_of_truth()` returns `cv.md + docs/PROJECT.md`, injected into the
system prompt as grounding.

### 2. The output critic is grounded against that source

`check_output` now takes `source` and prefixes the source of truth to the
classifier call. One new `ok=false` rule: assert a fact/skill/metric/employer/
technology that the source does not back (an overclaim). The main prompt gains a
nudge to phrase the AI connection **itself, only on technical questions** — no
hard-coded mappings, no forced framing.

## Consequences

- **Honest positioning.** The project story refreshes itself; the assistant can
  cite its own architecture as AI-engineering evidence without inventing.
- **Drift is bounded by honesty, not freshness.** A slightly stale `PROJECT.md`
  is caught the same way a fabricated employer is: the critic rejects any claim
  the current source does not support.
- **No brittle overclaim examples.** Overclaim examples and probe markers use
  credentials (`PhD`, `eight years`) that the CV can never acquire, not
  technologies it might legitimately add tomorrow (Kubernetes, Go…). Other
  grounding examples may mention technologies when testing claims about what
  the CV does or does not list.
- **Token cost on a small classifier.** The critic now reads the whole CV +
  brief every call. `gemma3:1b` on local hardware tolerates it but each turn is
  heavier; mitigated by `keep_alive=0` and the one-retry cap already in ADR 0001.
- **Derived prose is limited.** The "what this project is" paragraph is the only
  hand-written block; if it ever diverges from the code, the structured sections
  (nodes/endpoints/deps) are the ground truth.

## Alternatives considered

- **Hand-maintained project description** — simplest, but rots on change and a
  stale claim is a lie; rejected for exactly that reason.
- **RAG over the repository** — retrieves live code, zero drift, but needs a
  vector store, embeddings and more infra than a skateboard phase warrants, and
  on local Ollama the retrieval round-trip adds latency. Revisit when `ADR/`
  outgrows what fits in the prompt.
- **A repo-reading tool in the graph** — lets the bot introspect at query time;
  same latency/complexity cost as RAG for now, deferred as a later experiment.
- **Hard-coded AI mappings in the prompt** ("caching = low-latency serving") —
  over-specified, leaks a fixed framing, and goes stale; replaced by a generic,
  conditional instruction the model phrases itself.
