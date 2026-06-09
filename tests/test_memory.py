import unittest

from agent_core.memory import (
    clear_session,
    get_session_summary,
    add_message,
    memory_stats,
    summarize_exchange,
    update_session_summary,
)


class MemorySummaryTests(unittest.TestCase):
    def test_summarize_exchange_mentions_visual_output(self):
        """Verify Mermaid answers are condensed as visual outcomes."""

        summary = summarize_exchange("show graph", "```mermaid\ngraph TD\nA --> B\n```")
        self.assertIn("visual Mermaid", summary)

    def test_update_and_clear_summary(self):
        """Verify session summaries persist and clear with the session."""

        session_id = "summary-test"
        clear_session(session_id)
        updated = update_session_summary(session_id, "hi", "Hi. I am Midday Workbench.")
        self.assertIn("User asked: hi", updated["summary"])
        loaded = get_session_summary(session_id)
        self.assertEqual(loaded["summary"], updated["summary"])
        clear_session(session_id)
        self.assertEqual(get_session_summary(session_id)["summary"], "")

    def test_memory_stats_reports_counts_and_summary_state(self):
        """Verify memory telemetry exposes session message and summary state."""

        session_id = "memory-stats-test"
        clear_session(session_id)
        add_message(session_id, "user", "remember this")
        stats = memory_stats(session_id=session_id)
        self.assertEqual(stats["message_count"], 1)
        self.assertFalse(stats["has_summary"])
        update_session_summary(session_id, "remember this", "Stored.")
        stats = memory_stats(session_id=session_id)
        self.assertTrue(stats["has_summary"])
        self.assertGreater(stats["summary_chars"], 0)
        clear_session(session_id)


if __name__ == "__main__":
    unittest.main()
