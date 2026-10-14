# ADR 0005: Wrap the turn in a compiled agent subgraph

- **Status:** Accepted
- **Supersedes:** the "defer the guardrail subgraph" clause of ADR 0003. The
  positioning-measured-not-gated decision of ADR 0003 still stands.
- **Date:** 2026-10-14

## Context

The ADR 0003 deferral said the guardrail subgraph needed a live probe run before
it could be done, because nesting `output_guardrail` would hide its update from
the parent stream and silently break the SSE `restart` signal the server reads.

Two things changed since then:

- A **streaming oracle** (`tests/test_stream_contract.py`) now locks the exact
  event shapes `server.py` depends on (restart key, and `deflect`/`fallback`/
  `chatbot` token node names) using a stubbed LLM — so the refactor can be
  validated **offline**, no provider calls.
- Measuring LangGraph directly showed that streaming with `subgraphs=True` keeps
  inner node names in `messages` metadata and surfaces inner-node updates under a
  nested namespace, so the contract can be preserved if consumers opt in.

The user explicitly wants to go deeper on LangGraph; composition via subgraphs is
core LangGraph vocabulary worth adopting deliberately here.

## Decision

Compile the whole turn (input guardrail → chatbot → output guardrail, with the
retry loop and the `deflect`/`fallback` terminals) into an `agent` subgraph with
**no checkpointer**, and wrap it in a thin parent graph that owns the
checkpointer:

```
parent: START → agent(subgraph) → END
agent:  (unchanged internal guardrail/generate/review/retry topology)
```

Consequences for consumers (`server.py`, `scripts/guardrail_probe.py`): stream
with `subgraphs=True` and unpack the namespace tuple first —
`for _ns, update in stream(..., stream_mode="updates", subgraphs=True)` for the
probe, `for _ns, mode, data in stream(..., stream_mode=["messages","updates"],
subgraphs=True)` for the SSE server. The `output_guardrail` restart signal and
the `chatbot`/`deflect`/`fallback` token names survive under the nested namespace.

## Consequences

- The streaming contract shifted from 2-tuples to namespace-prefixed tuples; the
  oracle encodes exactly which shape every consumer must handle, so a future
  regression (dropping `subgraphs=True`, or a deeper nesting) fails offline.
- The parent is a near-empty wrapper; the real logic and reuse unit is `agent`.
  Checkpointing stays on the parent, so threads and history are unchanged.
- The `graph` section of `docs/PROJECT.md` still lists the five logical nodes:
  the generator only reads `builder.add_node(...)`, so the `agent` wrapper is
  correctly treated as an implementation detail, not a new public node.

## Alternatives considered

- **Keep the flat graph** — zero consumer changes; rejected by the user's wish to
  adopt LangGraph composition now that it is verifiable offline.
- **Extract only the guardrails into a subgraph** — impossible cleanly, because
  the retry loop `output_guardrail ⇢ chatbot` crosses the subgraph boundary, so
  `chatbot` would have to be excluded from the cycle.
- **Switch consumers to `get_state` polling instead of streaming** — loses the
  token streaming the UI is built around.
