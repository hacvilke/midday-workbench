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
    prune_history,
    retention_stats,
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
            file_writes=[{"path": "tmp.py", "sha256": "c" * 64, "bytes_written": 3, "lines": 1, "created": True}],
            usage={"prompt_chars": 6, "answer_chars": 6, "context_chars": 0},
        )
        session_id = "run-log-test"
        clear_runs(session_id)
        add_run(session_id, "prompt", run)
        rows = recent_runs(session_id=session_id)
        self.assertEqual(rows[0]["run_id"], "run-test")
        self.assertEqual(rows[0]["tools_used"], ["tool"])
        self.assertEqual(rows[0]["plan"]["intent"], "test")
        self.assertEqual(rows[0]["file_writes"][0]["path"], "tmp.py")
        self.assertEqual(rows[0]["usage"]["prompt_chars"], 6)
        detail = get_run("run-test")
        self.assertIsNotNone(detail)
        self.assertEqual(detail["prompt"], "prompt")
        self.assertEqual(detail["file_writes"][0]["sha256"], "c" * 64)
        self.assertEqual(detail["usage"]["answer_chars"], 6)
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

        session_id = "route-metrics-session"
        clear_runs(session_id)
        run = AgentRun(
            run_id="route-metrics-run",
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
            plan={"intent": "general", "confidence": 0.5, "ambiguous": True},
        )
        add_run(session_id, "unclear request", run)
        add_decision(
            session_id,
            "route",
            "show graph",
            {
                "intent": "visualize",
                "tools": ["rich_output_template_tool"],
                "confidence": 0.7,
                "alternatives": [{"intent": "visualize"}, {"intent": "system_design"}],
            },
        )
        metrics = operational_metrics(session_id=session_id)
        self.assertIn("runs", metrics)
        self.assertIn("commands", metrics)
        self.assertIn("files", metrics)
        self.assertIn("usage", metrics)
        self.assertIn("decisions", metrics)
        self.assertIn("verifier", metrics)
        self.assertIn("provider_routes", metrics)
        self.assertIn("memory", metrics)
        self.assertIn("quality_history", metrics)
        self.assertIn("context_window", metrics)
        self.assertIn("route_decisions", metrics)
        self.assertEqual(metrics["runs"]["count"], 1)
        self.assertEqual(metrics["runs"]["ambiguous_routes"], 1)
        self.assertEqual(metrics["runs"]["low_confidence_routes"], 1)
        self.assertEqual(metrics["route_decisions"]["ambiguous"], 1)
        self.assertEqual(metrics["route_decisions"]["low_confidence"], 1)
        self.assertEqual(metrics["route_decisions"]["intents"]["visualize"], 1)
        self.assertEqual(metrics["usage"]["average_prompt_chars"], 0)
        clear_runs(session_id)
        clear_decisions(session_id)

    def test_activity_timeline_merges_events(self):
        """Verify runs, commands, and decisions merge into one activity stream."""

        session_id = "timeline-test"
        clear_runs(session_id)
        clear_command_runs(session_id)
        clear_file_events(session_id)
        clear_decisions(session_id)

    def test_prune_history_keeps_newest_rows(self):
        """Verify retention pruning keeps newest audit rows per table."""

        session_id = "retention-test"
        clear_runs(session_id)
        clear_command_runs(session_id)
        for index in range(3):
            run = AgentRun(
                run_id=f"retention-run-{index}",
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
            add_run(session_id, f"prompt {index}", run)
            add_command_run(
                session_id,
                f"git status {index}",
                0,
                "ok",
                {"passed": True, "issues": [], "summary": "exit=0"},
                1,
                {"allowed": True},
            )
        before = retention_stats(session_id=session_id)
        self.assertEqual(before["counts"]["runs"], 3)
        result = prune_history(session_id=session_id, keep_per_table=1)
        self.assertEqual(result["deleted"]["runs"], 2)
        self.assertEqual(result["deleted"]["commands"], 2)
        self.assertEqual(retention_stats(session_id=session_id)["counts"]["runs"], 1)
        self.assertEqual(recent_runs(session_id=session_id)[0]["run_id"], "retention-run-2")
        clear_runs(session_id)
        clear_command_runs(session_id)
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
