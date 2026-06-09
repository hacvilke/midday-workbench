import unittest

from agent_core.quality import quality_gate_manifest, quality_history, required_quality_commands, run_quality_gates
from agent_core.run_log import add_command_run, clear_command_runs, recent_command_runs
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
        self.assertIn("secret_scan", [gate["name"] for gate in gates])
        self.assertIn("frontend_syntax", [gate["name"] for gate in gates])
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
        self.assertIn("policy_decision", report["results"][0])
        self.assertTrue(report["results"][0]["policy_decision"]["allowed"])

    def test_quality_gates_target_app_repo(self):
        """Verify quality gates run from the Midday app repo, not parent OSS workspace."""

        self.assertTrue((PROJECT_ROOT / "server.py").exists())
        report = run_quality_gates(required_only=True, dry_run=True)
        git_status = [item for item in report["results"] if item["name"] == "git_status"][0]
        self.assertTrue(git_status["verified"]["passed"])
        secret_scan = [item for item in report["results"] if item["name"] == "secret_scan"][0]
        self.assertTrue(secret_scan["verified"]["passed"])

    def test_quality_gate_run_persists_command_audit(self):
        """Verify actual quality runs can write command audit rows."""

        session_id = "quality-audit-test"
        clear_command_runs(session_id)
        report = run_quality_gates(required_only=False, dry_run=False, session_id=session_id, gate_names=["diff_stat"])
        diff_stat = [item for item in report["results"] if item["name"] == "diff_stat"][0]
        self.assertTrue(diff_stat["verified"]["summary"].startswith("quality:diff_stat"))
        self.assertTrue(diff_stat["policy_decision"]["allowed"])
        rows = recent_command_runs(session_id=session_id)
        self.assertGreaterEqual(len(rows), 1)
        self.assertTrue(any(row["verified"]["summary"].startswith("quality:diff_stat") for row in rows))
        self.assertTrue(any(row["policy_decision"].get("allowed") for row in rows))
        clear_command_runs(session_id)

    def test_quality_history_summarizes_persisted_gate_runs(self):
        """Verify quality command audits can be summarized separately."""

        session_id = "quality-history-test"
        clear_command_runs(session_id)
        add_command_run(
            session_id,
            "git diff --stat",
            0,
            "",
            {"passed": True, "issues": [], "summary": "quality:diff_stat exit=0"},
            3,
        )
        history = quality_history(session_id=session_id)
        self.assertEqual(history["count"], 1)
        self.assertEqual(history["passed"], 1)
        self.assertIsNone(history["latest_failed"])
        self.assertEqual(history["latest"][0]["gate"], "diff_stat")
        clear_command_runs(session_id)

    def test_quality_history_exposes_latest_failed_gate(self):
        """Verify failed gate summaries are easy for UI/control-plane consumers to find."""

        session_id = "quality-history-failed-test"
        clear_command_runs(session_id)
        add_command_run(
            session_id,
            "node --check web/app.js",
            1,
            "SyntaxError",
            {"passed": False, "issues": ["exit=1"], "summary": "quality:frontend_syntax exit=1"},
            5,
        )
        history = quality_history(session_id=session_id)
        self.assertEqual(history["failed"], 1)
        self.assertEqual(history["latest_failed"]["gate"], "frontend_syntax")
        clear_command_runs(session_id)


if __name__ == "__main__":
    unittest.main()
