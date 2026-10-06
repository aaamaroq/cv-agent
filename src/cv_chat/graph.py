from typing import Annotated, TypedDict

from langchain_ollama import ChatOllama
from langchain_core.messages import BaseMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.graph.state import CompiledStateGraph

from .config import Settings
from .prompts import build_prompt


class State(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


def build_graph(settings: Settings) -> CompiledStateGraph:
    llm = ChatOllama(
        model=settings.model,
        base_url=settings.ollama_host,
        temperature=settings.temperature,
    )
    chain = build_prompt() | llm

    def chatbot(state: State) -> State:
        return {"messages": [chain.invoke({"messages": state["messages"]})]}

    builder = StateGraph(State)
    builder.add_node("chatbot", chatbot)
    builder.add_edge(START, "chatbot")
    return builder.compile(checkpointer=MemorySaver())
