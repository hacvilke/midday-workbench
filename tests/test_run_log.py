import unittest

from agent_core.agent import AgentRun
from agent_core.run_log import (
    add_command_run,
    add_decision,
    add_file_event,
    add_run,
    activity_timeline,
    clear_command_runs,
    clear_decisions,
    clear_file_events,
    clear_runs,
    get_run,
    recent_decisions,
    recent_command_runs,
    recent_file_events,
    recent_runs,
    operational_metrics,
)


class RunLogTests(unittest.TestCase):
    def test_run_log_roundtrip(self):
        """Verify run metadata can be persisted and retrieved."""

        run = AgentRun(
            run_id="run-test",
            answer="answer",
            tools_used=["tool"],
            react_steps=[],
            context_attached=False,
            memory_items=0,
            provider="offline",
            duration_ms=1,
            fallback_used=False,
            error=None,
            provider_attempts=[{"provider": "offline", "ok": True, "duration_ms": 1, "error": None}],
            plan={"intent": "test", "tool": None},
        )
        session_id = "run-log-test"
        clear_runs(session_id)
        add_run(session_id, "prompt", run)
        rows = recent_runs(session_id=session_id)
        self.assertEqual(rows[0]["run_id"], "run-test")
        self.assertEqual(rows[0]["tools_used"], ["tool"])
        self.assertEqual(rows[0]["plan"]["intent"], "test")
        detail = get_run("run-test")
        self.assertIsNotNone(detail)
        self.assertEqual(detail["prompt"], "prompt")
        clear_runs(session_id)

    def test_get_run_missing_returns_none(self):
        """Verify missing run detail lookup is explicit."""

        self.assertIsNone(get_run("missing-run-id"))

    def test_command_run_roundtrip(self):
        """Verify sandbox command runs can be persisted and retrieved."""

        session_id = "command-log-test"
        clear_command_runs(session_id)
        add_command_run(
            session_id,
            "python --version",
            0,
            "Python 3",
            {"passed": True, "issues": [], "summary": "exit=0"},
            12,
            {
                "allowed": True,
                "reason": "command is allowlisted",
                "matched_prefix": "python --version",
            },
        )
        rows = recent_command_runs(session_id=session_id)
        self.assertEqual(rows[0]["command"], "python --version")
        self.assertTrue(rows[0]["verified"]["passed"])
        self.assertTrue(rows[0]["policy_decision"]["allowed"])
        self.assertEqual(rows[0]["policy_decision"]["matched_prefix"], "python --version")
        clear_command_runs(session_id)

    def test_decision_roundtrip(self):
        """Verify route/policy decisions can be persisted and retrieved."""

        session_id = "decision-log-test"
        clear_decisions(session_id)
        add_decision(session_id, "route", "show graph", {"intent": "visualize"})
        rows = recent_decisions(session_id=session_id)
        self.assertEqual(rows[0]["kind"], "route")
        self.assertEqual(rows[0]["decision"]["intent"], "visualize")
        clear_decisions(session_id)

    def test_file_event_roundtrip(self):
        """Verify file mutation events can be persisted and retrieved."""

        session_id = "file-event-test"
        clear_file_events(session_id)
        add_file_event(
            session_id,
            "write",
            {
                "path": "web/app.js",
                "bytes_written": 12,
                "lines": 2,
                "sha256": "a" * 64,
                "created": False,
                "message": "Written 12 bytes",
            },
        )
        rows = recent_file_events(session_id=session_id)
        self.assertEqual(rows[0]["action"], "write")
        self.assertEqual(rows[0]["path"], "web/app.js")
        self.assertEqual(rows[0]["bytes_written"], 12)
        self.assertEqual(rows[0]["sha256"], "a" * 64)
        clear_file_events(session_id)

    def test_operational_metrics_shape(self):
        """Verify metrics summarize runs, commands, decisions, and verifier state."""

        metrics = operational_metrics(session_id="missing-metrics-session")
        self.assertIn("runs", metrics)
        self.assertIn("commands", metrics)
        self.assertIn("files", metrics)
        self.assertIn("decisions", metrics)
        self.assertIn("verifier", metrics)
        self.assertEqual(metrics["runs"]["count"], 0)

    def test_activity_timeline_merges_events(self):
        """Verify runs, commands, and decisions merge into one activity stream."""

        session_id = "timeline-test"
        clear_runs(session_id)
        clear_command_runs(session_id)
        clear_file_events(session_id)
        clear_decisions(session_id)
        run = AgentRun(
            run_id="timeline-run",
            answer="answer",
            tools_used=[],
            react_steps=[],
            context_attached=False,
            memory_items=0,
            provider="local",
            duration_ms=1,
            fallback_used=False,
            error=None,
            provider_attempts=[{"provider": "local", "ok": True, "duration_ms": 1, "error": None}],
            plan={"intent": "plain_chat"},
        )
        add_run(session_id, "hi", run)
        add_command_run(
            session_id,
            "git status",
            0,
            "ok",
            {"passed": True, "issues": [], "summary": "exit=0"},
            1,
            {"allowed": True, "matched_prefix": "git status"},
        )
        add_decision(session_id, "route", "hi", {"intent": "plain_chat"})
        add_file_event(
            session_id,
            "patch",
            {
                "path": "server.py",
                "bytes_written": 20,
                "lines": 1,
                "sha256": "b" * 64,
                "created": False,
                "message": "Patched server.py",
            },
        )
        events = activity_timeline(session_id=session_id)
        self.assertEqual({"run", "command", "decision", "file"}, {event["type"] for event in events})
        clear_runs(session_id)
        clear_command_runs(session_id)
        clear_file_events(session_id)
        clear_decisions(session_id)


if __name__ == "__main__":
    unittest.main()
