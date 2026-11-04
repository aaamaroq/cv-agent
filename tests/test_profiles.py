"""Curated recruiter profiles and profile-scoped chat requests."""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from fastapi.testclient import TestClient  # noqa: E402

from cv_chat import server  # noqa: E402
from cv_chat.profiles import get_profile  # noqa: E402


class RecruiterProfileTests(unittest.TestCase):
    def test_demo_profile_public_data_excludes_private_prompt_context(self):
        profile = get_profile("acme")
        payload = profile.public_payload()

        self.assertEqual(payload["company_name"], "Acme (demo)")
        self.assertIn("MCP servers", payload["focus_areas"])
        self.assertIn("es", payload["questions"])
        self.assertNotIn("prompt_context", payload)

    def test_profile_endpoint_returns_demo_profile_and_rejects_unknown_slugs(self):
        with TestClient(server.app) as client:
            response = client.get("/api/profiles/acme")
            missing = client.get("/api/profiles/unknown")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["id"], "acme")
        self.assertEqual(missing.status_code, 404)

    def test_chat_uses_server_profile_context_and_scopes_thread_id(self):
        calls = []

        async def fake_stream(_graph, message, thread_id, profile_context):
            calls.append((message, thread_id, profile_context))
            yield {"token": "ok"}
            yield {"done": True}

        with patch.object(server, "astream_turn", fake_stream), TestClient(server.app) as client:
            response = client.post(
                "/api/chat",
                json={
                    "message": "¿Qué experiencia tiene con MCP?",
                    "thread_id": "same-browser-id",
                    "profile_id": "acme",
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

        self.assertEqual(response.status_code, 200)
        self.assertEqual(invalid_profile.status_code, 404)
        self.assertEqual(len(calls), 1)
        message, thread_id, profile_context = calls[0]
        self.assertEqual(message, "¿Qué experiencia tiene con MCP?")
        self.assertEqual(thread_id, "acme:same-browser-id")
        self.assertIn("fictional company Acme", profile_context)


if __name__ == "__main__":
    unittest.main()
