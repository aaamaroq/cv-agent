"""Curated public recruiter profiles and their server-side answer focus."""

from dataclasses import dataclass


@dataclass(frozen=True)
class RecruiterProfile:
    profile_id: str
    company_name: str | None
    target_role: str | None
    focus_areas: tuple[str, ...]
    prompt_context: str
    welcome: dict[str, str]
    questions: dict[str, tuple[dict[str, str], ...]]

    def public_payload(self) -> dict:
        return {
            "id": self.profile_id,
            "company_name": self.company_name,
            "target_role": self.target_role,
            "focus_areas": list(self.focus_areas),
            "welcome": self.welcome,
            "questions": {
                language: list(questions)
                for language, questions in self.questions.items()
            },
        }


GENERAL_PROFILE = RecruiterProfile(
    profile_id="general",
    company_name=None,
    target_role=None,
    focus_areas=(),
    prompt_context="",
    welcome={},
    questions={},
)

ACME_PROFILE = RecruiterProfile(
    profile_id="acme",
    company_name="Acme (demo)",
    target_role="AI Engineer",
    focus_areas=("enterprise LLM workflows", "MCP servers", "data processing with Spark"),
    prompt_context=(
        "This is a demonstration profile for the fictional company Acme and an "
        "AI Engineer role. Use its focus areas only to prioritize relevant facts "
        "that the CV or project notes directly support: enterprise LLM workflows, "
        "MCP servers, and data processing with Spark. This context is not evidence "
        "about Adrián or Acme. Do not infer Acme's actual hiring requirements, "
        "claim that Adrián matches them, or add experience beyond the sources."
    ),
    welcome={
        "es": (
            "Hola, equipo de Acme (perfil demo). Esta versión pone el foco en la "
            "experiencia documentada de Adrián con flujos de trabajo con LLMs, "
            "servidores MCP y procesamiento de datos. Las respuestas se basan "
            "en su CV y en las notas del proyecto."
        ),
        "en": (
            "Hi, Acme team (demo profile). This version focuses on Adrián's "
            "documented experience with LLM workflows, MCP servers, and data "
            "processing. Answers are grounded in his CV and project notes."
        ),
    },
    questions={
        "es": (
            {
                "label": "MCP y LLMs",
                "question": (
                    "¿Qué experiencia profesional documenta el CV de Adrián con "
                    "MCP y flujos de trabajo con LLMs?"
                ),
            },
            {
                "label": "Datos y Spark",
                "question": "¿Qué experiencia tiene Adrián con Spark y procesamiento de datos?",
            },
            {
                "label": "Chatbot de portfolio",
                "question": (
                    "¿Cómo funciona el chatbot de portfolio y qué partes están "
                    "implementadas actualmente?"
                ),
            },
        ),
        "en": (
            {
                "label": "MCP & LLMs",
                "question": (
                    "What professional experience does Adrián's CV document "
                    "with MCP and LLM workflows?"
                ),
            },
            {
                "label": "Data & Spark",
                "question": "What experience does Adrián have with Spark and data processing?",
            },
            {
                "label": "Portfolio chatbot",
                "question": (
                    "How does the portfolio chatbot work, and which parts are "
                    "implemented today?"
                ),
            },
        ),
    },
)

PROFILES = {
    GENERAL_PROFILE.profile_id: GENERAL_PROFILE,
    ACME_PROFILE.profile_id: ACME_PROFILE,
}


def get_profile(profile_id: str) -> RecruiterProfile:
    """Return a curated profile, or raise ``KeyError`` for an unknown slug."""
    return PROFILES[profile_id]
