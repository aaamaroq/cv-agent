# CV Web — AI-Powered Interactive Portfolio

Conversational chatbot over Adrián's CV. **Phase 1 (🛹 Skateboard):** LangGraph
with a `chatbot` node wrapped in input/output guardrail nodes (see
`ADR/0001-input-output-guardrails.md`), CV + derived project notes injected into
the system prompt, FastAPI + React/Tailwind UI, LLMs via OpenRouter.

## Stack

- **Backend:** Python, LangChain, stateless LangGraph turns, FastAPI
- **Frontend:** Vite, React, Tailwind CSS v4
- **Models:** via OpenRouter (`ChatOpenRouter`); `CV_MODEL` and
  `CV_GUARDRAIL_MODEL` select the answer and guardrail models. The answer model
  defaults to `mistralai/mistral-nemo`; the guardrail model defaults to
  `meta-llama/llama-3.1-8b-instruct`.
- **Observability:** self-hosted Langfuse with OpenTelemetry request spans and
  LangChain/LangGraph callbacks

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

### Personalized recruiter link

The root portfolio keeps the general recruiter greeting, questions, and answer
context; it never inherits criteria from a personalized route. The demo company
profile is available at `http://localhost:8000/p/acme` when using the packaged
app, or `http://localhost:5173/p/acme` in the Vite development stack. It changes
the chat greeting, suggested questions, and the emphasis used when answering;
all claims remain grounded in the CV and project notes. Profiles live in
`profiles/*.json`, are loaded by `src/cv_chat/profiles.py`, and are exposed as
presentation data through `GET /api/profiles/{profile_id}`. Profiles are read on
demand so Cloud Run can load reviewed JSON files from its private Cloud Storage
mount; criteria and the evidence map stay server-side.

An anonymized agentic-runtime role demo is also available at
`http://localhost:5173/p/conversational-crm-agentic-runtime` in the development
stack. The title remains the same as the general portfolio, while the friendly
intro, evidence summary, and suggested questions help recruiters assess the role
fit. It does not claim experience with offer requirements that the CV does not
document.

Generate a profile from a local UTF-8 job-offer text file:

```bash
OPENROUTER_API_KEY="sk-or-..." PYTHONPATH=src .venv/bin/python scripts/build_profile.py \
  --id acme-ai-engineer --company Acme --role "AI Engineer" \
  --offer /path/to/job-offer.txt
```

The one-time generator sends the offer, CV, and project notes to the configured
OpenRouter model. It validates exact offer quotes for sanitized criteria and
exact CV/project quotes for mapped evidence, then stores the criteria and the
evidence map for server-side prompting. It does not store the raw offer or the
offer quotes, and `GET /api/profiles/{profile_id}` does not expose the evidence
map. Review the generated profile—especially the direct/related evidence labels
and its positioning—before deploying it. It does not track later changes to
either source; regenerate a profile manually when needed.

The browser keeps up to 11 completed turns in the current page and sends them
with each question. The API and LangGraph graph are stateless, so a Cloud Run
restart does not interrupt context while the page remains open. Reloading starts
a fresh conversation.

### Docker development mode (automatic updates)

For code changes, use the development Compose overlay instead of the packaged
app command above:

```bash
docker compose -f compose.yaml -f compose.dev.yaml up --build
```

Open http://localhost:5173. Frontend changes update through Vite; edits in
`src/` or `docs/` restart the API automatically. Stop with `Ctrl+C`. Changes to
dependencies still require rebuilding the relevant image with `--build`.

## Local Docker stack with Langfuse

The local Compose stack runs the React UI + FastAPI app and a self-hosted
Langfuse instance. Chat traces include the full model inputs/outputs, guardrail
calls, retries, and rejected drafts, so use this setup only for your own local
debugging. OpenRouter still receives the prompts used to generate responses.

1. Create the private CV file if needed:

   ```bash
   cp cv.md.sample cv.md
   ```

2. Copy `.env.example` to `.env`. Add your `OPENROUTER_API_KEY`, set the local
   Langfuse user password and project API keys (`pk-lf-...` and `sk-lf-...`),
   and replace the secret placeholders. Generate 64-character hex secrets with
   `openssl rand -hex 32`; use a different value for `ENCRYPTION_KEY`,
   `NEXTAUTH_SECRET`, `SALT`, and each database/storage password. The Langfuse
   project public/secret keys in `.env` are also used by the app.

