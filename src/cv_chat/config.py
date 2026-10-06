import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CV_PATH = REPO_ROOT / "cv.md"


@dataclass(frozen=True)
class Settings:
    model: str
    ollama_host: str
    temperature: float


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(
        model=os.getenv("CV_MODEL", "gemma3:4b"),
        ollama_host=os.getenv("OLLAMA_HOST", "http://localhost:11434"),
        temperature=float(os.getenv("CV_TEMPERATURE", "0.3")),
    )
