# Project Notes (generated — do not edit by hand)

> Derived from the live repo by `scripts/gen_project_brief.py`. These are facts about what this project *is*, not what it plans to be.

## What this project is

An AI-powered portfolio chatbot: a LangGraph agent that answers recruiters' questions about Adrián Amaro's CV. It calls LLMs through the OpenRouter gateway and wraps the main model with input and output guardrails on a separate, cheaper classifier model. The assistant you are reading lives inside this repository.

## AI-engineering signals in this repo

- Multi-node LLM orchestration with LangGraph (a compiled agent subgraph + conditional routing + a checkpointer on the parent).
- Layered input/output guardrails with a separate classifier model (structured JSON output, fail-open) — see the ADR below.
- Adversarial robustness: prompt-injection and leading-question handling, verified by an evaluation harness (`scripts/guardrail_probe.py`).
- Token streaming over Server-Sent Events from FastAPI to a React UI.
- Provider-agnostic LLM serving through OpenRouter (one endpoint, many models, per-request model routing for the cheap guardrail classifier).

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
- `POST /api/chat`

## Configuration

- `CV_MODEL` (default `google/gemma-4-31b-it:free`)
- `CV_GUARDRAIL_MODEL` (default `deepseek/deepseek-chat:free`)
- `CV_TEMPERATURE` (default `0.3`)
- `CV_MAX_THREADS` (default `32`)
- `CV_HISTORY_WINDOW` (default `24`)
- `CV_LLM_TIMEOUT_S` (default `60`)

## Stack

- langchain
- langchain-openrouter
- langgraph
- fastapi
- uvicorn

## Decision records

- **ADR 0001: Input and output guardrails as graph nodes** (Accepted · 2026-10-07)
- **ADR 0002: Derived project memory and a grounded output critic** (Accepted · 2026-10-14)
- **ADR 0003: Positioning is measured, not gated; subgraph extraction deferred** (Accepted · 2026-10-14)
- **ADR 0004: Migrate inference from local Ollama to OpenRouter** (Accepted · 2026-10-14)
- **ADR 0005: Wrap the turn in a compiled agent subgraph** (Accepted · 2026-10-14)
- **ADR 0006: Keep the loaded rewrite as the stored history** (Accepted · 2026-10-15)
- **ADR 0007: Gate streamed tokens behind the output verdict (and add runtime limits)** (Accepted · 2026-10-15)
- **ADR 0008: Isolate stream adaptation and coordinate conversation runtime** (Accepted · 2026-10-15)
