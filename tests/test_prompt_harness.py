"""Prompt harness tests for Midday Workbench identity and context."""

import unittest

from agent_core.config import get_config
from agent_core.prompt_harness import build_system_prompt, format_operational_guardrails, prompt_registry


class PromptHarnessTests(unittest.TestCase):
    def test_coordinator_identity_is_midday_workbench(self):
        """Verify the active coordinator prompt uses current product identity."""

        prompt = prompt_registry()["coordinator"]
        self.assertIn("You are Midday Workbench", prompt)
        self.assertNotIn("You are OSS Agent Workbench", prompt)
        self.assertIn("do not use tools", prompt)

    def test_system_prompt_includes_environment_context(self):
        """Verify generated system prompts include dynamic environment context."""

        prompt = build_system_prompt(get_config())
        self.assertIn("You are Midday Workbench", prompt)
        self.assertIn("# Current Environment Context", prompt)

    def test_system_prompt_includes_operational_guardrails(self):
        """Verify provider prompts include live routing and sandbox guardrails."""

        prompt = build_system_prompt(get_config())
        self.assertIn("# Operational Guardrails", prompt)
        self.assertIn("Routing Audit", prompt)
        self.assertIn("Command Sandbox", prompt)
        self.assertIn("Provider Route", prompt)
        self.assertIn("Parallel Policy", prompt)
        self.assertIn("Route Decision Drift", prompt)
        self.assertIn("Quality Action", prompt)
        self.assertIn("Quality Readiness", prompt)
        self.assertIn("Command Action", prompt)
        self.assertIn("Completion Evidence", prompt)
        self.assertIn("Top Operational Action", prompt)
        self.assertIn("Route Confidence Policy", prompt)
        self.assertIn("Verification Rule", prompt)

    def test_operational_guardrails_are_compact(self):
        """Verify guardrails are concise enough for every provider prompt."""

        guardrails = format_operational_guardrails(get_config())
        self.assertLess(len(guardrails), 1700)
        self.assertIn("Allowed Command Prefixes", guardrails)
        self.assertIn("latest failed", guardrails)
        self.assertIn("failed command", guardrails)
        self.assertIn("Quality Readiness", guardrails)
        self.assertIn("Completion Evidence", guardrails)
        self.assertIn("Top Operational Action", guardrails)
        self.assertIn("below 0.75 confidence", guardrails)
        self.assertIn("remote ready", guardrails)


if __name__ == "__main__":
    unittest.main()
