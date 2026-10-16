# ADR 0008: Isolate stream adaptation and coordinate conversation runtime

- **Status:** Accepted
- **Supersedes:** the thread-cap and message-window decisions in ADR 0007
- **Date:** 2026-10-15

## Context

The recent streaming and runtime-limit work left two responsibilities together in
`streaming.py`: interpreting LangGraph's nested event tuples and enforcing the
wire-level token gate, plus maintaining thread retention and trimming persisted
history. The runtime policy also evicted the oldest thread at turn start without
knowing whether that thread still had an active turn, and turns sharing one
`thread_id` had no serialization.

Configuration parsed resource limits but let individual consumers clamp some
values while passing other invalid values further into graph construction.

## Decision

### Stream adapter

Decode LangGraph event tuples into semantic token/verdict events before passing
them to `_TokenGate`. The gate owns only the delivery policy: buffer chatbot
drafts, flush accepted text, discard rejected text and emit restart, and stream
canned deflect/fallback text immediately. Both sync and async paths use the same
decoder and gate. The wire event shapes and `subgraphs=True` contract do not
change.

### Conversation runtime

Move per-thread lifecycle policy into `conversation_runtime.py`. It owns history
trimming, turn serialization, active-thread pinning, and LRU eviction. The parent
graph continues to own the checkpointer; the agent subgraph remains without one
(ADR 0005).

- Sync and async turns share a per-graph, per-thread lock. Async callers wait
  without blocking the event loop, and cancellation while waiting immediately
  releases its reservation.
- A thread is considered in use from reservation until its turn completes,
  including time waiting behind another turn with the same ID.
- Eviction preserves oldest-first LRU order and never removes an in-use thread.
  If the oldest thread is in use, `CV_MAX_THREADS` is a soft limit temporarily;
  idle threads are evicted again once that oldest thread completes.
- History trimming remains best-effort and happens once before each graph turn,
  where the parent checkpointer is available.

### Settings invariants

Validate runtime limits when `Settings` is created: `CV_MAX_THREADS >= 1`,
`CV_HISTORY_WINDOW >= 4`, and `CV_LLM_TIMEOUT_S` must be finite and at least
0.001 seconds (the smallest timeout representable by the SDK's millisecond
setting). Invalid explicit values fail during startup. Defaults are unchanged.

## Consequences

- Changes to LangGraph event shapes are localized in the adapter and can be
  tested independently from the output safety policy.
- Turns for one conversation retain a serial history order, while different
  conversations can still progress independently.
- The thread cap can be exceeded while its oldest conversation is active or
  queued. This favors preserving in-flight state over deleting it; the cap is
  restored by oldest-idle eviction after the active reservation ends.
- Invalid runtime-limit settings fail early instead of being interpreted
  differently by separate consumers.
- LLM timeout, fail-open cleanup, the parent checkpointer, SSE event shapes, and
  guardrail behavior remain unchanged.

## Alternatives considered

- **Keep graph parsing inside `_TokenGate`:** couples transport policy to
  LangGraph's nested event representation and duplicates protocol knowledge in
  the policy module.
- **Evict the oldest thread even while active:** preserves a strict cap but can
  delete checkpoint state while a turn is using it.
- **Reject a new thread whenever all retained threads are active:** enforces a
  hard cap at the cost of failing otherwise valid requests; the soft cap was
  chosen to preserve turn availability.
- **Clamp invalid values downstream:** keeps startup permissive but hides
  configuration mistakes and leaves range policy split across callers.
