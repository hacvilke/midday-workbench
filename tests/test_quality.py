import unittest

from agent_core.quality import quality_gate_manifest, required_quality_commands, run_quality_gates
from agent_core.sandbox import ExecutionSandbox
from agent_core.config import PROJECT_ROOT, get_config


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

    def test_run_quality_gates_shape(self):
        """Verify batch quality runner returns verifier-backed results."""

        report = run_quality_gates(required_only=True, dry_run=True)
        self.assertIn("passed", report)
        self.assertIn("results", report)
        self.assertGreaterEqual(len(report["results"]), 1)
        self.assertIn("verified", report["results"][0])

    def test_quality_gates_target_app_repo(self):
        """Verify quality gates run from the Midday app repo, not parent OSS workspace."""

        self.assertTrue((PROJECT_ROOT / "server.py").exists())
        report = run_quality_gates(required_only=True, dry_run=True)
        git_status = [item for item in report["results"] if item["name"] == "git_status"][0]
        self.assertTrue(git_status["verified"]["passed"])


if __name__ == "__main__":
    unittest.main()
