#!/usr/bin/env python
"""Generate a reviewed recruiter profile from an offer, CV and project notes.

The offer and sources are sent to the configured OpenRouter model for this
one-time step. The generated profile stores sanitized role criteria and exact
candidate evidence excerpts, but never the raw offer or offer quotations.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Literal

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openrouter import ChatOpenRouter
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cv_chat.config import get_settings  # noqa: E402
from cv_chat.guardrails import is_spanish_text  # noqa: E402
from cv_chat.prompts import load_cv, load_project_notes  # noqa: E402
from cv_chat.profiles import PROFILES_DIR  # noqa: E402

PROFILE_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
MAX_OFFER_CHARS = 40_000
NEGATIVE_STARTER_RE = re.compile(
    r"\b(?:weakness(?:es)?|gaps?|missing|lack(?:ing)?|shortfall(?:s)?|"
    r"downside(?:s)?|drawback(?:s)?|debilidad(?:es)?|carencia(?:s)?|"
    r"falta(?:n)?|punto débil|puntos débiles|brecha(?:s)?)\b",
    re.IGNORECASE,
)
PROFESSIONAL_FIT_RE = re.compile(
    r"\b(?:backend|distributed(?: systems)?|data pipelines|data engineering|"
    r"software engineer|cloud deployment|platform engineering|systems engineering|"
    r"API|microservices|data processing|ingenier[oa] de software|"
    r"sistemas distribuidos|pipelines? de datos|ingenier[ií]a de datos|"
    r"despliegue cloud|ingenier[ií]a de plataformas|microservicios|"
    r"procesamiento de datos)\b",
    re.IGNORECASE,
)
AI_READINESS_RE = re.compile(
    r"\b(?:AI|GenAI|LLM|language model|LangGraph|RAG|guardrails|evaluation|"
    r"retrieval|agentic|prompt design|model|IA|inteligencia artificial|"
    r"modelos? de lenguaje|evaluaci[oó]n|recuperaci[oó]n)\b",
    re.IGNORECASE,
)
PROJECT_LEAD_RE = re.compile(
    r"^\s*(?:mcp|langgraph|chatbot|personal project|project|prototype)\b",
    re.IGNORECASE,
)
GENERIC_QUESTION_RE = re.compile(
    r"\b(?:what technologies|qué tecnologías|what projects|qué proyectos|"
    r"in general|en general|generally|overall|general overview|resumen general)\b",
    re.IGNORECASE,
)

EvidenceSource = Literal[
    "cv_summary",
    "cv_professional",
    "cv_projects",
    "cv_skills",
    "cv_development",
    "project_notes",
]
EvidenceType = Literal[
    "professional experience",
    "personal project",
    "listed skill",
    "training",
]
EvidenceRelation = Literal["direct", "related", "listed_only", "training_only"]


class RoleRequirement(BaseModel):
    id: str = Field(description="Short stable id, e.g. professional-llm-work")
    label: str = Field(description="Short display label for this role criterion")
    description: str = Field(
        description="Sanitized paraphrase of one important offer requirement"
    )
    priority: Literal["required", "preferred"]
    offer_quote: str = Field(
        description="Exact short supporting quote copied from the offer"
    )


class CandidateEvidence(BaseModel):
    requirement_id: str = Field(description="An id from the generated role criteria")
    source: EvidenceSource
    evidence_type: EvidenceType
    relation: EvidenceRelation = Field(
        description=(
            "direct for demonstrated evidence, related for transferable evidence, "
            "listed_only for skills-list mentions, training_only for coursework"
        )
    )
    quote: str = Field(
        description="Exact supporting quote copied from the selected candidate source"
    )


class SuggestedQuestion(BaseModel):
    label: str = Field(description="Short visible question label")
    question: str = Field(description="A concise recruiter question in the requested language")


class ProfileDraft(BaseModel):
    requirements: list[RoleRequirement] = Field(min_length=1, max_length=8)
    evidence: list[CandidateEvidence] = Field(min_length=1, max_length=16)
    positioning_es: str = Field(
        description="One concise, factual introduction to Adrián as a software engineer in Spanish"
    )
    positioning_en: str = Field(
        description="One concise, factual introduction to Adrián as a software engineer in English"
    )
    questions_es: list[SuggestedQuestion] = Field(min_length=3, max_length=3)
    questions_en: list[SuggestedQuestion] = Field(min_length=3, max_length=3)


GENERATOR_SYSTEM_PROMPT = """Create a recruiter-profile draft from a job offer, a CV, and project notes.

