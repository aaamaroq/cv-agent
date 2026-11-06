# Project Notes (generated — do not edit by hand)

> Derived from the live repo by `scripts/gen_project_brief.py`. These are facts about what this project *is*, not what it plans to be.

## What this project is

An AI-powered portfolio chatbot: a LangGraph agent that answers recruiters' questions about Adrián Amaro's CV. It calls LLMs through the OpenRouter gateway and wraps the main model with input and output guardrails using a separately configurable classifier model. The assistant you are reading lives inside this repository.

## AI-engineering signals in this repo

- Multi-node LLM orchestration with LangGraph (a compiled agent subgraph + conditional routing; browser-supplied history keeps each request stateless).
- Layered input/output guardrails with a separate classifier model (structured JSON output, fail-open) — see the ADR below.
- Adversarial robustness: prompt-injection and leading-question handling, verified by an evaluation harness (`scripts/guardrail_probe.py`).
- Token streaming over Server-Sent Events from FastAPI to a React UI.
- OpenRouter serving with independently configurable answer and guardrail model IDs.

## Graph

**Nodes** (input_guardrail, chatbot, output_guardrail, deflect, fallback):

- `input_guardrail`
- `chatbot`
- `output_guardrail`
- `deflect`
- `fallback`

**Edges:**

- START → input_guardrail
- chatbot → output_guardrail
- deflect → END
- fallback → END
- input_guardrail ⇢ branching (conditional from `route_input`)
- output_guardrail ⇢ branching (conditional from `route_output`)

## HTTP API

- `GET /api/health`
- `GET /api/warmup`
- `GET /api/profiles/{profile_id}`
- `POST /api/chat`
- `GET /p/{profile_id}`

## Configuration

- `CV_PATH` (default `cv.md`)
- `CV_PROFILES_DIR` (default `profiles`)
- `CV_MODEL` (default `openai/gpt-oss-20b`)
- `CV_GUARDRAIL_MODEL` (default `openai/gpt-oss-20b`)
- `OPENROUTER_API_KEY` (default ``)
- `CV_TEMPERATURE` (default `0.3`)
- `CV_HISTORY_WINDOW` (default `24`)
- `CV_LLM_TIMEOUT_S` (default `60`)
- `CV_LANGFUSE_ENABLED` (default `true`)
- `LANGFUSE_PUBLIC_KEY` (default ``)
- `LANGFUSE_SECRET_KEY` (default ``)
- `LANGFUSE_BASE_URL` (default ``)

## Stack

- langchain
- langchain-openrouter
- langgraph
- fastapi
- uvicorn
- langfuse
- opentelemetry-api

## Deployment

The bullets in this section are parsed verbatim into `docs/PROJECT.md` by
`scripts/gen_project_brief.py`; keep them factual and stable.
- Frontend: React/Vite app served by Vercel; `web/vercel.json` proxies `/api/*`
  to the backend on the same origin.
- Backend: FastAPI image built from `Dockerfile.backend` and served on Google
  Cloud Run with minimum 0 and maximum 1 instances (scales to zero).
- Image delivery: built with Cloud Build (`gcloud builds submit`) and pushed to
  Artifact Registry.
- Content: a private Cloud Storage bucket mounted read-only at
  `/mnt/cv-content` holds `cv.md` and `profiles/*.json`.
- Secrets: `OPENROUTER_API_KEY` comes from Secret Manager and is mapped into
  the Cloud Run service.
- IAM: the Cloud Run runtime service account holds `roles/storage.objectViewer`
  on the content bucket.
- Observability: Cloud Run writes request and error logs to Cloud Logging and
  metrics to Cloud Monitoring by default; Langfuse tracing is optional and
  controlled by `CV_LANGFUSE_ENABLED`.

## Decision records

- **ADR 0001: Input and output guardrails as graph nodes** (Accepted · 2026-10-07)
- **ADR 0002: Derived project memory and a grounded output critic** (Accepted · 2026-10-14)
- **ADR 0003: Positioning is measured, not gated; subgraph extraction deferred** (Accepted · 2026-10-14)
- **ADR 0004: Migrate inference from local Ollama to OpenRouter** (Accepted · 2026-10-14)
- **ADR 0005: Wrap the turn in a compiled agent subgraph** (Accepted · 2026-10-14)
- **ADR 0006: Keep the loaded rewrite as the stored history** (Accepted · 2026-10-15)
- **ADR 0007: Gate streamed tokens behind the output verdict (and add runtime limits)** (Accepted · 2026-10-15)
- **ADR 0008: Isolate stream adaptation and coordinate conversation runtime** (Accepted · 2026-10-15)
- **ADR 0009: Self-host local observability with Langfuse and OpenTelemetry** (Accepted · 2026-10-20)
- **ADR 0010: Hot reload for local Docker development** (Accepted · 2026-10-26)
- **ADR 0011: Portfolio voice and local RAG evaluation (implementation pending)** (Accepted · 2026-10-26)
- **ADR 0012: Update OpenRouter model defaults** (Accepted · 2026-10-29)
- **ADR 0013: Use Mistral Nemo for answers and Llama for guardrails** (Accepted · 2026-11-04)
- **ADR 0014: Curated recruiter profiles without conversation resumption** (Accepted · 2026-11-04)
- **ADR 0015: Offer-grounded recruiter profiles with an unchanged general portfolio** (Accepted · 2026-11-04)
- **ADR 0016: Stateless chat turns and Cloud Storage content** (Accepted · 2026-11-05)
- **ADR 0017: Use gpt-oss-20b for answers and guardrail checks** (Accepted · 2026-11-05)
