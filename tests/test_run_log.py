import unittest

from agent_core.agent import AgentRun
from agent_core.run_log import (
    add_command_run,
    add_run,
    clear_command_runs,
    clear_runs,
    recent_command_runs,
    recent_runs,
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
        clear_runs(session_id)

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
        )
        rows = recent_command_runs(session_id=session_id)
        self.assertEqual(rows[0]["command"], "python --version")
        self.assertTrue(rows[0]["verified"]["passed"])
        clear_command_runs(session_id)


if __name__ == "__main__":
    unittest.main()