Extract 3–8 important role criteria as concise sanitized paraphrases. Keep an
exact short `offer_quote` only for validation; it will not be stored in the
profile. Do not copy company names, customer brands, funding, locations, or
other identifying offer details into descriptions, labels, questions, or
positioning.

Map candidate evidence only when a verbatim quote in the supplied sources is
relevant to a criterion. Cite the exact source and quote. Keep professional
experience, personal projects, listed skills, and training distinct. Use
`direct` only when the quote demonstrates the criterion itself; use `related`
for transferable evidence; use `listed_only` for skills-list mentions and
`training_only` for courses. Do not treat a skill or course as work experience.
It is valid for a criterion to have no mapped evidence. Never invent a quote,
customer usage, production deployment, outcome, metric, or level of ownership.
Calibrate prominence to the breadth and depth of documented evidence. Do not
make one project dominate positioning solely because its terminology matches
the offer; balance it with broader experience and other relevant projects. Do
not imply sustained specialization or production delivery unless the sources
establish it.

Write a concise, factual introduction in Spanish and English that presents
Adrián first as a software engineer with strong documented experience in
backend/data engineering, distributed systems and production-oriented software
work. Then connect that foundation to AI/LLM readiness and the role's
requirements. Keep it personal and approachable; do not open with MCP,
LangGraph, a chatbot, or a personal-project pitch as the main story. The
introduction must read as a value proposition for the target company: explain
who Adrián is, what relevant experience he brings, and what he can contribute
to the team or business, while staying grounded in the source evidence. The
profile should feel like a recruiter-facing applicant pitch, not a neutral
project summary. Frame the message around “why is Adrián prepared for this
role?” and “what can he contribute to this company or team?”, not just “what
is he working on?” When describing fit, lead with the strongest professional
backend/data evidence and treat the GenAI work as supporting evidence, not the
whole story. Do not claim that all requirements are met or recommend a hiring
decision. If the profile is being shared with a recruiter, explicitly invite
them to review the tailored portfolio or offer-specific profile link for
additional context. Keep professional experience and personal portfolio work
clearly distinct. Do not invent customer deployments, domain integrations,
industrial environments, or company-specific claims that the sources do not
document.
Write exactly three suggested questions in each language that directly answer
recruiter fit questions such as: why Adrián is prepared for this role, what
experience connects to the offer, and what value he can bring to the team. They
must sound like HR/recruiter questions about fit, relevance, and contribution,
not generic questions about technologies, career history, or project lists. Do
not suggest a question focused on weaknesses, gaps, or missing skills. Do not
include raw offer text or identifying company details in those questions. Return
structured data only."""


def _normalise(text: str) -> str:
    return " ".join(text.casefold().split())


def _section(text: str, heading: str) -> str:
    start = text.find(heading)
    if start < 0:
        return ""
    start += len(heading)
    end = text.find("\n## ", start)
    return text[start:] if end < 0 else text[start:end]


def candidate_sources(cv: str, project_notes: str) -> dict[str, str]:
    return {
        "cv_summary": _section(cv, "## Summary"),
        "cv_professional": _section(cv, "## Professional Experience"),
        "cv_projects": _section(cv, "## AI Projects"),
        "cv_skills": _section(cv, "## Technical Skills"),
        "cv_development": _section(cv, "## Professional Development"),
        "project_notes": project_notes,
    }


def validate_draft(
    draft: ProfileDraft, offer: str, cv: str, project_notes: str = ""
) -> None:
    """Ensure offer criteria and candidate evidence quotes exist in their sources."""
    if not 1 <= len(draft.requirements) <= 8:
        raise ValueError("The generated profile must contain between 1 and 8 requirements")
    if len(draft.questions_es) != 3 or len(draft.questions_en) != 3:
        raise ValueError("The generated profile must contain exactly 3 questions per language")
    if not 1 <= len(draft.evidence) <= 16:
        raise ValueError("The generated profile must contain between 1 and 16 evidence items")
    for language, questions in (
        ("Spanish", draft.questions_es),
        ("English", draft.questions_en),
    ):
        for question in questions:
            if is_spanish_text(question.question) != (language == "Spanish"):
                raise ValueError(f"Suggested questions must be written in {language}")
            if NEGATIVE_STARTER_RE.search(question.label) or NEGATIVE_STARTER_RE.search(
                question.question
            ):
                raise ValueError(
                    "Suggested questions must invite evidence about role-relevant "
                    "experience, not focus on weaknesses or gaps"
                )
            question_text = f"{question.label} {question.question}"
            if GENERIC_QUESTION_RE.search(question_text):
                raise ValueError(
                    "Suggested questions must answer recruiter fit and offer relevance, "
                    "not generic background prompts"
                )

    for field_name, text in {
        "positioning_es": draft.positioning_es,
        "positioning_en": draft.positioning_en,
    }.items():
        if PROJECT_LEAD_RE.match(text):
            raise ValueError(
                "Positioning must lead with documented backend or data experience and "
                "then connect it to AI/LLM work, not with MCP or a personal-project lead"
            )
        if not PROFESSIONAL_FIT_RE.search(text):
            raise ValueError(
                f"{field_name} must lead with documented backend or data experience "
                "before connecting it to AI/LLM work"
            )
        if not AI_READINESS_RE.search(text):
            raise ValueError(
                f"{field_name} must connect the candidate's professional experience to AI/LLM readiness"
            )

    offer_text = _normalise(offer)
    sources = {key: _normalise(value) for key, value in candidate_sources(cv, project_notes).items()}
    requirements: dict[str, RoleRequirement] = {}
    for requirement in draft.requirements:
        if not PROFILE_ID_RE.fullmatch(requirement.id):
            raise ValueError(f"Invalid requirement id: {requirement.id!r}")
        if requirement.id in requirements:
            raise ValueError(f"Duplicate requirement id: {requirement.id!r}")
        quote = _normalise(requirement.offer_quote)
        if not quote or quote not in offer_text:
            raise ValueError(
                f"Requirement {requirement.id!r} has no exact supporting quote in the offer"
            )
        requirements[requirement.id] = requirement

    seen_evidence: set[tuple[str, str, str]] = set()
    expected_types = {
        "cv_summary": {"professional experience"},
        "cv_professional": {"professional experience"},
        "cv_projects": {"personal project"},
        "cv_skills": {"listed skill"},
        "cv_development": {"training"},
        "project_notes": {"personal project"},
    }
    expected_relations = {
        "cv_skills": {"listed_only"},
        "cv_development": {"training_only"},
    }
    for item in draft.evidence:
        if item.requirement_id not in requirements:
            raise ValueError(
                f"Evidence references unknown requirement {item.requirement_id!r}"
            )
        if item.evidence_type not in expected_types[item.source]:
            raise ValueError(
                f"Evidence type {item.evidence_type!r} does not match source {item.source!r}"
            )
        if item.source in expected_relations and item.relation not in expected_relations[item.source]:
            raise ValueError(
                f"Evidence from {item.source!r} must use relation "
                f"{next(iter(expected_relations[item.source]))!r}"
            )
        if item.source not in expected_relations and item.relation in {
            "listed_only",
            "training_only",
        }:
            raise ValueError(
                f"Evidence from {item.source!r} cannot use relation {item.relation!r}"
            )
        quote = _normalise(item.quote)
        if not quote or quote not in sources[item.source]:
            raise ValueError(
                f"Evidence for {item.requirement_id!r} has no exact quote in {item.source}"
            )
        key = (item.requirement_id, item.source, quote)
        if key in seen_evidence:
            raise ValueError(f"Duplicate evidence quote for {item.requirement_id!r}")
        seen_evidence.add(key)


def build_profile_document(
    profile_id: str,
    company_name: str,
    target_role: str,
    draft: ProfileDraft,
) -> dict:
    """Build a profile without retaining the raw offer or its supporting quotes."""
    requirements = [
        {
            "id": item.id,
            "label": item.label,
            "description": item.description,
            "priority": item.priority,
        }
        for item in draft.requirements
    ]
    evidence = [item.model_dump() for item in draft.evidence]
    portfolio_url = f"https://webcv-agent.vercel.app/p/{profile_id}"
    return {
        "id": profile_id,
        "company_name": company_name,
        "target_role": target_role,
        "themes": [item.label for item in draft.requirements],
        "requirements": requirements,
        "evidence": evidence,
        "positioning": {
            "es": (
                f"{draft.positioning_es}\n\nRevisa el perfil personalizado para "
                f"esta oferta: [portfolio de Adrián]({portfolio_url})."
            ),
            "en": (
                f"{draft.positioning_en}\n\nReview the tailored profile for this "
                f"role: [Adrián's portfolio]({portfolio_url})."
            ),
        },
        "welcome": {
            "es": (
                f"¡Hola, equipo de {company_name}! He preparado esta página para "
                f"facilitaros la revisión de la experiencia de Adrián para {target_role}."
            ),
            "en": (
                f"Hi, {company_name} team! I put this page together to make it easier "
                f"to review Adrián's experience for {target_role}."
            ),
        },
        "questions": {
            "es": [question.model_dump() for question in draft.questions_es],
            "en": [question.model_dump() for question in draft.questions_en],
        },
    }


def generate_draft(offer: str, cv: str, project_notes: str) -> ProfileDraft:
    settings = get_settings()
    if not settings.api_key:
        raise RuntimeError("Set OPENROUTER_API_KEY to generate a profile")

    llm = ChatOpenRouter(
        model=settings.model,
        api_key=settings.api_key,
        temperature=0.0,
        timeout=int(settings.llm_timeout_s * 1000),
    )
    sources = candidate_sources(cv, project_notes)
    if not any(sources.values()):
        raise ValueError("CV or project notes must contain evidence")

    draft = llm.with_structured_output(ProfileDraft).invoke(
        [
            SystemMessage(content=GENERATOR_SYSTEM_PROMPT),
            HumanMessage(
                content=(
                    "CANDIDATE SOURCES (keep their evidence types distinct):\n"
                    + "\n\n".join(
                        f"[{source}]\n{text}"
                        for source, text in sources.items()
                        if text.strip()
                    )
                    + f"\n\nJOB OFFER:\n{offer}"
                )
            ),
        ]
    )
    validate_draft(draft, offer, cv, project_notes)
    return draft


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--id", required=True, help="Public URL slug, e.g. acme-ai-engineer")
    parser.add_argument("--company", required=True, help="Public company label")
    parser.add_argument("--role", required=True, help="Public role title")
    parser.add_argument(
        "--offer", required=True, help="Local UTF-8 offer text file, or '-' to read stdin"
    )
    parser.add_argument("--force", action="store_true", help="Replace an existing profile JSON")
    args = parser.parse_args()

    if not PROFILE_ID_RE.fullmatch(args.id) or args.id == "general":
        parser.error("--id must be a lowercase URL slug and cannot be 'general'")
    if args.offer == "-":
        offer = sys.stdin.read().strip()
    else:
        offer_path = Path(args.offer)
        if not offer_path.is_file():
            parser.error(f"Offer file not found: {offer_path}")
        offer = offer_path.read_text(encoding="utf-8").strip()
    if not offer or len(offer) > MAX_OFFER_CHARS:
        parser.error(f"Offer must contain 1–{MAX_OFFER_CHARS} characters")

    output = PROFILES_DIR / f"{args.id}.json"
    if output.exists() and not args.force:
        parser.error(f"{output} already exists; pass --force to replace it")

    try:
        draft = generate_draft(offer, load_cv(), load_project_notes())
    except (RuntimeError, ValueError) as exc:
        parser.error(str(exc))

    document = build_profile_document(args.id, args.company, args.role, draft)
    PROFILES_DIR.mkdir(exist_ok=True)
    temporary = output.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    temporary.replace(output)
    print(f"Wrote {output.relative_to(ROOT)}; review the fit map before sharing the profile.")


if __name__ == "__main__":
    main()
