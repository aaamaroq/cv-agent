import os
from dataclasses import dataclass, field
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
    api_key: str = field(repr=False)
    temperature: float
    max_threads: int
    history_window: int
    llm_timeout_s: float
    langfuse_enabled: bool = True
    langfuse_public_key: str = ""
    langfuse_secret_key: str = field(default="", repr=False)
    langfuse_base_url: str = ""

    def __post_init__(self) -> None:
        if self.max_threads < 1:
            raise ValueError("CV_MAX_THREADS must be at least 1")
        if self.history_window < 4:
            raise ValueError("CV_HISTORY_WINDOW must be at least 4")
        if not isfinite(self.llm_timeout_s) or self.llm_timeout_s < 0.001:
            raise ValueError("CV_LLM_TIMEOUT_S must be finite and at least 0.001 seconds")

    @property
    def langfuse_configured(self) -> bool:
        return self.langfuse_enabled and all(
            (
                self.langfuse_public_key,
                self.langfuse_secret_key,
                self.langfuse_base_url,
            )
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(
        model=os.getenv("CV_MODEL", "mistralai/mistral-nemo"),
        guardrail_model=os.getenv("CV_GUARDRAIL_MODEL", "mistralai/mistral-nemo"),
        api_key=os.getenv("OPENROUTER_API_KEY", ""),
        temperature=float(os.getenv("CV_TEMPERATURE", "0.3")),
        max_threads=int(os.getenv("CV_MAX_THREADS", "32")),
        history_window=int(os.getenv("CV_HISTORY_WINDOW", "24")),
        llm_timeout_s=float(os.getenv("CV_LLM_TIMEOUT_S", "60")),
        langfuse_enabled=os.getenv("CV_LANGFUSE_ENABLED", "true").lower()
        in {"1", "true", "yes", "on"},
        langfuse_public_key=os.getenv("LANGFUSE_PUBLIC_KEY", ""),
        langfuse_secret_key=os.getenv("LANGFUSE_SECRET_KEY", ""),
        langfuse_base_url=os.getenv("LANGFUSE_BASE_URL", ""),
    )
