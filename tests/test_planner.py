import unittest

from agent_core.planner import AgentPlanner


class PlannerTests(unittest.TestCase):
    def test_greeting_plan_has_no_tool(self):
        """Verify plain chat produces a direct-response plan."""

        plan = AgentPlanner().build_plan("hi")
        self.assertEqual(plan.intent, "plain_chat")
        self.assertIsNone(plan.tool)
        self.assertEqual(plan.verification, "confirm no tool/provider was required")

    def test_visual_plan_selects_template_tool(self):
        """Verify visual prompts plan a single rich output tool call."""

        plan = AgentPlanner().build_plan("show graph of potential energy against kinetic")
        self.assertEqual(plan.intent, "visualize")
        self.assertEqual(plan.tool, "rich_output_template_tool")
        self.assertIn("Mermaid", plan.verification)
        self.assertGreaterEqual(len(plan.steps), 4)


if __name__ == "__main__":
    unittest.main()
