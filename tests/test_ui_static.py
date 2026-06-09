import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class UiStaticTests(unittest.TestCase):
    def test_route_alternatives_rendered_in_ui(self):
        """Verify route alternatives are shown in key operator surfaces."""

        app_js = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
        self.assertIn("function formatRouteAlternatives", app_js)
        self.assertIn("formatRouteAlternatives(data.alternatives || [])", app_js)
        self.assertIn("const alternatives = plan.alternatives || []", app_js)
        self.assertIn("async function loadRoutingAudit", app_js)
        self.assertIn("function formatSandboxDecision", app_js)
        self.assertIn("formatSandboxDecision(entry.policy_decision)", app_js)
        self.assertIn("async function loadIndexStats", app_js)
        self.assertIn("write.sha256", app_js)
        self.assertIn("data.files?.count", app_js)
        self.assertIn("session_id: sessionId", app_js)


if __name__ == "__main__":
    unittest.main()
