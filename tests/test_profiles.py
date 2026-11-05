"""Curated recruiter profiles and profile-scoped chat requests."""

import sys
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from fastapi.testclient import TestClient  # noqa: E402

from cv_chat import server  # noqa: E402
from cv_chat import profiles  # noqa: E402
from cv_chat.profiles import get_profile  # noqa: E402


class RecruiterProfileTests(unittest.TestCase):
    def test_demo_profile_public_data_excludes_private_prompt_context(self):
        profile = get_profile("acme")
        payload = profile.public_payload()

        self.assertEqual(payload["company_name"], "Acme (demo)")
        self.assertIn("MCP servers", payload["focus_areas"])
        self.assertIn("es", payload["questions"])
        self.assertNotIn("prompt_context", payload)
        self.assertNotIn("requirements", payload)
        self.assertNotIn("evidence", payload)

    def test_general_profile_has_no_offer_context_or_fit_claim(self):
        profile = get_profile("general")

        self.assertEqual(profile.prompt_context, "")
        self.assertEqual(profile.requirements, ())
        self.assertEqual(profile.evidence, ())

    def test_profile_is_read_from_configured_directory_on_each_request(self):
        source = Path(__file__).resolve().parents[1] / "profiles" / "acme.json"
        with tempfile.TemporaryDirectory() as temp_dir:
            profile_path = Path(temp_dir) / "acme.json"
            shutil.copyfile(source, profile_path)
            with patch.object(profiles, "PROFILES_DIR", Path(temp_dir)):
                self.assertEqual(get_profile("acme").company_name, "Acme (demo)")
                data = json.loads(profile_path.read_text(encoding="utf-8"))
                data["company_name"] = "Uploaded profile"
                profile_path.write_text(json.dumps(data), encoding="utf-8")
                self.assertEqual(get_profile("acme").company_name, "Uploaded profile")

    def test_uploaded_profile_id_and_evidence_references_are_validated(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            profile_path = Path(temp_dir) / "acme.json"
            with patch.object(profiles, "PROFILES_DIR", Path(temp_dir)):
                profile_path.write_text(json.dumps({"id": "other"}), encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "match its filename"):
                    get_profile("acme")

                profile_path.write_text(
                    json.dumps({
                        "id": "acme",
                        "requirements": [{"id": "req-1"}],
                        "evidence": [{"requirement_id": "missing"}],
                    }),
                    encoding="utf-8",
                )
                with self.assertRaisesRegex(ValueError, "unknown requirement"):
                    get_profile("acme")

                with self.assertRaises(KeyError):
                    get_profile("../cv")

    def test_offer_profile_keeps_role_rubric_server_side(self):
        profile = get_profile("conversational-crm-agentic-runtime")
        payload = profile.public_payload()
        prompt_context = profile.prompt_context

        self.assertIn("Professional software and LLM work", payload["focus_areas"])
        self.assertIn("ingeniero de software", payload["positioning"]["es"])
        self.assertNotIn("MCP", payload["positioning"]["es"])
        self.assertTrue(payload["welcome"]["es"].startswith("¡Hola, equipo de Conversational CRM!"))
        self.assertNotIn("requirements", payload)
        self.assertNotIn("evidence", payload)
        self.assertNotIn("TextYess", prompt_context)
        self.assertIn("real users", prompt_context)
        self.assertIn("professional experience (related; cv_professional)", prompt_context)
        self.assertIn("listed skill (listed_only; cv_skills)", prompt_context)
        self.assertIn("Do not volunteer a list of weaknesses", prompt_context)
        suggestions = [
            item["question"].casefold()
            for language_questions in payload["questions"].values()
            for item in language_questions
        ]
        self.assertTrue(any("por qué encaja" in item or "why is" in item for item in suggestions))
        self.assertFalse(
            any(
                word in question
                for question in suggestions
                for word in ("weakness", "gap", "missing", "debilidad", "carencia", "falta")
            )
        )

    def test_profile_endpoint_returns_demo_profile_and_rejects_unknown_slugs(self):
        with TestClient(server.app) as client:
            response = client.get("/api/profiles/acme")
            offer_demo = client.get(
                "/api/profiles/conversational-crm-agentic-runtime"
            )
            missing = client.get("/api/profiles/unknown")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["id"], "acme")
        self.assertEqual(offer_demo.status_code, 200)
        self.assertIn("Evaluation and observability", offer_demo.json()["focus_areas"])
        self.assertNotIn("TextYess", offer_demo.text)
        self.assertNotIn("requirements", offer_demo.json())
        self.assertNotIn("evidence", offer_demo.json())
        self.assertEqual(missing.status_code, 404)

    def test_chat_uses_server_profile_context_and_scopes_thread_id(self):
        calls = []

        async def fake_stream(_graph, message, thread_id, profile_context, history=()):
            calls.append((message, thread_id, profile_context, history))
            yield {"token": "ok"}
            yield {"done": True}

        with patch.object(server, "astream_turn", fake_stream), TestClient(server.app) as client:
            response = client.post(
                "/api/chat",
                json={
                    "message": "¿Qué experiencia tiene con MCP?",
                    "thread_id": "same-browser-id",
                    "profile_id": "acme",
                    "history": [
                        {"role": "user", "content": "first question"},
                        {"role": "assistant", "content": "first answer"},
                    ],
                },
            )
            general = client.post(
                "/api/chat",
                json={
                    "message": "¿Qué experiencia aporta Adrián a un puesto de AI Engineer?",
                    "thread_id": "same-browser-id",
                    "profile_id": "general",
                    "history": [],
                },
            )
            invalid_profile = client.post(
                "/api/chat",
                json={
                    "message": "Hello",
                    "thread_id": "same-browser-id",
                    "profile_id": "unknown",
                },
            )
            invalid_history = client.post(
                "/api/chat",
                json={
                    "message": "Hello",
                    "thread_id": "same-browser-id",
                    "history": [{"role": "user", "content": "unpaired"}],
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(general.status_code, 200)
        self.assertEqual(invalid_profile.status_code, 404)
        self.assertEqual(invalid_history.status_code, 422)
        self.assertEqual(len(calls), 2)
        message, thread_id, profile_context, history = calls[0]
        self.assertEqual(message, "¿Qué experiencia tiene con MCP?")
        self.assertEqual(thread_id, "acme:same-browser-id")
        self.assertIn("not evidence about Adrián or the company", profile_context)
        self.assertEqual(
            history,
            [
                {"role": "user", "content": "first question"},
                {"role": "assistant", "content": "first answer"},
            ],
        )
        self.assertEqual(calls[1][0], "¿Qué experiencia aporta Adrián a un puesto de AI Engineer?")
        self.assertEqual(calls[1][1], "general:same-browser-id")
        self.assertEqual(calls[1][2], "")


if __name__ == "__main__":
    unittest.main()
