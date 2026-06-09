import tempfile
import unittest
from pathlib import Path

from agent_core.context_window import ContextWindow
from agent_core.oss_tools import ToolResult
from agent_core.session import load_session_state, save_session_state


class ContextWindowTests(unittest.TestCase):
    def test_context_window_serializes_tool_result(self):
        window = ContextWindow()
        window.add_tool_result(ToolResult("tool_a", "summary", "content"))
        loaded = ContextWindow.deserialize(window.serialize())
        self.assertEqual(loaded.items[0].tool, "tool_a")
        self.assertIn("tool_a", loaded.chained_query("next"))

    def test_session_state_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "session_state.json"
            window = ContextWindow()
            window.add_tool_result(ToolResult("tool_b", "summary", "content"))
            save_session_state(window, path=path)
            loaded = load_session_state(path=path)
            self.assertEqual(loaded.items[0].tool, "tool_b")


if __name__ == "__main__":
    unittest.main()