3. Build and start the complete stack:

   ```bash
   docker compose up --build
   ```

   Open the chat at http://localhost:8000 and Langfuse at
   http://localhost:3000. The initial Langfuse account and project are created
   from the `.env` values on the first start. All published ports bind to
   `127.0.0.1`.

`docker compose down` stops the services while keeping traces and databases in
named volumes. `docker compose down -v` also deletes that persisted Langfuse
data. The `cv.md` host file is mounted read-only and is not copied into the app
image.

The chat trace groups each turn under its conversation `thread_id`. OpenTelemetry
captures request latency across the full SSE response; the Langfuse callback
captures the LangGraph run and nested model calls, including token usage. Cost
estimates depend on Langfuse having current pricing for the selected provider
and model; compare them with OpenRouter billing. If Langfuse is disabled or
unavailable, the chat continues without telemetry.

## First run (collaborators)

`cv.md` is intentionally gitignored — it contains personal data — but it is
required at runtime and by the tests. Copy the template and fill it in with
your own details:

```bash
cp cv.md.sample cv.md
```

## Configuration

| Env var | Default | Purpose |
|---|---|---|
| `CV_MODEL` | `mistralai/mistral-nemo` | OpenRouter slug for the chat model |
| `CV_GUARDRAIL_MODEL` | `meta-llama/llama-3.1-8b-instruct` | Model ID for input/output guardrails; configurable separately from the chat model |
| `OPENROUTER_API_KEY` | *(empty)* | OpenRouter key; required for live runs (graph still builds offline) |
| `CV_TEMPERATURE` | `0.3` | Sampling temperature |
| `CV_HISTORY_WINDOW` | `24` | Maximum messages accepted as browser-supplied conversation context |
| `CV_LLM_TIMEOUT_S` | `60` | Timeout for chat and guardrail model calls |
| `CV_PATH` | `cv.md` | CV source path; Cloud Run uses the read-only Cloud Storage mount |
| `CV_PROFILES_DIR` | `profiles` | Curated profile directory; Cloud Run uses the read-only Cloud Storage mount |
| `CV_LANGFUSE_ENABLED` | `true` | Enables local Langfuse tracing when the credentials and base URL are set |
| `LANGFUSE_PUBLIC_KEY` | *(empty)* | Langfuse project public key |
| `LANGFUSE_SECRET_KEY` | *(empty)* | Langfuse project secret key |
| `LANGFUSE_BASE_URL` | *(empty)* | Langfuse API base URL; Compose uses `http://langfuse-web:3000` internally |

## Project layout

```
cv.md                    # CV content (source of truth → system prompt)
docs/PROJECT.md          # GENERATED project memory (see below — never hand-edit)
AGENTS.md                # rules for agents/humans working on this repo
ADR/                     # architecture decision records
scripts/
  build_profile.py      # generates reviewed recruiter profiles from job offers
  gen_project_brief.py   # derives docs/PROJECT.md from the live repo
  guardrail_probe.py     # guardrail evaluation ladder
  profiles/                 # reviewed profile JSON; never store raw offers here
src/cv_chat/
  config.py              # settings
  prompts.py             # loads CV, project notes, and server-resolved profile focus
  guardrails.py          # input/output guardrail prompts + checks
  graph.py               # LangGraph: guardrail nodes + stateless agent subgraph
  server.py              # FastAPI: endpoints, SSE streaming, and HTTP tracing
  observability.py        # Optional OpenTelemetry + Langfuse integration
web/                     # Vite + React + Tailwind UI
Dockerfile.backend       # Cloud Run API image; frontend is deployed separately
compose.yaml              # Local app + self-hosted Langfuse services
```

## Cloud deployment

The production split deployment uses Vercel for `web/` and Cloud Run for the
FastAPI API. Cloud Run mounts the private CV/profile bucket read-only; see
[`docs/deployment-continuation.md`](docs/deployment-continuation.md) for the
environment and deployment steps.

## Project memory

`docs/PROJECT.md` is a second source of truth the assistant and its output
guardrail read at runtime. It is **derived from the repo** (graph nodes, API,
config, ADRs, deps), so it can only describe what the project actually *is* —
never a planned feature. Regenerate it after any architecture change:

```bash
.venv/bin/python scripts/gen_project_brief.py
```
