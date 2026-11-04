from typing import Annotated, Literal, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_openrouter import ChatOpenRouter
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import START, END, StateGraph
from langgraph.graph.message import RemoveMessage, add_messages
from langgraph.graph.state import CompiledStateGraph

from . import guardrails
from .config import Settings
from .prompts import build_prompt, source_of_truth

MAX_OUTPUT_RETRIES = 1


class State(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    profile_context: str
    input_verdict: Literal["ok", "loaded", "abuse", "injection"]
    neutral_question: str | None
    output_ok: bool
    guardrail_note: str | None
    retries: int


def route_input(state: State) -> Literal["chatbot", "deflect"]:
    return (
        "deflect"
        if state.get("input_verdict") in ("abuse", "injection")
        else "chatbot"
    )


def route_output(state: State) -> Literal["chatbot", "fallback", "__end__"]:
    if state.get("output_ok", True):
        return END
    if int(state.get("retries", 0)) <= MAX_OUTPUT_RETRIES:
        return "chatbot"
    return "fallback"


def build_graph(settings: Settings) -> CompiledStateGraph:
    timeout_ms = int(settings.llm_timeout_s * 1000)
    llm = ChatOpenRouter(
        model=settings.model,
        api_key=settings.api_key or "offline-placeholder",
        temperature=settings.temperature,
        max_tokens=2048,
        timeout=timeout_ms,
    )
    guardrail_llm = ChatOpenRouter(
        model=settings.guardrail_model,
        api_key=settings.api_key or "offline-placeholder",
        temperature=0.0,
        timeout=timeout_ms,
    )
    chain = build_prompt() | llm
    source = source_of_truth()

    def input_guardrail(state: State) -> State:
        last = state["messages"][-1]
        verdict, neutral = (
            guardrails.classify_input(guardrail_llm, guardrails.message_text(last))
            if isinstance(last, HumanMessage)
            else ("ok", None)
        )
        return {
            "input_verdict": verdict,
            "neutral_question": neutral,
            "output_ok": True,
            "guardrail_note": None,
            "retries": 0,
        }

    def chatbot(state: State) -> State:
        messages = list(state["messages"])
        rewrite = None
        if (
            state.get("input_verdict") == "loaded"
            and state.get("neutral_question")
            and isinstance(messages[-1], HumanMessage)
        ):
            last_human = messages.pop()
            rewrite = HumanMessage(
                content=state["neutral_question"], id=last_human.id
            )
            messages.append(rewrite)
        note = state.get("guardrail_note")
        if note and messages:
            human = messages.pop()
            messages.append(SystemMessage(content=note))
            messages.append(human)
        reply = chain.invoke(
            {
                "messages": messages,
                "profile_context": state.get("profile_context", ""),
            }
        )
        if rewrite is not None:
            return {"messages": [rewrite, reply]}
        return {"messages": [reply]}

    def output_guardrail(state: State) -> State:
        messages = state["messages"]
        last = messages[-1]
        if not isinstance(last, AIMessage):
            return {"output_ok": True, "retries": state.get("retries", 0)}
        question = next(
            (guardrails.message_text(m) for m in reversed(messages) if isinstance(m, HumanMessage)),
            "",
        )
        if state.get("input_verdict") == "loaded" and state.get("neutral_question"):
            question = state["neutral_question"]
        ok, reason = guardrails.check_output(
            guardrail_llm, question, guardrails.message_text(last), source
        )
        if ok:
            return {"output_ok": True, "retries": state.get("retries", 0)}
        return {
            "messages": [RemoveMessage(id=last.id)],
            "output_ok": False,
            "guardrail_note": guardrails.RETRY_NOTE.format(
                reason=reason or "it did not meet the quality policy."
            ),
            "retries": state.get("retries", 0) + 1,
        }

    def deflect(state: State) -> State:
        content = (
            guardrails.INJECTION_MESSAGE
            if state.get("input_verdict") == "injection"
            else guardrails.DEFLECT_MESSAGE
        )
        return {"messages": [AIMessage(content=content)]}

    def fallback(state: State) -> State:
        question = next(
            (
                guardrails.message_text(message)
                for message in reversed(state["messages"])
                if isinstance(message, HumanMessage)
            ),
            "",
        )
        return {
            "messages": [AIMessage(content=guardrails.fallback_message(question))]
        }

    builder = StateGraph(State)
    builder.add_node("input_guardrail", input_guardrail)
    builder.add_node("chatbot", chatbot)
    builder.add_node("output_guardrail", output_guardrail)
    builder.add_node("deflect", deflect)
    builder.add_node("fallback", fallback)

    builder.add_edge(START, "input_guardrail")
    builder.add_conditional_edges("input_guardrail", route_input)
    builder.add_edge("chatbot", "output_guardrail")
    builder.add_conditional_edges("output_guardrail", route_output)
    builder.add_edge("deflect", END)
    builder.add_edge("fallback", END)
    agent = builder.compile()

    # The whole turn is a reusable subgraph; the parent graph is a thin wrapper
    # that owns the checkpointer. server.py must stream with subgraphs=True so
    # the inner chatbot/deflect/fallback nodes (and the output_guardrail retry
    # signal) keep surfacing — see tests/test_stream_contract.py.
    parent = StateGraph(State)
    parent.add_node("agent", agent)
    parent.add_edge(START, "agent")
    parent.add_edge("agent", END)
    return parent.compile(checkpointer=MemorySaver())
