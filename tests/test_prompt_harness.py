"""Prompt harness tests for Midday Workbench identity and context."""

import unittest

from agent_core.config import get_config
from agent_core.prompt_harness import build_system_prompt, prompt_registry


class PromptHarnessTests(unittest.TestCase):
    def test_coordinator_identity_is_midday_workbench(self):
        """Verify the active coordinator prompt uses current product identity."""

        prompt = prompt_registry()["coordinator"]
        self.assertIn("You are Midday Workbench", prompt)
        self.assertNotIn("You are OSS Agent Workbench", prompt)

    def test_system_prompt_includes_environment_context(self):
        """Verify generated system prompts include dynamic environment context."""

        prompt = build_system_prompt(get_config())
        self.assertIn("You are Midday Workbench", prompt)
        self.assertIn("# Current Environment Context", prompt)


if __name__ == "__main__":
    unittest.main()
