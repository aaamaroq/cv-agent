"""Conversation-history limits and per-thread turn coordination.

The parent graph owns the checkpointer. This module owns when a conversation is
admitted, serialized with turns for the same thread, trimmed, and evicted.
"""

from __future__ import annotations

import asyncio
import threading
from collections import OrderedDict
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Iterator

from langgraph.graph.message import RemoveMessage

from .config import Settings


@dataclass
class _Conversation:
    graph: Any
    thread_id: str
    lock: threading.Lock = field(default_factory=threading.Lock)
    in_flight: int = 0


class ConversationRuntime:
    """Bounded, serialized access to persisted conversation histories.

    Active or queued threads are pinned. If all old threads are in use, the
    limit may be exceeded temporarily; the oldest idle thread is evicted once
    it becomes safe to do so.
    """

    def __init__(self, settings: Settings) -> None:
        self._max_threads = settings.max_threads
        self._history_window = settings.history_window
        self._guard = threading.RLock()
        self._conversations: OrderedDict[tuple[int, str], _Conversation] = OrderedDict()

    @contextmanager
    def turn(self, graph: Any, thread_id: str) -> Iterator[None]:
        """Serialize a synchronous turn and maintain bounded history."""
        conversation = self._reserve(graph, thread_id)
        try:
            conversation.lock.acquire()
        except BaseException:
            self._finish(conversation)
            raise
        try:
            self._trim_history(conversation)
            yield
        finally:
            conversation.lock.release()
            self._finish(conversation)

    @asynccontextmanager
    async def aturn(self, graph: Any, thread_id: str) -> AsyncIterator[None]:
        """Async-compatible turn lock shared with synchronous callers."""
        conversation = self._reserve(graph, thread_id)
        try:
            while not conversation.lock.acquire(blocking=False):
                await asyncio.sleep(0.01)
        except BaseException:
            self._finish(conversation)
            raise

        try:
            self._trim_history(conversation)
            yield
        finally:
            conversation.lock.release()
            self._finish(conversation)

    def _reserve(self, graph: Any, thread_id: str) -> _Conversation:
        key = (id(graph), thread_id)
        with self._guard:
            conversation = self._conversations.pop(key, None)
            if conversation is None:
                conversation = _Conversation(graph=graph, thread_id=thread_id)
            conversation.in_flight += 1
            self._conversations[key] = conversation
            self._prune_locked()
            return conversation

    def _finish(self, conversation: _Conversation) -> None:
        with self._guard:
            conversation.in_flight -= 1
            self._prune_locked()

    def _prune_locked(self) -> None:
        while len(self._conversations) > self._max_threads:
            key, oldest = next(iter(self._conversations.items()))
            if oldest.in_flight:
                # Preserve LRU order: do not evict a newer idle thread while
                # the oldest conversation is still being used.
                return
            self._conversations.pop(key)
            self._delete_checkpoint(oldest)

    @staticmethod
    def _delete_checkpoint(conversation: _Conversation) -> None:
        try:
            checkpointer = getattr(conversation.graph, "checkpointer", None)
            delete_thread = getattr(checkpointer, "delete_thread", None)
            if delete_thread is None:
                return
            delete_thread(conversation.thread_id)
        except Exception:  # noqa: BLE001 - eviction never breaks a turn
            pass

    def _trim_history(self, conversation: _Conversation) -> None:
        graph = conversation.graph
        config = {"configurable": {"thread_id": conversation.thread_id}}
        try:
            snapshot = graph.get_state(config)
        except Exception:  # noqa: BLE001 - trimming is best-effort
            return
        messages = snapshot.values.get("messages", [])
        if len(messages) <= self._history_window:
            return
        stale_ids = [
            message.id
            for message in messages[:-self._history_window]
            if message.id
        ]
        if not stale_ids:
            return
        try:
            graph.update_state(
                config,
                {"messages": [RemoveMessage(id=message_id) for message_id in stale_ids]},
            )
        except Exception:  # noqa: BLE001 - trimming is best-effort
            pass
