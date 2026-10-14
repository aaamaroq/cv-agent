# CV Web — AI-Powered Interactive Portfolio

Conversational chatbot over Adrián's CV. **Phase 1 (🛹 Skateboard):** LangGraph
with a `chatbot` node wrapped in input/output guardrail nodes (see
`ADR/0001-input-output-guardrails.md`), CV + derived project notes injected into
the system prompt, FastAPI + React/Tailwind UI, LLMs via OpenRouter.

## Stack

- **Backend:** Python, LangChain, LangGraph (StateGraph + MemorySaver), FastAPI
- **Frontend:** Vite, React, Tailwind CSS v4
- **Models:** via OpenRouter (`ChatOpenRouter`) — a free chat model plus a
  cheaper classifier for the guardrails

## Run

Terminal 1 — backend (port 8000):

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
export OPENROUTER_API_KEY="sk-or-..."   # required for live runs
PYTHONPATH=src .venv/bin/uvicorn cv_chat.server:app --reload
```

Terminal 2 — frontend (port 5173):

```bash
cd web && npm install && npm run dev
```

Open http://localhost:5173

## Configuration

| Env var | Default | Purpose |
|---|---|---|
| `CV_MODEL` | `google/gemma-4-31b-it:free` | OpenRouter slug for the chat model |
| `CV_GUARDRAIL_MODEL` | `deepseek/deepseek-chat:free` | Cheaper classifier for input/output guardrails |
| `OPENROUTER_API_KEY` | *(empty)* | OpenRouter key; required for live runs (graph still builds offline) |
| `CV_TEMPERATURE` | `0.3` | Sampling temperature |

## Project layout

```
cv.md                    # CV content (source of truth → system prompt)
docs/PROJECT.md          # GENERATED project memory (see below — never hand-edit)
AGENTS.md                # rules for agents/humans working on this repo
ADR/                     # architecture decision records
scripts/
  gen_project_brief.py   # derives docs/PROJECT.md from the live repo
  guardrail_probe.py     # guardrail evaluation ladder
src/cv_chat/
  config.py              # settings
  prompts.py             # loads cv.md + docs/PROJECT.md into the system prompt
  guardrails.py          # input/output guardrail prompts + checks
  graph.py               # LangGraph: guardrail nodes + agent subgraph + checkpointer
  server.py              # FastAPI: POST /api/chat (SSE streaming)
web/                     # Vite + React + Tailwind UI
```

## Project memory

`docs/PROJECT.md` is a second source of truth the assistant and its output
guardrail read at runtime. It is **derived from the repo** (graph nodes, API,
config, ADRs, deps), so it can only describe what the project actually *is* —
never a planned feature. Regenerate it after any architecture change:

```bash
.venv/bin/python scripts/gen_project_brief.py
```
