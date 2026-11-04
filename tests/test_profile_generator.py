"""Offline checks for offer-to-evidence recruiter profile generation."""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from build_profile import (  # noqa: E402
    CandidateEvidence,
    ProfileDraft,
    RoleRequirement,
    SuggestedQuestion,
    build_profile_document,
    validate_draft,
)


def _questions(prefix: str) -> list[SuggestedQuestion]:
    return [
        SuggestedQuestion(label=f"{prefix} {number}", question=f"Question {number}?")
        for number in range(1, 4)
    ]


class ProfileGeneratorTests(unittest.TestCase):
    def setUp(self):
        self.offer = (
            "Build agent runtimes with tool and retrieval orchestration. "
            "Professional LLM work used by real customers is required."
        )
        self.cv = """## Summary
Software engineer with over three years of experience.

## Technical Skills
grounded retrieval (RAG)

## Professional Experience
Built MCP servers to support enterprise LLM workflows.

## AI Projects
Designed a personal LangGraph agent with guardrails.

## Professional Development
Completed a course covering Agentic RAG.
"""
        self.project_notes = "Langfuse traces and an evaluation harness are implemented."
        self.draft = ProfileDraft(
            requirements=[
                RoleRequirement(
                    id="agent-runtime",
                    label="Agent runtime",
                    description="Build agent runtimes with tool and retrieval orchestration.",
                    priority="required",
                    offer_quote="tool and retrieval orchestration",
                ),
                RoleRequirement(
                    id="professional-llm",
                    label="Professional LLM work",
                    description="Professional LLM work used by real customers.",
                    priority="required",
                    offer_quote="Professional LLM work used by real customers",
                ),
            ],
            evidence=[
                CandidateEvidence(
                    requirement_id="agent-runtime",
                    source="cv_professional",
                    evidence_type="professional experience",
                    relation="related",
                    quote="Built MCP servers to support enterprise LLM workflows.",
                ),
                CandidateEvidence(
                    requirement_id="agent-runtime",
                    source="cv_projects",
                    evidence_type="personal project",
                    relation="related",
                    quote="Designed a personal LangGraph agent with guardrails.",
                ),
            ],
            positioning_es="Experiencia profesional relacionada con LLMs y agentes.",
            positioning_en="Professional experience related to LLMs and agents.",
            questions_es=_questions("ES"),
            questions_en=_questions("EN"),
        )

    def test_semantic_relationship_does_not_require_literal_overlap(self):
        validate_draft(self.draft, self.offer, self.cv, self.project_notes)

    def test_rejects_requirement_without_exact_offer_quote(self):
        draft = self.draft.model_copy(
            update={
                "requirements": [
                    self.draft.requirements[0].model_copy(
                        update={"offer_quote": "vector database wizard"}
                    ),
                    self.draft.requirements[1],
                ]
            }
        )
        with self.assertRaisesRegex(ValueError, "exact supporting quote in the offer"):
            validate_draft(draft, self.offer, self.cv, self.project_notes)

    def test_rejects_candidate_quote_from_wrong_or_missing_source(self):
        draft = self.draft.model_copy(
            update={
                "evidence": [
                    self.draft.evidence[0].model_copy(
                        update={"quote": "Adrián has shipped production RAG."}
                    )
                ]
            }
        )
        with self.assertRaisesRegex(ValueError, "no exact quote in cv_professional"):
            validate_draft(draft, self.offer, self.cv, self.project_notes)

    def test_skills_and_training_cannot_be_marked_as_demonstrated_experience(self):
        skill_evidence = CandidateEvidence(
            requirement_id="agent-runtime",
            source="cv_skills",
            evidence_type="listed skill",
            relation="related",
            quote="grounded retrieval (RAG)",
        )
        draft = self.draft.model_copy(update={"evidence": [skill_evidence]})
        with self.assertRaisesRegex(ValueError, "must use relation 'listed_only'"):
            validate_draft(draft, self.offer, self.cv, self.project_notes)

    def test_evidence_must_reference_a_real_role_criterion(self):
        evidence = self.draft.evidence[0].model_copy(
            update={"requirement_id": "unknown-requirement"}
        )
        draft = self.draft.model_copy(update={"evidence": [evidence]})
        with self.assertRaisesRegex(ValueError, "unknown requirement"):
            validate_draft(draft, self.offer, self.cv, self.project_notes)

    def test_rejects_suggested_starters_that_focus_on_weaknesses(self):
        draft = self.draft.model_copy(
            update={
                "questions_es": [
                    self.draft.questions_es[0].model_copy(
                        update={"question": "¿Qué carencias tiene Adrián para este puesto?"}
                    ),
                    *self.draft.questions_es[1:],
                ]
            }
        )
        with self.assertRaisesRegex(ValueError, "not focus on weaknesses or gaps"):
            validate_draft(draft, self.offer, self.cv, self.project_notes)

    def test_public_profile_omits_offer_quotes_but_retains_private_evidence_map(self):
        document = build_profile_document("demo", "Demo", "AI Engineer", self.draft)

        self.assertEqual(document["requirements"][0]["id"], "agent-runtime")
        self.assertNotIn("offer_quote", str(document))
        self.assertIn(self.draft.evidence[0].quote, str(document))
        self.assertNotIn(self.offer, str(document))
        self.assertTrue(document["welcome"]["es"].startswith("¡Hola, equipo de Demo!"))
        self.assertIn("question", document["questions"]["es"][0])


if __name__ == "__main__":
    unittest.main()
