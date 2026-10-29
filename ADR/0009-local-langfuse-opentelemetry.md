# ADR 0009: Self-host local observability with Langfuse and OpenTelemetry

- **Status:** Accepted
- **Date:** 2026-10-20

## Context

The portfolio chatbot runs LangGraph with OpenRouter-backed answer and
guardrail models, but has no durable trace or latency view. Its FastAPI response
is an SSE stream: graph execution occurs while the response body is being sent.
The application also uses a private, local `cv.md` file and intentionally
discards output-guardrail-rejected drafts before they reach the browser.

## Decision

- Run the app and a self-hosted Langfuse v4 stack together with Docker Compose,
  bound to loopback on the host. Persist Langfuse state in named Docker volumes.
- Build the React assets and Python API into one app image. Mount `cv.md` from
  the host as a read-only file rather than copying it into the image.
- Create an OpenTelemetry server span around each `POST /api/chat` ASGI request,
  including the complete SSE body lifetime. Use Langfuse's LangChain callback
  for the LangGraph run and nested model calls. Export the HTTP span and
  Langfuse observations to the same local Langfuse instance.
- Create one trace per chat turn and use the conversation `thread_id` as the
  Langfuse session ID. Capture model inputs and outputs, including guardrail
  calls, retries, and rejected drafts.
- Record token usage and let Langfuse estimate costs using its model pricing
  definitions. Model selection and current defaults are recorded separately in
  ADR 0012.
- Initialize the local Langfuse user, project, and API keys through environment
  variables. Keep local credentials in an untracked `.env` file.
- Treat telemetry as optional and fail-open: an absent or broken Langfuse
  instance must not stop the chat app.

## Consequences

- Local traces include personal CV context and internal rejected drafts; this
  setup is for personal, local debugging, not public traffic.
- The Compose stack contains the app plus Langfuse's web, worker, PostgreSQL,
  ClickHouse, Redis, and MinIO services. `docker compose down` preserves data;
  `docker compose down -v` deletes it.
- OpenTelemetry provides request-level timing, while the LangChain callback
  captures graph/model details and token usage. Estimated costs depend on
  Langfuse having a matching provider/model price; compare estimates with the
  provider's billing data.
- OpenRouter still receives the prompts required to generate answers. The
  observability data is stored in the local Langfuse instance.

## Alternatives considered

- **Langfuse Cloud:** rejected because the user wants a self-hosted Docker
  deployment as part of the portfolio project.
- **Langfuse callback only:** rejected because it omits a request-level HTTP
  span around the SSE lifecycle.
- **Generic OpenTelemetry LangChain instrumentor:** rejected for this first
  version because the current model is `ChatOpenRouter` and provider-specific
  span/usage support is less certain than Langfuse's LangChain callback.
- **OpenRouter-reported exact cost:** deferred; the first version records
  usage and uses Langfuse model-price estimates rather than adding a separate
  cost ingestion path.
