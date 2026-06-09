import unittest

from agent_core.config import get_config
from agent_core.agent import Agent
from agent_core.oss_tools import OssToolRegistry
from agent_core.react_loop import ReactPlanner
from agent_core.router import IntentRouter


class RouterTests(unittest.TestCase):
    def test_greeting_uses_no_tool(self):
        """Verify greetings and identity questions do not invoke tools."""

        for message in ("hi", "hello", "help", "thanks", "who are you"):
            route = IntentRouter().classify(message)
            self.assertEqual(route.intent, "plain_chat")
            self.assertEqual(route.tools, [])

    def test_visual_graph_uses_template_tool(self):
        route = IntentRouter().classify("show me a graph of the agent architecture")
        self.assertEqual(route.intent, "visualize")
        self.assertEqual(route.tools, ["rich_output_template_tool"])

    def test_route_records_matching_alternatives(self):
        """Verify ambiguous prompts expose ranked route candidates."""

        route = IntentRouter().classify("show graph of microservice architecture")
        self.assertEqual(route.intent, "visualize")
        self.assertGreaterEqual(len(route.alternatives or []), 2)
        self.assertEqual(route.alternatives[0]["intent"], "visualize")
        self.assertIn("system_design", [item["intent"] for item in route.alternatives or []])

    def test_show_graph_without_article_uses_template_tool(self):
        """Verify show graph phrasing still routes to visual output."""

        route = IntentRouter().classify("show graph of potential energy aginst kinetic")
        self.assertEqual(route.intent, "visualize")
        self.assertEqual(route.tools, ["rich_output_template_tool"])

    def test_graph_algorithm_uses_cugraph(self):
        """Verify graph algorithm requests use cuGraph."""

        route = IntentRouter().classify("run pagerank centrality on the repository graph")
        self.assertEqual(route.intent, "analyze_graph")
        self.assertIn("cugraph_graph_tool", route.tools)
        self.assertEqual(len(route.tools), 1)

    def test_explicit_cugraph_uses_cugraph(self):
        """Verify explicit cuGraph requests use cuGraph."""

        route = IntentRouter().classify("cuGraph dependency graph ranking")
        self.assertEqual(route.intent, "analyze_graph")
        self.assertIn("cugraph_graph_tool", route.tools)
        self.assertEqual(len(route.tools), 1)

    def test_exact_prompt_tool_table(self):
        """Verify each OSS workbench routing family selects one exact tool."""

        cases = {
            "purchase order invoice": "erpnext_business_tool",
            "fix code and commit patch": "aider_git_native_tool",
            "pack repo context": "repomix_context_pack_tool",
            "https://github.com/Aider-AI/aider ingest repo": "gitingest_remote_context_tool",
            "latest news last 30 days": "last30days_research_tool",
            "microservice caching queues architecture": "system_design_tool",
            "julia compiler runtime package": "julia_language_tool",
        }
        for message, tool_name in cases.items():
            route = IntentRouter().classify(message)
            self.assertEqual(route.tools, [tool_name], message)

    def test_react_uses_intent_router(self):
        """Verify the ReAct planner follows the intent router."""

        registry = OssToolRegistry(get_config())
        steps, results, reports = ReactPlanner(registry).run("make a graph of the tools")
        self.assertEqual([result.name for result in results], ["rich_output_template_tool"])
        self.assertEqual([step.action for step in steps], ["rich_output_template_tool"])
        self.assertEqual(len(reports), len(results))

    def test_agent_greeting_direct_answer(self):
        """Verify greetings return locally without provider or tools."""

        run = Agent().run_with_metadata("hi")
        self.assertEqual(run.tools_used, [])
        self.assertEqual(run.provider, "local")
        self.assertIn("Midday Workbench", run.answer)

    def test_agent_streaming_greeting_has_plan_metadata(self):
        """Verify streaming greetings finish with structured plan metadata."""

        events = list(Agent().stream_with_events("hi"))
        done = events[-1]
        self.assertEqual(done["type"], "done")
        self.assertEqual(done["metadata"]["provider"], "local")
        self.assertEqual(done["metadata"]["tools_used"], [])
        self.assertEqual(done["metadata"]["plan"]["intent"], "plain_chat")

    def test_agent_visual_answer_is_mermaid_only(self):
        """Verify visual requests return a single Mermaid fence."""

        run = Agent().run_with_metadata("show me a graph")
        self.assertEqual(run.tools_used, ["rich_output_template_tool"])
        self.assertEqual(run.provider, "local")
        self.assertTrue(run.answer.startswith("```mermaid\n"))
        self.assertTrue(run.answer.endswith("\n```"))
        self.assertEqual(run.answer.count("```"), 2)

    def test_agent_energy_graph_fast_path(self):
        """Verify energy graph requests do not retrieve repo context or call a provider."""

        run = Agent().run_with_metadata("show graph of potential energy aginst kinetic")
        self.assertEqual(run.tools_used, ["rich_output_template_tool"])
        self.assertEqual(run.provider, "local")
        self.assertFalse(run.context_attached)
        self.assertIn("xychart-beta", run.answer)
        self.assertIn("Potential Energy", run.answer)

    def test_agent_streaming_visual_has_plan_metadata(self):
        """Verify streaming visual fast path includes planner metadata."""

        events = list(Agent().stream_with_events("show me a graph"))
        done = events[-1]
        self.assertEqual(done["type"], "done")
        self.assertEqual(done["metadata"]["tools_used"], ["rich_output_template_tool"])
        self.assertEqual(done["metadata"]["plan"]["intent"], "visualize")


if __name__ == "__main__":
    unittest.main()
