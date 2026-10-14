from typing import Annotated, Literal, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_ollama import ChatOllama
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
    llm = ChatOllama(
        model=settings.model,
        base_url=settings.ollama_host,
        temperature=settings.temperature,
    )
    guardrail_llm = ChatOllama(
        model=settings.guardrail_model,
        base_url=settings.ollama_host,
        temperature=0.0,
        format="json",
        keep_alive=0,
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
        reply = chain.invoke({"messages": messages})
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
        return {"messages": [AIMessage(content=guardrails.FALLBACK_MESSAGE)]}

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
    return builder.compile(checkpointer=MemorySaver())
