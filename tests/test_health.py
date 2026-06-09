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
        self.assertTrue(report["tool_health_included"])
        self.assertGreaterEqual(len(report["tools"]), 9)
        first = report["tools"][0]
        self.assertIn("tool", first)
        self.assertIn("status", first)
        self.assertIn("latency_ms", first)
        self.assertIn("last_ok_at", first)

    def test_lightweight_health_skips_tool_probes(self):
        """Verify control-plane callers can request fast platform health."""

        report = health_report(include_tools=False)
        self.assertFalse(report["tool_health_included"])
        self.assertEqual(report["tools"], [])
        self.assertGreater(len(report["checks"]), 1)
        self.assertIn("provider_diagnostics", report)
        self.assertIn("route", report["provider_diagnostics"])

    def test_health_provider_diagnostics_are_redacted(self):
        """Verify health provider metadata never exposes key fields."""

        report = health_report(include_tools=False)
        payload = str(report["provider_diagnostics"])
        self.assertNotIn("api_key", payload)
        self.assertNotIn("secret", payload)
        self.assertNotIn("token", payload)

    def test_control_plane_health_checks_exist(self):
        """Verify health checks cover policy and quality gates."""

        names = {check.name for check in run_health_checks()}
        self.assertIn("execution_policy", names)
        self.assertIn("policy_manifest", names)
        self.assertIn("quality_gates_allowlisted", names)
        self.assertIn("secret_scan", names)
        self.assertIn("frontend_syntax_gate", names)
        self.assertIn("routing_audit", names)
        self.assertIn("search_index", names)
        self.assertIn("provider_diagnostics", names)


if __name__ == "__main__":
    unittest.main()
