import unittest

from agent_core.memory import (
    clear_session,
    get_session_summary,
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


if __name__ == "__main__":
    unittest.main()
