import json
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from .config import CV_PATH, PROJECT_NOTES_PATH, REPO_ROOT, get_settings
from .graph import build_graph
from .observability import (
    ChatRequestTracingMiddleware,
    configure_observability,
    shutdown_observability,
)
from .streaming import astream_turn

configure_observability(get_settings())


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    try:
        yield
    finally:
        shutdown_observability()


app = FastAPI(title="CV Chat API", lifespan=lifespan)
app.add_middleware(ChatRequestTracingMiddleware)
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


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


@app.get("/api/health")
def health() -> dict:
    settings = get_settings()
    return {
        "status": "ok",
        "api_key_configured": bool(settings.api_key),
        "cv_present": CV_PATH.is_file(),
        "project_notes_present": PROJECT_NOTES_PATH.is_file(),
        "model": settings.model,
        "guardrail_model": settings.guardrail_model,
    }


@app.post("/api/chat")
async def chat(req: ChatRequest, request: Request) -> StreamingResponse:
    async def event_stream() -> AsyncIterator[str]:
        events = astream_turn(graph, req.message, req.thread_id)
        try:
            async for event in events:
                if await request.is_disconnected():
                    return
                yield _sse(event)
        finally:
            await events.aclose()

    return StreamingResponse(event_stream(), media_type="text/event-stream")


_dist = REPO_ROOT / "web" / "dist"
if _dist.is_dir():
    from fastapi.staticfiles import StaticFiles

    app.mount("/", StaticFiles(directory=_dist, html=True), name="web")
