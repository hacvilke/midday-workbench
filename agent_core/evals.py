from __future__ import annotations

import argparse
import uuid
from dataclasses import asdict, dataclass

from .agent import Agent
from .config import get_config
from .health import health_report
from .memory import add_message, clear_session, get_recent_messages
from .oss_tools import OssToolRegistry
from .repo_graph import build_repo_graph
from .router import IntentRouter
from .run_log import add_run, clear_runs, recent_runs


@dataclass(frozen=True)
class EvalCase:
    name: str
    passed: bool
    detail: str


def run_evals(include_provider: bool = False) -> list[EvalCase]:
    config = get_config()
    registry = OssToolRegistry(config)
    cases: list[EvalCase] = []

    health = health_report()
    cases.append(EvalCase("health_report", bool(health["passed"]), f"{len(health['checks'])} checks"))

    expected_routes = {
        "erpnext": ("ERPNext inventory valuation", "erpnext_business_tool"),
        "julia": ("Julia parser runtime performance", "julia_language_tool"),
        "cugraph": ("cuGraph dependency graph ranking", "cugraph_graph_tool"),
        "template": ("dashboard template", "rich_output_template_tool"),
    }
    for name, (query, expected) in expected_routes.items():
        results = registry.run_for_prompt(query)
        tools = [result.name for result in results]
        cases.append(EvalCase(f"route_{name}", expected in tools, ", ".join(tools)))

    direct = registry.run_tool_by_name("erpnext_business_tool", "stock valuation")
    cases.append(EvalCase("direct_tool_execution", direct.name == "erpnext_business_tool", direct.summary))

    graph = build_repo_graph(config.workspace_root)
    cases.append(EvalCase("repo_graph_builder", bool(graph.nodes and graph.mermaid.startswith("flowchart")), f"{len(graph.nodes)} nodes, {len(graph.edges)} edges"))

    graph_tool = registry.run_tool_by_name("cugraph_graph_tool", "dependency graph centrality")
    cases.append(EvalCase("repo_graph_tool", "centrality" in graph_tool.content, graph_tool.summary))

    route = IntentRouter().classify("show me a graph")
    cases.append(EvalCase("intent_visual_graph", route.tools == ["rich_output_template_tool"], f"{route.intent}: {route.tools}"))

    dry_run = Agent().run_with_metadata("hi")
    run_sid = f"eval-run-{uuid.uuid4().hex[:8]}"
    clear_runs(run_sid)
    add_run(run_sid, "hi", dry_run)
    logged = recent_runs(session_id=run_sid, limit=1)
    cases.append(EvalCase("run_log_roundtrip", bool(logged and logged[0]["run_id"] == dry_run.run_id), str(logged[:1])))
    clear_runs(run_sid)

    sid = f"eval-memory-{uuid.uuid4().hex[:8]}"
    clear_session(sid)
    add_message(sid, "user", "remember eval")
    memory = get_recent_messages(sid)
    clear_session(sid)
    cases.append(EvalCase("memory_roundtrip", len(memory) == 1 and memory[0]["content"] == "remember eval", str(memory)))

    if include_provider:
        run = Agent().run_with_metadata("hi")
        lower_answer = run.answer.lower()
        passed_hi = "provider failed" not in lower_answer and ("hello" in lower_answer or lower_answer.startswith("hi"))
        cases.append(EvalCase("provider_casual_hi", passed_hi, run.answer[:200]))
        metadata_ok = bool(run.provider) and bool(run.run_id) and run.duration_ms >= 0 and bool(run.provider_attempts)
        cases.append(EvalCase("provider_metadata", metadata_ok, f"provider={run.provider}, attempts={run.provider_attempts}, run={run.run_id}, ms={run.duration_ms}, tools={run.tools_used}"))

    return cases


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", action="store_true", help="Include live provider calls.")
    args = parser.parse_args()
    cases = run_evals(include_provider=args.provider)
    for case in cases:
        status = "PASS" if case.passed else "FAIL"
        print(f"{status} {case.name}: {case.detail}")
    if not all(case.passed for case in cases):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
