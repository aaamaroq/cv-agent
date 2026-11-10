"""Load curated recruiter profiles and build server-side answer focus."""

import json
import re
from dataclasses import dataclass
from pathlib import Path

from .config import CV_PROFILES_DIR

PROFILES_DIR = CV_PROFILES_DIR
PROFILE_ID_PATTERN = re.compile(r"^[a-z0-9-]{1,40}$")


@dataclass(frozen=True)
class RecruiterProfile:
    profile_id: str
    company_name: str | None
    target_role: str | None
    themes: tuple[str, ...]
    welcome: dict[str, str]
    questions: dict[str, tuple[dict[str, str], ...]]
    positioning: dict[str, str]
    requirements: tuple[dict[str, str], ...]
    evidence: tuple[dict[str, str], ...]

    def public_payload(self) -> dict:
        """Return page copy only; keep role rubric and evidence map server-side."""
        return {
            "id": self.profile_id,
            "company_name": self.company_name,
            "target_role": self.target_role,
            "focus_areas": list(self.themes),
            "welcome": self.welcome,
            "questions": {
                language: list(questions)
                for language, questions in self.questions.items()
            },
            "positioning": self.positioning,
        }

    @property
    def prompt_context(self) -> str:
        if not self.requirements:
            if not self.themes:
                return ""
            themes = ", ".join(self.themes)
            return (
                "Role focus: "
                f"{themes}. "
                "Use these as relevance cues only; they are not evidence about Adrián or the company. "
                "Do not infer a full match from the themes alone."
            )

        evidence_by_requirement: dict[str, list[str]] = {}
        for item in self.evidence:
            evidence_by_requirement.setdefault(item["requirement_id"], []).append(
                f"{item['evidence_type']} ({item['relation']}; {item['source']}): {item['quote']}"
            )

        direct_evidence: list[str] = []
        related_evidence: list[str] = []
        unknowns: list[str] = []
        for requirement in self.requirements:
            requirement_id = requirement["id"]
            mapped = evidence_by_requirement.get(requirement_id, [])
            if not mapped:
                unknowns.append(requirement_id)
                continue
            if any("direct" in entry.lower() for entry in mapped):
                direct_evidence.append(requirement_id)
            else:
                related_evidence.append(requirement_id)

        direct_summary = ", ".join(sorted(set(direct_evidence))) or "none mapped"
        related_summary = ", ".join(sorted(set(related_evidence))) or "none mapped"
        unknown_summary = ", ".join(sorted(set(unknowns))) or "none flagged"

        focus = ", ".join(self.themes) if self.themes else "general portfolio"
        return (
            f"Role: {self.target_role or 'target role'}.\n"
            f"Focus: {focus}.\n"
            f"Direct evidence: {direct_summary}.\n"
            f"Related evidence: {related_summary}.\n"
            f"Unknowns: {unknown_summary}.\n"
            "Guidance: lead with direct evidence, keep personal projects separate from professional experience, "
            "label transferability clearly, and say when a requirement is not documented instead of inferring a negative."
        )


GENERAL_PROFILE = RecruiterProfile(
    profile_id="general",
    company_name=None,
    target_role=None,
    themes=(),
    welcome={},
    questions={},
    positioning={},
    requirements=(),
    evidence=(),
)


def _load_profile(path: Path, requested_id: str) -> RecruiterProfile:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Profile {path.name} must contain a JSON object")

    requirements = tuple(data.get("requirements", ()))
    requirement_ids = {item["id"] for item in requirements}
    evidence = tuple(data.get("evidence", ()))
    for item in evidence:
        if item["requirement_id"] not in requirement_ids:
            raise ValueError(
                f"Profile {path.name} evidence references unknown requirement "
                f"{item['requirement_id']!r}"
            )

    profile = RecruiterProfile(
        profile_id=data["id"],
        company_name=data.get("company_name"),
        target_role=data.get("target_role"),
        themes=tuple(data.get("themes", ())),
        welcome=data.get("welcome", {}),
        questions={
            language: tuple(questions)
            for language, questions in data.get("questions", {}).items()
        },
        positioning=data.get("positioning", {}),
        requirements=requirements,
        evidence=evidence,
    )
    if profile.profile_id != path.stem or profile.profile_id != requested_id:
        raise ValueError(f"Profile id must match its filename: {path.name}")
    return profile


def get_profile(profile_id: str) -> RecruiterProfile:
    """Load one curated profile by slug, or raise ``KeyError`` if it is missing.

    Reading on demand keeps Cloud Storage volume uploads visible without an
    application image rebuild or a process restart.
    """
    if profile_id == GENERAL_PROFILE.profile_id:
        return GENERAL_PROFILE
    if not PROFILE_ID_PATTERN.fullmatch(profile_id):
        raise KeyError(profile_id)
    path = PROFILES_DIR / f"{profile_id}.json"
    if not path.is_file():
        raise KeyError(profile_id)
    return _load_profile(path, profile_id)
