import os
from dataclasses import dataclass
from functools import lru_cache
from math import isfinite
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CV_PATH = REPO_ROOT / "cv.md"
PROJECT_NOTES_PATH = REPO_ROOT / "docs" / "PROJECT.md"


@dataclass(frozen=True)
class Settings:
    model: str
    guardrail_model: str
    api_key: str
    temperature: float
    max_threads: int
    history_window: int
    llm_timeout_s: float

    def __post_init__(self) -> None:
        if self.max_threads < 1:
            raise ValueError("CV_MAX_THREADS must be at least 1")
        if self.history_window < 4:
            raise ValueError("CV_HISTORY_WINDOW must be at least 4")
        if not isfinite(self.llm_timeout_s) or self.llm_timeout_s < 0.001:
            raise ValueError("CV_LLM_TIMEOUT_S must be finite and at least 0.001 seconds")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(
        model=os.getenv("CV_MODEL", "google/gemma-4-31b-it:free"),
        guardrail_model=os.getenv("CV_GUARDRAIL_MODEL", "deepseek/deepseek-chat:free"),
        api_key=os.getenv("OPENROUTER_API_KEY", ""),
        temperature=float(os.getenv("CV_TEMPERATURE", "0.3")),
        max_threads=int(os.getenv("CV_MAX_THREADS", "32")),
        history_window=int(os.getenv("CV_HISTORY_WINDOW", "24")),
        llm_timeout_s=float(os.getenv("CV_LLM_TIMEOUT_S", "60")),
    )
