"""Per-turn policy tests."""

import unittest

from agent_core.turn_policy import classify_turn_policy


class TurnPolicyTests(unittest.TestCase):
    def test_no_tools_turn_blocks_tools(self):
        policy = classify_turn_policy("Do not use tools, just explain the idea.")

        self.assertTrue(policy.block_tools)
        self.assertEqual(policy.mode, "guide_only")

    def test_normal_turn_allows_tools(self):
        policy = classify_turn_policy("make me a graph")

        self.assertFalse(policy.block_tools)
        self.assertEqual(policy.mode, "normal")


if __name__ == "__main__":
    unittest.main()
