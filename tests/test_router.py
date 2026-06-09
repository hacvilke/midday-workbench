import unittest
from dataclasses import replace

from agent_core.config import get_config
from agent_core.agent import Agent
from agent_core.oss_tools import OssToolRegistry
from agent_core.react_loop import ReactPlanner
from agent_core.router import IntentRouter


class RouterTests(unittest.TestCase):
    def test_greeting_uses_no_tool(self):
        """Verify greetings and identity questions do not invoke tools."""

        for message in ("hi", "hello", "help", "thanks", "who are you", "what can you do"):
            route = IntentRouter().classify(message)
            self.assertEqual(route.intent, "plain_chat")
            self.assertEqual(route.tools, [])

    def test_visual_graph_uses_template_tool(self):
        route = IntentRouter().classify("show me a graph of the agent architecture")
        self.assertEqual(route.intent, "visualize")
        self.assertEqual(route.tools, ["rich_output_template_tool"])

    def test_no_tools_request_blocks_visual_tool(self):
        """Verify explicit no-tool turns override tool routing."""

        route = IntentRouter().classify("do not use tools, make me a graph")
        self.assertEqual(route.intent, "plain_chat")
        self.assertEqual(route.tools, [])
        self.assertIn("tools blocked", route.rationale)

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
        self.assertGreater(run.plan["confidence"], 0.9)
        self.assertFalse(run.plan["ambiguous"])
        self.assertEqual(run.usage["prompt_chars"], 2)
        self.assertGreater(run.usage["answer_chars"], 0)
        self.assertTrue(run.completion_evidence["provider_verified"])
        self.assertTrue(run.completion_evidence["tools_verified"])

    def test_agent_streaming_greeting_has_plan_metadata(self):
        """Verify streaming greetings finish with structured plan metadata."""

        events = list(Agent().stream_with_events("hi"))
        done = events[-1]
        self.assertEqual(done["type"], "done")
        self.assertEqual(done["metadata"]["provider"], "local")
        self.assertEqual(done["metadata"]["tools_used"], [])
        self.assertEqual(done["metadata"]["plan"]["intent"], "plain_chat")
        self.assertIn("confidence", done["metadata"]["plan"])
        self.assertIn("usage", done["metadata"])
        self.assertEqual(done["metadata"]["usage"]["prompt_chars"], 2)
        self.assertIn("completion_evidence", done["metadata"])
        self.assertTrue(done["metadata"]["completion_evidence"]["provider_verified"])

    def test_agent_streaming_general_has_provider_attempts(self):
        """Verify streamed general runs expose provider attempt metadata."""

        events = list(Agent().stream_with_events("explain Midday Workbench briefly"))
        done = events[-1]
        self.assertEqual(done["type"], "done")
        self.assertGreaterEqual(len(done["metadata"]["provider_attempts"]), 1)
        self.assertIn("provider", done["metadata"]["provider_attempts"][0])
        self.assertIn("ok", done["metadata"]["provider_attempts"][0])
        self.assertIn("completion_evidence", done["metadata"])

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
        self.assertGreater(run.usage["tool_result_chars"], 0)
        self.assertTrue(run.completion_evidence["tools_verified"])
        self.assertIn("xychart-beta", run.answer)
        self.assertIn("Potential Energy", run.answer)

    def test_agent_trading_graph_routes_to_visual_tool(self):
        """Verify natural graph wording uses local visual tooling."""

        run = Agent().run_with_metadata("make me a trading graph")
        self.assertEqual(run.tools_used, ["rich_output_template_tool"])
        self.assertEqual(run.provider, "local")
        self.assertTrue(run.answer.startswith("```mermaid\n"))

    def test_agent_capabilities_question_is_local(self):
        """Verify capability questions do not spend provider credits."""

        run = Agent().run_with_metadata("what can you do")
        self.assertEqual(run.tools_used, [])
        self.assertEqual(run.provider, "local")
        self.assertIn("Midday Workbench", run.answer)

    def test_agent_no_tools_request_is_local(self):
        """Verify guide-only requests do not invoke providers or tools."""

        run = Agent().run_with_metadata("do not use tools, make me a graph")
        self.assertEqual(run.tools_used, [])
        self.assertEqual(run.provider, "local")
        self.assertIn("without tools", run.answer)

    def test_agent_retrieved_context_is_budgeted(self):
        """Verify retrieved repository context is capped before provider calls."""

        agent = Agent()
        agent.config = replace(agent.config, context_char_budget=120)
        context = agent.retrieve_context("explain repository architecture and code tools")
        self.assertLessEqual(len(context), 170)
        if context:
            self.assertIn("context trimmed", context)

    def test_agent_streaming_visual_has_plan_metadata(self):
        """Verify streaming visual fast path includes planner metadata."""

        events = list(Agent().stream_with_events("show graph of microservice architecture"))
        done = events[-1]
        self.assertEqual(done["type"], "done")
        self.assertEqual(done["metadata"]["tools_used"], ["rich_output_template_tool"])
        self.assertEqual(done["metadata"]["plan"]["intent"], "visualize")
        self.assertTrue(done["metadata"]["plan"]["ambiguous"])


if __name__ == "__main__":
    unittest.main()
