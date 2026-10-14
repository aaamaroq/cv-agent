# ADR 0004: Migrate inference from local Ollama to OpenRouter

- **Status:** Accepted
- **Supersedes:** the provider-specific supporting decisions of ADR 0001
  (`format="json"` and `keep_alive=0`, both Ollama-only). The guardrail-as-graph-
  nodes design, the fail-open policy and the verdict taxonomy still stand.
- **Date:** 2026-10-14

## Context

Through Phase 1 the assistant ran entirely on a local Ollama (`gemma3:4b` chat +
`gemma3:1b` classifier). That gave a "no API keys" story and the `keep_alive=0`
RAM trade-off in ADR 0001, but it also capped what we could do:

- The classifier was a tiny local model, so the hand-calibrated `format="json"`
  + regex `extract_json` path was the only reliable structured-output option
  (ADR 0001 had to fight a JSON-anchoring bug because of it).
- Model choice was limited to whatever fit the local machine.

The goal is now explicitly **AI-engineering** work and deeper **LangGraph**
learning: reliable structured output, per-request model routing, and the
provider/agent abstraction LangChain exposes. The user chose a **total
replacement** of the backend (not a switchable option).

## Decision

Use the dedicated `langchain-openrouter` integration (`ChatOpenRouter`) for
both the chat model and the guardrail classifier, replacing `ChatOllama`.

- **Models** (cheapest that are real and OpenAI-compatible, overridable by env):
  - chat → `google/gemma-4-31b-it:free`
  - guardrail classifier → `deepseek/deepseek-chat:free`
- **Key handling**: `OPENROUTER_API_KEY` is read into `Settings.api_key`.
  `ChatOpenRouter` *validates the key at construction* (unlike Ollama, which was
  lazy), so `build_graph` passes a non-secret placeholder (`"offline-placeholder"`)
  when the key is empty. The graph therefore still builds and imports **without a
  key and without network**; a real call is required to hit the endpoint, which
  is what an empty/placeholder key correctly fails against.
- **Requirements**: `langchain-ollama` → `langchain-openrouter`.
- The two Ollama-only constructor args (`format="json"`, `keep_alive`) are
  dropped. Interim guardrail JSON is prompt-instructed + parsed by the tolerant
  `extract_json`; structured output via `with_structured_output` is the next
  step now that the backend supports it.

## Consequences

- Guardrails can use native structured output (planned in ADR 0003's follow-up);
  `ChatOpenRouter` supports tool calling + structured output per its docs.
- Live runs now **require** a key and make network calls; the offline "no keys"
  claim is gone. Free-tier limits apply: ~20 requests/min, and the `:free`
  models are capped (50/day untopped, 1000/day after a one-time $10 credit) —
  which directly bounds how often `scripts/guardrail_probe.py` can run.
- The `keep_alive`/local-RAM rationale no longer applies and is removed from
  the generated project memory.
- Secrets: the key is only ever read from the environment and passed through as
  `SecretStr`-style config; never logged, never committed, never in
  `docs/PROJECT.md`.

## Alternatives considered

- **Switchable provider (env `CV_PROVIDER`)** — would preserve the local-first
  story, but the user explicitly chose a total replacement; more surface area.
- **`ChatOpenAI` with `base_url=https://openrouter.ai/api/v1`** — works, but it
  is the legacy path; `langchain-openrouter` is the current, structured-output-
  aware integration for a current LangChain (we are on 1.4.3).
