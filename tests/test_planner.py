import unittest

from agent_core.planner import AgentPlanner


class PlannerTests(unittest.TestCase):
    def test_greeting_plan_has_no_tool(self):
        """Verify plain chat produces a direct-response plan."""

        plan = AgentPlanner().build_plan("hi")
        self.assertEqual(plan.intent, "plain_chat")
        self.assertIsNone(plan.tool)
        self.assertGreater(plan.confidence, 0.9)
        self.assertFalse(plan.ambiguous)
        self.assertEqual(plan.verification, "confirm no tool/provider was required")
        self.assertEqual(plan.delegations[0]["agent_id"], "manager")
        self.assertEqual(plan.delegations[1]["agent_id"], "direct-responder")
        self.assertEqual(plan.concurrency["serial_order"], ["manager", "direct-responder"])
        self.assertEqual(plan.specialist["identifier"], "direct-responder")

    def test_visual_plan_selects_template_tool(self):
        """Verify visual prompts plan a single rich output tool call."""

        plan = AgentPlanner().build_plan("show graph of microservice architecture")
        self.assertEqual(plan.intent, "visualize")
        self.assertEqual(plan.tool, "rich_output_template_tool")
        self.assertIn("Mermaid", plan.verification)
        self.assertGreaterEqual(len(plan.steps), 4)
        self.assertGreaterEqual(len(plan.alternatives), 2)
        self.assertTrue(plan.ambiguous)
        self.assertEqual(plan.specialist["identifier"], "visual-renderer")
        self.assertIn("rich_output_template_tool", plan.specialist["permissions"])
        self.assertIn("verifier", [assignment["agent_id"] for assignment in plan.delegations])
        self.assertIn(["verifier"], plan.concurrency["parallel_groups"])

    def test_code_plan_includes_read_only_reviewer_candidate(self):
        """Verify code requests expose future parallel review assignment."""

        plan = AgentPlanner().build_plan("fix web/app.js")
        self.assertEqual(plan.intent, "code_edit")
        self.assertEqual(plan.specialist["identifier"], "implementation-runner")
        self.assertIn("reviewer", [assignment["agent_id"] for assignment in plan.delegations])
        self.assertIn("reviewer", [item["agent_id"] for item in plan.concurrency["blocked_parallel"]])


if __name__ == "__main__":
    unittest.main()
