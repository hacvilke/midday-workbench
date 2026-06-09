import unittest

from agent_core.quality import quality_gate_manifest, required_quality_commands
from agent_core.sandbox import ExecutionSandbox
from agent_core.config import get_config


class QualityGateTests(unittest.TestCase):
    def test_required_quality_commands_are_allowlisted(self):
        """Verify required quality gates can run through the sandbox."""

        sandbox = ExecutionSandbox(get_config().workspace_root)
        for command in required_quality_commands():
            self.assertTrue(sandbox.is_allowed(command), command)

    def test_quality_manifest_shape(self):
        """Verify quality gate metadata is structured for API/UI use."""

        gates = quality_gate_manifest()
        self.assertGreaterEqual(len(gates), 3)
        first = gates[0]
        self.assertIn("name", first)
        self.assertIn("command", first)
        self.assertIn("purpose", first)
        self.assertIn("required", first)


if __name__ == "__main__":
    unittest.main()
