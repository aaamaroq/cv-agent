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
    if prefix == "ES":
        return [
            SuggestedQuestion(
                label=f"Encaje {number}",
                question=f"¿Por qué está Adrián preparado para este puesto {number}?",
            )
            for number in range(1, 4)
        ]
    return [
        SuggestedQuestion(
            label=f"{prefix} {number}",
            question=f"Why is Adrián prepared for this role {number}?",
        )
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
            positioning_es=(
                "Adrián es ingeniero de software con experiencia en backend distribuido, "
                "pipelines de datos y despliegues cloud. También ha trabajado con LLMs "
                "y proyectos personales con guardrails y evaluación."
            ),
            positioning_en=(
                "Adrián is a software engineer with experience in distributed backend "
                "systems, data pipelines and cloud deployment. He has also worked with "
                "LLMs and personal projects that include guardrails and evaluation."
            ),
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

    def test_rejects_generic_questions_that_do_not_answer_offer_fit(self):
        draft = self.draft.model_copy(
            update={
                "questions_es": [
                    self.draft.questions_es[0].model_copy(
                        update={
                            "label": "Tecnologías",
                            "question": "¿Qué tecnologías usa Adrián?",
                        }
                    ),
                    self.draft.questions_es[1].model_copy(
                        update={"question": "¿Qué experiencia tiene Adrián en general?"}
                    ),
                    self.draft.questions_es[2].model_copy(
                        update={"question": "¿Qué proyectos ha hecho Adrián?"}
                    ),
                ]
            }
        )
        with self.assertRaisesRegex(ValueError, "recruiter fit"):
            validate_draft(draft, self.offer, self.cv, self.project_notes)

    def test_accepts_specific_experience_question(self):
        draft = self.draft.model_copy(
            update={
                "questions_es": [
                    self.draft.questions_es[0].model_copy(
                        update={
                            "question": (
                                "¿Qué experiencia de Adrián se relaciona con "
                                "los requisitos de este puesto?"
                            )
                        }
                    ),
                    *self.draft.questions_es[1:],
                ]
            }
        )

        validate_draft(draft, self.offer, self.cv, self.project_notes)

    def test_rejects_questions_in_the_wrong_language(self):
        spanish_questions_in_english = self.draft.model_copy(
            update={"questions_en": self.draft.questions_es}
        )
        english_questions_in_spanish = self.draft.model_copy(
            update={"questions_es": self.draft.questions_en}
        )

        with self.assertRaisesRegex(ValueError, "written in English"):
            validate_draft(
                spanish_questions_in_english, self.offer, self.cv, self.project_notes
            )
        with self.assertRaisesRegex(ValueError, "written in Spanish"):
            validate_draft(
                english_questions_in_spanish, self.offer, self.cv, self.project_notes
            )

    def test_accepts_natural_spanish_positioning(self):
        draft = self.draft.model_copy(
            update={
                "positioning_es": (
                    "Adrián es ingeniero de software con experiencia en sistemas "
                    "distribuidos e ingeniería de datos; aplica inteligencia "
                    "artificial en proyectos personales."
                )
            }
        )

        validate_draft(draft, self.offer, self.cv, self.project_notes)

    def test_rejects_positioning_that_leads_with_mcp_over_professional_experience(self):
        draft = self.draft.model_copy(
            update={
                "positioning_en": (
                    "MCP and LangGraph are central to Adrián's profile. He built servers "
                    "for enterprise LLM workflows and the experience is the main story."
                )
            }
        )
        with self.assertRaisesRegex(ValueError, "backend|data|professional experience"):
            validate_draft(draft, self.offer, self.cv, self.project_notes)

    def test_public_profile_omits_offer_quotes_but_retains_private_evidence_map(self):
        document = build_profile_document("demo", "Demo", "AI Engineer", self.draft)

        self.assertEqual(document["requirements"][0]["id"], "agent-runtime")
        self.assertNotIn("offer_quote", str(document))
        self.assertIn(self.draft.evidence[0].quote, str(document))
        self.assertNotIn(self.offer, str(document))
        self.assertTrue(document["welcome"]["es"].startswith("¡Hola, equipo de Demo!"))
        self.assertIn("https://webcv-agent.vercel.app/p/demo", document["positioning"]["es"])
        self.assertIn("https://webcv-agent.vercel.app/p/demo", document["positioning"]["en"])
        self.assertIn("question", document["questions"]["es"][0])


if __name__ == "__main__":
    unittest.main()
