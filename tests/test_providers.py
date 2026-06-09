"""Provider routing and diagnostics tests."""
from __future__ import annotations

import json
import unittest
from pathlib import Path

from agent_core.config import AgentConfig
from agent_core.providers import ChatProvider, Message, ProviderError, ProviderRouter, provider_diagnostics


class FailingStreamProvider(ChatProvider):
    name = "failing"

    def complete(self, messages):
        raise ProviderError("nope")

    def stream(self, messages):
        raise ProviderError("stream nope")
        yield ""


class GoodStreamProvider(ChatProvider):
    name = "good"

    def complete(self, messages):
        return "ok"

    def stream(self, messages):
        yield "hello "
        yield "world"


def _config(**overrides: object) -> AgentConfig:
    values = {
        "provider": "offline",
        "workspace_root": Path("."),
        "index_path": Path("data/workspace_index.sqlite3"),
        "max_tool_rounds": 4,
        "groq_api_key": "",
        "groq_model": "groq-test-model",
        "openrouter_api_key": "",
        "openrouter_model": "openrouter-test-model",
        "local_base_url": "http://127.0.0.1:11434/v1",
        "local_model": "local-test-model",
        "provider_max_tokens": 512,
        "context_char_budget": 6000,
    }
    values.update(overrides)
    return AgentConfig(**values)


class ProviderDiagnosticsTests(unittest.TestCase):
    def test_default_diagnostics_are_structured(self):
        diagnostics = provider_diagnostics(_config())

        self.assertIn("selected_provider", diagnostics)
        self.assertIn("route", diagnostics)
        self.assertIn("providers", diagnostics)
        self.assertIn("remote_ready", diagnostics)
        self.assertIsInstance(diagnostics["route"], list)
        self.assertIsInstance(diagnostics["providers"], list)
        self.assertGreaterEqual(len(diagnostics["providers"]), 1)

    def test_diagnostics_do_not_expose_api_keys(self):
        diagnostics = provider_diagnostics(
            _config(
                provider="openrouter",
                openrouter_api_key="fake-openrouter-key",
                groq_api_key="fake-groq-key",
            )
        )
        payload = json.dumps(diagnostics)

        self.assertNotIn("fake-openrouter-key", payload)
        self.assertNotIn("fake-groq-key", payload)
        for record in diagnostics["providers"]:
            self.assertNotIn("api_key", record)
            self.assertNotIn("secret", record)
            self.assertNotIn("token", record)

    def test_diagnostics_expose_safe_output_limit(self):
        diagnostics = provider_diagnostics(
            _config(provider="openrouter", openrouter_api_key="fake-openrouter-key", provider_max_tokens=384)
        )

        selected = diagnostics["providers"][0]
        self.assertEqual(selected["name"], "openrouter")
        self.assertEqual(selected["output_limit"], 384)

    def test_remote_ready_tracks_configured_remote_provider(self):
        diagnostics = provider_diagnostics(
            _config(provider="groq", groq_api_key="fake-groq-key")
        )

        self.assertTrue(diagnostics["remote_ready"])
        self.assertEqual(diagnostics["selected_provider"], "groq")


class ProviderRouterTests(unittest.TestCase):
    def test_stream_with_metadata_records_fallback_attempts(self):
        """Verify streaming fallback keeps detailed provider attempts."""

        router = ProviderRouter([FailingStreamProvider(), GoodStreamProvider()])
        events = list(router.stream_with_metadata([Message("user", "hi")]))
        metadata = events[-1]
        tokens = "".join(str(event.get("token", "")) for event in events if event["type"] == "token")
        self.assertEqual(tokens, "hello world")
        self.assertEqual(metadata["type"], "metadata")
        self.assertEqual(metadata["provider"], "good")
        self.assertTrue(metadata["fallback_used"])
        self.assertEqual([attempt.provider for attempt in metadata["attempts"]], ["failing", "good"])
        self.assertFalse(metadata["attempts"][0].ok)
        self.assertTrue(metadata["attempts"][1].ok)


if __name__ == "__main__":
    unittest.main()
