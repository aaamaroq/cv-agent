"""Runtime settings reject invalid resource limits at startup."""

import os
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from cv_chat.config import get_settings  # noqa: E402


class SettingsValidationTests(unittest.TestCase):
    def tearDown(self):
        get_settings.cache_clear()

    def settings_from_env(self, values):
        get_settings.cache_clear()
        with mock.patch.dict(os.environ, values, clear=True):
            return get_settings()

    def test_resource_limit_defaults_are_valid(self):
        settings = self.settings_from_env({})
        self.assertEqual(settings.model, "openai/gpt-oss-20b")
        self.assertEqual(
            settings.guardrail_model, "openai/gpt-oss-20b"
        )
        self.assertEqual(settings.history_window, 24)
        self.assertEqual(settings.llm_timeout_s, 60.0)
        self.assertFalse(settings.langfuse_configured)

    def test_langfuse_requires_enabled_flag_and_all_local_credentials(self):
        settings = self.settings_from_env({
            "CV_LANGFUSE_ENABLED": "true",
            "LANGFUSE_PUBLIC_KEY": "pk-lf-local",
            "LANGFUSE_SECRET_KEY": "sk-lf-local",
            "LANGFUSE_BASE_URL": "http://langfuse-web:3000",
        })
        self.assertTrue(settings.langfuse_configured)

        disabled = self.settings_from_env({
            "CV_LANGFUSE_ENABLED": "false",
            "LANGFUSE_PUBLIC_KEY": "pk-lf-local",
            "LANGFUSE_SECRET_KEY": "sk-lf-local",
            "LANGFUSE_BASE_URL": "http://langfuse-web:3000",
        })
        self.assertFalse(disabled.langfuse_configured)

    def test_minimum_allowed_resource_limits_are_valid(self):
        settings = self.settings_from_env({
            "CV_HISTORY_WINDOW": "4",
            "CV_LLM_TIMEOUT_S": "0.001",
        })
        self.assertEqual(settings.history_window, 4)
        self.assertEqual(settings.llm_timeout_s, 0.001)

    def test_out_of_range_limits_fail_during_settings_load(self):
        cases = (
            ({"CV_HISTORY_WINDOW": "3"}, "CV_HISTORY_WINDOW"),
            ({"CV_LLM_TIMEOUT_S": "0"}, "CV_LLM_TIMEOUT_S"),
            ({"CV_LLM_TIMEOUT_S": "0.0005"}, "CV_LLM_TIMEOUT_S"),
            ({"CV_LLM_TIMEOUT_S": "nan"}, "CV_LLM_TIMEOUT_S"),
            ({"CV_LLM_TIMEOUT_S": "inf"}, "CV_LLM_TIMEOUT_S"),
        )
        for env, setting_name in cases:
            with self.subTest(env=env), mock.patch.dict(os.environ, env, clear=True):
                get_settings.cache_clear()
                with self.assertRaisesRegex(ValueError, setting_name):
                    get_settings()


if __name__ == "__main__":
    unittest.main()
