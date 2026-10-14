# Project Notes (generated — do not edit by hand)

> Derived from the live repo by `scripts/gen_project_brief.py`. These are facts about what this project *is*, not what it plans to be.

## What this project is

An AI-powered portfolio chatbot: a LangGraph agent that answers recruiters' questions about Adrián Amaro's CV. It runs a local LLM through Ollama and wraps the main model with input and output guardrails on a smaller classifier model. The assistant you are reading lives inside this repository.

## AI-engineering signals in this repo

- Multi-node LLM orchestration with LangGraph (StateGraph + conditional routing + a checkpointer).
- Layered input/output guardrails with a separate classifier model (JSON output, fail-open) — see the ADR below.
- Adversarial robustness: prompt-injection and leading-question handling, verified by an evaluation harness (`scripts/guardrail_probe.py`).
- Token streaming over Server-Sent Events from FastAPI to a React UI.
- Local model serving with explicit memory/latency trade-offs.

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

- `CV_MODEL` (default `gemma3:4b`)
- `CV_GUARDRAIL_MODEL` (default `gemma3:1b`)
- `OLLAMA_HOST` (default `http://localhost:11434`)
- `CV_TEMPERATURE` (default `0.3`)

## Stack

- langchain
- langchain-ollama
- langgraph
- fastapi
- uvicorn

## Decision records

- **ADR 0001: Input and output guardrails as graph nodes** (Accepted · 2026-10-07)
- **ADR 0002: Derived project memory and a grounded output critic** (Accepted · 2026-10-14)

## Recent history

- a092d7b Add input/output guardrail nodes to chat graph
- f4b7865 Add Phase 1 skateboard: LangGraph CV chatbot with FastAPI + React UI
- bb61e74 Add project manifest
