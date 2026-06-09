import unittest
import tempfile
from pathlib import Path

from agent_core.agent import Agent
from agent_core.oss_tools import ToolResult
from agent_core.execution_policy import decide, policy_manifest
from agent_core.file_editor import FileEditorTool


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

    def test_file_write_metadata_includes_checksum(self):
        """Verify file writes expose audit metadata."""

        with tempfile.TemporaryDirectory() as tmp:
            editor = FileEditorTool(Path(tmp))
            result = editor.write_file_with_metadata("hello.txt", "hello\n")
            self.assertTrue(result.created)
            self.assertEqual(result.bytes_written, 6)
            self.assertEqual(result.lines, 2)
            self.assertEqual(len(result.sha256), 64)
            metadata = editor.file_metadata("hello.txt")
            self.assertEqual(metadata.sha256, result.sha256)

    def test_agent_confirmed_file_write_returns_metadata(self):
        """Verify confirmed automatic file writes return auditable metadata."""

        with tempfile.TemporaryDirectory() as tmp:
            agent = Agent()
            agent.editor = FileEditorTool(Path(tmp))
            answer = "```python\nprint('hello')\n```"
            updated, writes = agent._maybe_write_file_with_metadata(
                "confirmed write file tmp_policy_agent.py",
                [ToolResult("file_edit_tool", "summary", "content")],
                answer,
            )
            self.assertIn("Created", updated)
            self.assertEqual(len(writes), 1)
            self.assertEqual(writes[0]["path"], "tmp_policy_agent.py")
            self.assertEqual(len(writes[0]["sha256"]), 64)
            self.assertTrue((Path(tmp) / "tmp_policy_agent.py").exists())


if __name__ == "__main__":
    unittest.main()
