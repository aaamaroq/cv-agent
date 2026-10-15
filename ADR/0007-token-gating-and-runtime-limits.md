# ADR 0007: Gate streamed tokens behind the output verdict (and add runtime limits)

- **Status:** Accepted
- **Date:** 2026-10-15

## Context

`server.py` streamed chatbot tokens live to the client via `stream_mode "messages"`.
The output guardrail reviewed the draft *after* its tokens had already left the
server.  A rejected draft (e.g. a system-prompt leak) was readable in the raw SSE
stream by anyone inspecting the connection.

Additionally, the runtime had no defences against unbounded growth:
`MemorySaver` grew forever (client-chosen `thread_id`, no eviction), there was no
LLM request timeout, client disconnects did not cancel in-flight LLM calls, and
`GET /api/health` reported `"ok"` regardless of whether an API key or the CV
source file were actually present.

## Decision

### Token gating

New module `streaming.py` is the single owner of the
"LangGraph events → wire events" translation.  `stream_turn` (sync) and
`astream_turn` (async) share a `_TokenGate` that buffers chatbot tokens until the
`output_guardrail` update lands:

- **Acceptance** (`output_ok True`): buffered tokens are flushed as `{"token"}`
  events.  First-token latency increases by the guardrail review time.
- **Rejection** (`output_ok False`): buffer is discarded, `{"restart": True}` is
  emitted (the React UI already handles this event).
- **Deflect / fallback** (canned text, nothing to review): stream immediately.

Tokens from a rejected draft never reach the wire.  This is a deliberate
security-over-latency trade-off.  An "optimistic streaming with retract" mode
(where tokens stream live and a late rejection triggers a UI rollback) is a
possible future explicit opt-in, not the default.

### Runtime limits

**LLM timeout:**  Both `ChatOpenRouter` instances (chat and guardrail) receive
`timeout` (alias for `request_timeout`, in milliseconds) from the new
`CV_LLM_TIMEOUT_S` setting (default 60 seconds).  The OpenRouter SDK maps this
to `timeout_ms` on its underlying HTTP client.

**Thread cap:**  A `ThreadLRU` in `streaming.py` tracks `thread_id`s.  When a new
thread exceeds the cap (`CV_MAX_THREADS`, default 32), the oldest thread is
evicted and its checkpoint deleted via `checkpointer.delete_thread`.  Eviction is
guarded by `try/except` so it never breaks a turn.

**Message window:**  The `input_guardrail` node trims persisted history to the
last N messages (`CV_HISTORY_WINDOW`, default 24, minimum 4) by emitting
`RemoveMessage` for older messages alongside its usual state update.  This keeps
MemorySaver bounded per thread.  The trim runs once per turn (not per retry),
before the chatbot node, so it does not interfere with the loaded-rewrite logic,
the output-guardrail question extraction, or the retry-note injection.

**Honest health:**  `GET /api/health` now reports `api_key_configured` (bool, never
the key itself), `cv_present`, and `project_notes_present` so callers and
load-balancers can distinguish a live-but-misconfigured instance from a healthy
one.

## Consequences

- First-token latency increases by the guardrail review time (typically a cheap
  classifier call, < 1 s).  The trade-off is explicit and documented.
- `streaming.py` owns the wire contract; `server.py` delegates entirely and only
  handles SSE framing and disconnect-aware cancellation (`astream_turn` +
  `request.is_disconnected()`).
- The three new env vars (`CV_MAX_THREADS`, `CV_HISTORY_WINDOW`,
  `CV_LLM_TIMEOUT_S`) follow the two-arg `os.getenv` shape that
  `scripts/gen_project_brief.py` parses, so `docs/PROJECT.md` will list them
  automatically on the next regeneration.
- `ChatOpenRouter`'s `timeout` is in **milliseconds** (mapping to the SDK's
  `timeout_ms`).  The settings value is in seconds and converted at construction
  time.

## Alternatives considered

- **Optimistic streaming with retract** — stream tokens live and roll back on
  rejection; rejected content is briefly visible.  Rejected by the security
  requirement that unreviewed tokens must never leave the server.
- **Post-hoc SSE filter in `server.py`** — buffer in the route handler instead of
  a dedicated module; couples wire logic to HTTP framing and makes the translation
  harder to test in isolation.
- **`asyncio.wait_for` for LLM timeout** — wraps each call; more granular but
  adds complexity.  The SDK-level `timeout` is simpler and covers the same case.
- **Database-backed checkpointer** — would give durable eviction; overkill for a
  single-instance deployment.  MemorySaver + `delete_thread` is sufficient.