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

Write a concise, factual introduction in Spanish and English that presents
Adrián first as a software engineer and summarizes broad experience areas. Keep
it personal and approachable; do not open with a list of offer-specific
technologies. Do not claim that all requirements are met or recommend a hiring decision.
Write exactly three suggested questions in each language: one about why the
documented experience relates to the role, one about relevant professional
experience, and one about relevant capabilities or projects. Do not suggest a
question focused on weaknesses, gaps, or missing skills. Do not include raw offer
text or identifying company details in those questions. Return structured data
only."""


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
    questions = draft.questions_es + draft.questions_en
    for question in questions:
        if NEGATIVE_STARTER_RE.search(question.label) or NEGATIVE_STARTER_RE.search(
            question.question
        ):
            raise ValueError(
                "Suggested questions must invite evidence about role-relevant "
                "experience, not focus on weaknesses or gaps"
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
    return {
        "id": profile_id,
        "company_name": company_name,
        "target_role": target_role,
        "themes": [item.label for item in draft.requirements],
        "requirements": requirements,
        "evidence": evidence,
        "positioning": {
            "es": draft.positioning_es,
            "en": draft.positioning_en,
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
