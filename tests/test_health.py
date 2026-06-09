import unittest

from agent_core.health import health_report, run_health_checks


class HealthTests(unittest.TestCase):
    def test_all_health_checks_pass(self):
        """Verify platform health checks all pass."""

        failed = [check for check in run_health_checks() if not check.passed]
        self.assertEqual(failed, [])

    def test_tool_health_is_structured(self):
        """Verify per-tool health returns structured JSON fields."""

        report = health_report()
        self.assertGreaterEqual(len(report["tools"]), 9)
        first = report["tools"][0]
        self.assertIn("tool", first)
        self.assertIn("status", first)
        self.assertIn("latency_ms", first)
        self.assertIn("last_ok_at", first)

    def test_control_plane_health_checks_exist(self):
        """Verify health checks cover policy and quality gates."""

        names = {check.name for check in run_health_checks()}
        self.assertIn("execution_policy", names)
        self.assertIn("policy_manifest", names)
        self.assertIn("quality_gates_allowlisted", names)


if __name__ == "__main__":
    unittest.main()
