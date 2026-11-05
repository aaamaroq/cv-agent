"""Translate graph events into client SSE payloads.

Public interface:
  stream_turn(graph, message, thread_id, profile_context, history)  -> Iterator[dict]
  astream_turn(graph, message, thread_id, profile_context, history) -> AsyncIterator[dict]

Both paths adapt LangGraph events into the same wire events and share the
token-gating policy: chatbot tokens are buffered until the output guardrail
accepts them, rejected drafts are discarded, and canned deflect/fallback text
streams immediately. The browser supplies bounded, completed conversation turns
so requests remain independent of the serving instance.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, AsyncIterator, Iterator, Sequence

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from .config import get_settings
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
# Public interface
# ---------------------------------------------------------------------------

def _history_message(message: Any) -> BaseMessage:
    role = message.role if hasattr(message, "role") else message["role"]
    content = message.content if hasattr(message, "content") else message["content"]
    return HumanMessage(content) if role == "user" else AIMessage(content)


def _input(
    message: str,
    profile_context: str = "",
    history: Sequence[Any] = (),
) -> dict:
    bounded_history = list(history)[-(get_settings().history_window - 1) :]
    if bounded_history:
        first_role = (
            bounded_history[0].role
            if hasattr(bounded_history[0], "role")
            else bounded_history[0]["role"]
        )
        if first_role != "user":
            bounded_history = bounded_history[1:]
    if len(bounded_history) % 2:
        bounded_history = bounded_history[:-1]
    messages = [_history_message(item) for item in bounded_history]
    messages.append(HumanMessage(message))
    return {"messages": messages, "profile_context": profile_context}


def _config(thread_id: str) -> dict:
    config = {"configurable": {"thread_id": thread_id}}
    callback = langfuse_callback_handler()
    if callback is not None:
        profile_id, separator, _ = thread_id.partition(":")
        if not separator:
            profile_id = "general"
        config.update(
            {
                "run_name": "cv-chat-turn",
                "metadata": {
                    "langfuse_session_id": thread_id,
                    "langfuse_trace_name": "CV chat turn",
                    "profile_id": profile_id,
                    "langfuse_tags": [
                        "cv-chat",
                        "langgraph",
                        f"profile:{profile_id}",
                    ],
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
    history: Sequence[Any] = (),
) -> Iterator[dict[str, Any]]:
    """Translate LangGraph events into wire events (sync)."""
    gate = _TokenGate()
    try:
        for event in graph.stream(
            _input(message, profile_context, history),
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
    history: Sequence[Any] = (),
) -> AsyncIterator[dict[str, Any]]:
    """Translate LangGraph events into wire events (async, supports cancellation)."""
    gate = _TokenGate()
    stream = graph.astream(
        _input(message, profile_context, history),
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
