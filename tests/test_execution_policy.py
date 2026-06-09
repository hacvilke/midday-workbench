import unittest

from agent_core.agent import Agent
from agent_core.oss_tools import ToolResult
from agent_core.execution_policy import decide, policy_manifest


class ExecutionPolicyTests(unittest.TestCase):
    def test_safe_action_allowed(self):
        """Verify read-only actions can run without confirmation."""

        decision = decide("sandbox_readonly")
        self.assertTrue(decision.allowed)
        self.assertFalse(decision.requires_confirmation)

    def test_write_action_requires_confirmation(self):
        """Verify workspace mutations require explicit confirmation."""

        decision = decide("write_file")
        self.assertFalse(decision.allowed)
        self.assertTrue(decision.requires_confirmation)

    def test_destructive_action_blocked(self):
        """Verify destructive actions are blocked outright."""

        decision = decide("delete_file")
        self.assertFalse(decision.allowed)
        self.assertFalse(decision.requires_confirmation)

    def test_policy_manifest_shape(self):
        """Verify policy manifest is structured for API/UI use."""

        manifest = policy_manifest()
        self.assertIn("safe_actions", manifest)
        self.assertIn("confirmation_actions", manifest)
        self.assertIn("blocked_actions", manifest)
        self.assertIn("examples", manifest)

    def test_agent_file_write_post_processing_requires_confirmation(self):
        """Verify automatic file writes are gated by policy."""

        agent = Agent()
        answer = "```python\nprint('hello')\n```"
        guarded = agent._maybe_write_file(
            "write file tmp_policy_agent.py",
            [ToolResult("file_edit_tool", "summary", "content")],
            answer,
        )
        self.assertIn("not applied", guarded)


if __name__ == "__main__":
    unittest.main()
