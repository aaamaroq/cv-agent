"""Wire-level translation of LangGraph events into client SSE payloads.

Public interface:
  stream_turn(graph, message, thread_id)  -> Iterator[dict]   (sync)
  astream_turn(graph, message, thread_id) -> AsyncIterator[dict] (async)

Both yield the same wire events and share the token-gating logic via
``_TokenGate``: chatbot tokens are buffered and only flushed once the
output guardrail emits an acceptance update; on rejection the buffer is
discarded and ``{"restart": True}`` is emitted.  ``deflect`` / ``fallback``
(canned text, nothing to review) stream immediately.

A module-level ``ThreadLRU`` evicts the oldest thread_id when the cap is
exceeded, deleting its checkpoint via ``checkpointer.delete_thread``.
"""

from __future__ import annotations

from collections import OrderedDict
from typing import Any, AsyncIterator, Iterator

from langchain_core.messages import HumanMessage
from langgraph.graph.message import RemoveMessage

from .config import get_settings

CHATBOT_NODE = "chatbot"
IMMEDIATE_NODES = frozenset({"deflect", "fallback"})


# ---------------------------------------------------------------------------
# Wire-event helpers
# ---------------------------------------------------------------------------

def _chunk_text(chunk: object) -> str:
    content = getattr(chunk, "content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(p.get("text", "") for p in content if isinstance(p, dict))
    return ""


class _TokenGate:
    """Buffers chatbot tokens until the output verdict lands."""

    def __init__(self) -> None:
        self._buffer: list[str] = []

    def feed(self, event: tuple) -> list[dict[str, Any]]:
        _namespace, mode, data = event
        out: list[dict[str, Any]] = []
        if mode == "updates":
            update = data.get("output_guardrail") if isinstance(data, dict) else None
            if isinstance(update, dict):
                if update.get("output_ok") is False:
                    self._buffer.clear()
                    out.append({"restart": True})
                else:
                    out.extend({"token": t} for t in self._buffer)
                    self._buffer.clear()
            return out
        # messages mode
        chunk, metadata = data
        node = metadata.get("langgraph_node")
        text = _chunk_text(chunk)
        if not text:
            return out
        if node == CHATBOT_NODE:
            self._buffer.append(text)
        elif node in IMMEDIATE_NODES:
            out.append({"token": text})
        return out

    def finish(self) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        if self._buffer:
            self._buffer.clear()
            out.append({"restart": True})
        out.append({"done": True})
        return out


# ---------------------------------------------------------------------------
# Thread LRU
# ---------------------------------------------------------------------------

class ThreadLRU:
    """Bounded LRU of thread_ids; eviction prevents unbounded MemorySaver growth."""

    def __init__(self, max_threads: int) -> None:
        self._max = max(1, int(max_threads))
        self._order: OrderedDict[str, None] = OrderedDict()

    def touch(self, thread_id: str) -> str | None:
        self._order.pop(thread_id, None)
        self._order[thread_id] = None
        if len(self._order) <= self._max:
            return None
        evicted, _ = self._order.popitem(last=False)
        return evicted


_thread_lru = ThreadLRU(get_settings().max_threads)


def _register(graph: Any, thread_id: str) -> None:
    evicted = _thread_lru.touch(thread_id)
    if evicted is None:
        return
    checkpointer = getattr(graph, "checkpointer", None)
    delete_thread = getattr(checkpointer, "delete_thread", None)
    if delete_thread is None:
        return
    try:
        delete_thread(evicted)
    except Exception:  # noqa: BLE001 - eviction never breaks a turn
        pass


def _trim_history(graph: Any, thread_id: str, window: int) -> None:
    """Trim persisted messages to the last *window* ones.

    Runs at the streaming layer (not inside the subgraph) because
    ``RemoveMessage`` needs a checkpointer to take effect and the agent
    subgraph intentionally has none (ADR-0005).
    """
    window = max(4, window)
    config = {"configurable": {"thread_id": thread_id}}
    try:
        snapshot = graph.get_state(config)
    except Exception:  # noqa: BLE001
        return
    msgs = snapshot.values.get("messages", [])
    if len(msgs) <= window:
        return
    stale = msgs[:-window]
    ids = [m.id for m in stale if m.id]
    if ids:
        try:
            graph.update_state(config, {"messages": [RemoveMessage(id=i) for i in ids]})
        except Exception:  # noqa: BLE001 - trimming is best-effort
            pass


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def _input(message: str) -> dict:
    return {"messages": [HumanMessage(message)]}


def _config(thread_id: str) -> dict:
    return {"configurable": {"thread_id": thread_id}}


def stream_turn(graph: Any, message: str, thread_id: str) -> Iterator[dict[str, Any]]:
    """Translate LangGraph events into wire events (sync)."""
    _register(graph, thread_id)
    _trim_history(graph, thread_id, get_settings().history_window)
    gate = _TokenGate()
    try:
        for event in graph.stream(
            _input(message),
            _config(thread_id),
            stream_mode=["messages", "updates"],
            subgraphs=True,
        ):
            yield from gate.feed(event)
        yield from gate.finish()
    except Exception as exc:  # noqa: BLE001
        yield {"error": str(exc)}


async def astream_turn(graph: Any, message: str, thread_id: str) -> AsyncIterator[dict[str, Any]]:
    """Translate LangGraph events into wire events (async, supports cancellation)."""
    _register(graph, thread_id)
    _trim_history(graph, thread_id, get_settings().history_window)
    gate = _TokenGate()
    stream = graph.astream(
        _input(message),
        _config(thread_id),
        stream_mode=["messages", "updates"],
        subgraphs=True,
    )
    try:
        async for event in stream:
            for wire in gate.feed(event):
                yield wire
        for wire in gate.finish():
            yield wire
    except Exception as exc:  # noqa: BLE001
        yield {"error": str(exc)}
    finally:
        aclose = getattr(stream, "aclose", None)
        if aclose is not None:
            await aclose()