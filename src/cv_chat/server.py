import json
from typing import Iterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field

from .config import REPO_ROOT, get_settings
from .graph import build_graph

app = FastAPI(title="CV Chat API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

graph = build_graph(get_settings())


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    thread_id: str = Field(min_length=1, max_length=64)


def _chunk_text(chunk: object) -> str:
    content = getattr(chunk, "content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(p.get("text", "") for p in content if isinstance(p, dict))
    return ""


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "model": get_settings().model}


@app.post("/api/chat")
def chat(req: ChatRequest) -> StreamingResponse:
    config = {"configurable": {"thread_id": req.thread_id}}

    def event_stream() -> Iterator[str]:
        try:
            for chunk, metadata in graph.stream(
                {"messages": [HumanMessage(req.message)]},
                config,
                stream_mode="messages",
            ):
                if metadata.get("langgraph_node") != "chatbot":
                    continue
                text = _chunk_text(chunk)
                if text:
                    yield _sse({"token": text})
            yield _sse({"done": True})
        except Exception as exc:  # noqa: BLE001 - surface any backend error to the UI
            yield _sse({"error": str(exc)})

    return StreamingResponse(event_stream(), media_type="text/event-stream")


_dist = REPO_ROOT / "web" / "dist"
if _dist.is_dir():
    from fastapi.staticfiles import StaticFiles

    app.mount("/", StaticFiles(directory=_dist, html=True), name="web")
