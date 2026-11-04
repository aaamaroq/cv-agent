import json
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field

from .config import CV_PATH, PROJECT_NOTES_PATH, REPO_ROOT, get_settings
from .graph import build_graph
from .observability import (
    ChatRequestTracingMiddleware,
    configure_observability,
    shutdown_observability,
)
from .profiles import get_profile
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
    profile_id: str = Field(
        default="general", min_length=1, max_length=40, pattern=r"^[a-z0-9-]+$"
    )


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


@app.get("/api/profiles/{profile_id}")
def recruiter_profile(profile_id: str) -> dict:
    try:
        return get_profile(profile_id).public_payload()
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Portfolio profile not found") from exc


@app.post("/api/chat")
async def chat(req: ChatRequest, request: Request) -> StreamingResponse:
    try:
        profile = get_profile(req.profile_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Portfolio profile not found") from exc

    # A thread can never carry context across different recruiter profiles.
    thread_id = f"{profile.profile_id}:{req.thread_id}"

    async def event_stream() -> AsyncIterator[str]:
        events = astream_turn(
            graph, req.message, thread_id, profile.prompt_context
        )
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

    @app.get("/p/{profile_id}", include_in_schema=False)
    def recruiter_profile_page(profile_id: str):
        return FileResponse(_dist / "index.html")

    app.mount("/", StaticFiles(directory=_dist, html=True), name="web")
