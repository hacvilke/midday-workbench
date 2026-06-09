import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class UiStaticTests(unittest.TestCase):
    def test_route_alternatives_rendered_in_ui(self):
        """Verify route alternatives are shown in key operator surfaces."""

        app_js = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
        self.assertIn("function formatRouteAlternatives", app_js)
        self.assertIn("function formatRouteDecisionSummary", app_js)
        self.assertIn("formatRouteDecisionSummary(decision)", app_js)
        self.assertIn("/api/decisions/routes", app_js)
        self.assertIn("Route Decision Summary", app_js)
        self.assertIn("formatRouteAlternatives(data.alternatives || [])", app_js)
        self.assertIn("const alternatives = plan.alternatives || []", app_js)
        self.assertIn("async function loadRoutingAudit", app_js)
        self.assertIn("function formatSandboxDecision", app_js)
        self.assertIn("formatSandboxDecision(entry.policy_decision)", app_js)
        self.assertIn("formatSandboxDecision(gate.policy_decision)", app_js)
        self.assertIn("entry.policy_decision", app_js)
        self.assertIn("Current command:", app_js)
        self.assertIn("commandInput.addEventListener(\"input\"", app_js)
        self.assertIn("async function loadIndexStats", app_js)
        self.assertIn("write.sha256", app_js)
        self.assertIn("data.files?.count", app_js)
        self.assertIn("data.runs?.ambiguous_routes", app_js)
        self.assertIn("session_id: sessionId", app_js)
        self.assertIn("plan?.confidence", app_js)
        self.assertIn("plan.ambiguous", app_js)
        self.assertIn("plan.concurrency", app_js)
        self.assertIn("concurrency serial", app_js)
        self.assertIn("metadata.file_writes", app_js)
        self.assertIn("file writes ${fileWrites", app_js)
        self.assertIn("metadata.usage", app_js)
        self.assertIn("data.usage?.average_answer_chars", app_js)
        self.assertIn("data.provider_routes?.degraded", app_js)
        self.assertIn("data.memory?.message_count", app_js)
        self.assertIn("data.quality_history?.failed", app_js)
        self.assertIn("data.commands?.latest_failed?.command", app_js)
        self.assertIn("Command Fails", app_js)
        self.assertIn("data.context_window?.item_count", app_js)
        self.assertIn("data.route_decisions?.ambiguous", app_js)
        self.assertIn("frontend_syntax_gate", app_js)
        self.assertIn("healthStatus.title", app_js)
        self.assertIn("toolHealthStatus.title", app_js)
        self.assertIn("/api/context-window/prune", app_js)
        self.assertIn("/api/memory/prune", app_js)
        self.assertIn("/api/quality/history", app_js)
        self.assertIn("data.latest_failed", app_js)
        self.assertIn("loadQualityHistory", app_js)
        self.assertIn("event.quality_gate", app_js)
        self.assertIn("formatSandboxDecision(event.policy_decision)", app_js)
        self.assertIn("data.retention?.total", app_js)
        self.assertIn("(data.risks || []).slice(0, 2)", app_js)
        self.assertIn("data.next_action", app_js)
        self.assertIn("data.action_items", app_js)
        self.assertIn("topAction.severity", app_js)
        self.assertIn("topAction.category", app_js)
        self.assertIn("provider_diagnostics", app_js)
        self.assertIn("remote_ready", app_js)
        self.assertIn("providerPanel", app_js)
        self.assertIn("Concurrency Plan", app_js)
        self.assertIn("parallel_groups", app_js)


if __name__ == "__main__":
    unittest.main()
