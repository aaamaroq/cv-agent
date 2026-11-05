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
                f"Prioritize documented CV or project evidence relevant to these "
                f"offer themes: {themes}. The themes are relevance guidance only, "
                "not evidence about Adrián or the company. They do not define "
                "the role's full requirements or establish a candidate match."
            )

        requirements = "\n".join(
            f"- [{item['priority']}] {item['id']}: {item['description']}"
            for item in self.requirements
        )
        evidence_by_requirement: dict[str, list[str]] = {}
        for item in self.evidence:
            evidence_by_requirement.setdefault(item["requirement_id"], []).append(
                f"  - {item['evidence_type']} ({item['relation']}; {item['source']}): "
                f"{item['quote']}"
            )
        evidence = "\n".join(
            f"- {requirement['id']}:\n"
            + "\n".join(evidence_by_requirement.get(requirement["id"], ["  - No mapped evidence."]))
            for requirement in self.requirements
        )
        return (
            f"Customized recruiter profile for {self.target_role or 'the target role'}.\n"
            "The role criteria below are sanitized descriptions of the offer, not "
            "facts about Adrián. The evidence map contains curated pointers to "
            "verbatim CV/project excerpts; verify any candidate claim against the "
            "source of truth above. 'Professional experience', 'personal project', "
            "'training', and 'listed skill' are distinct evidence types. 'Related' "
            "means transferable, not proof of the exact requirement.\n"
            "Role criteria:\n"
            f"{requirements}\n"
            "Mapped evidence:\n"
            f"{evidence}\n"
            "When directly asked about fit, compare the most relevant documented "
            "evidence with these criteria. Lead with the strongest professional "
            "evidence; use personal projects as complementary evidence and label "
            "them clearly. Do not present related, training, or listed-skill "
            "evidence as direct professional experience. Do not claim that every "
            "requirement is met or make a final hiring decision. Mention an "
            "unverified required criterion only when it materially qualifies a "
            "direct fit assessment or the recruiter asks about it; say the sources "
            "do not specify it, rather than asserting the experience does not exist. "
            "Do not volunteer a list of weaknesses."
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
