"""Translate graph events into client SSE payloads.

Public interface:
  stream_turn(graph, message, thread_id)  -> Iterator[dict]   (sync)
  astream_turn(graph, message, thread_id) -> AsyncIterator[dict] (async)

Both paths adapt LangGraph events into the same wire events and share the
token-gating policy: chatbot tokens are buffered until the output guardrail
accepts them, rejected drafts are discarded, and canned deflect/fallback text
streams immediately. Conversation history and per-thread coordination live in
``conversation_runtime.py``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, AsyncIterator, Iterator

from langchain_core.messages import HumanMessage

from .config import get_settings
from .conversation_runtime import ConversationRuntime
from .observability import langfuse_callback_handler

CHATBOT_NODE = "chatbot"
IMMEDIATE_NODES = frozenset({"deflect", "fallback"})


# ---------------------------------------------------------------------------
# LangGraph event adapter
# ---------------------------------------------------------------------------

def _chunk_text(chunk: object) -> str:
    content = getattr(chunk, "content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(p.get("text", "") for p in content if isinstance(p, dict))
    return ""


@dataclass(frozen=True)
class _TokenChunk:
    node: str | None
    text: str


@dataclass(frozen=True)
class _OutputVerdict:
    accepted: bool


_DecodedEvent = _TokenChunk | _OutputVerdict | None


def _decode_graph_event(event: tuple) -> _DecodedEvent:
    """Translate LangGraph's nested stream tuples into semantic events."""
    _namespace, mode, data = event
    if mode == "updates":
        update = data.get("output_guardrail") if isinstance(data, dict) else None
        if isinstance(update, dict):
            return _OutputVerdict(accepted=update.get("output_ok") is not False)
        return None

    chunk, metadata = data
    text = _chunk_text(chunk)
    if not text:
        return None
    return _TokenChunk(node=metadata.get("langgraph_node"), text=text)


class _TokenGate:
    """Buffers chatbot tokens until the output verdict lands."""

    def __init__(self) -> None:
        self._buffer: list[str] = []

    def feed(self, event: _DecodedEvent) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        if isinstance(event, _OutputVerdict):
            if not event.accepted:
                self._buffer.clear()
                out.append({"restart": True})
            else:
                out.extend({"token": token} for token in self._buffer)
                self._buffer.clear()
            return out
        if not isinstance(event, _TokenChunk):
            return out
        if event.node == CHATBOT_NODE:
            self._buffer.append(event.text)
        elif event.node in IMMEDIATE_NODES:
            out.append({"token": event.text})
        return out

    def finish(self) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        if self._buffer:
            self._buffer.clear()
            out.append({"restart": True})
        out.append({"done": True})
        return out


# ---------------------------------------------------------------------------
# Conversation runtime
# ---------------------------------------------------------------------------

_runtime = ConversationRuntime(get_settings())


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def _input(message: str, profile_context: str = "") -> dict:
    return {"messages": [HumanMessage(message)], "profile_context": profile_context}


def _config(thread_id: str) -> dict:
    config = {"configurable": {"thread_id": thread_id}}
    callback = langfuse_callback_handler()
    if callback is not None:
        config.update(
            {
                "run_name": "cv-chat-turn",
                "metadata": {
                    "langfuse_session_id": thread_id,
                    "langfuse_trace_name": "CV chat turn",
                    "langfuse_tags": ["cv-chat", "langgraph"],
                },
                "callbacks": [callback],
            }
        )
    return config


def stream_turn(
    graph: Any,
    message: str,
    thread_id: str,
    profile_context: str = "",
) -> Iterator[dict[str, Any]]:
    """Translate LangGraph events into wire events (sync)."""
    with _runtime.turn(graph, thread_id):
        gate = _TokenGate()
        try:
            for event in graph.stream(
                _input(message, profile_context),
                _config(thread_id),
                stream_mode=["messages", "updates"],
                subgraphs=True,
            ):
                yield from gate.feed(_decode_graph_event(event))
            yield from gate.finish()
        except Exception as exc:  # noqa: BLE001
            yield {"error": str(exc)}


async def astream_turn(
    graph: Any,
    message: str,
    thread_id: str,
    profile_context: str = "",
) -> AsyncIterator[dict[str, Any]]:
    """Translate LangGraph events into wire events (async, supports cancellation)."""
    async with _runtime.aturn(graph, thread_id):
        gate = _TokenGate()
        stream = graph.astream(
            _input(message, profile_context),
            _config(thread_id),
            stream_mode=["messages", "updates"],
            subgraphs=True,
        )
        try:
            async for event in stream:
                for wire in gate.feed(_decode_graph_event(event)):
                    yield wire
            for wire in gate.finish():
                yield wire
        except Exception as exc:  # noqa: BLE001
            yield {"error": str(exc)}
        finally:
            aclose = getattr(stream, "aclose", None)
            if aclose is not None:
                await aclose()
