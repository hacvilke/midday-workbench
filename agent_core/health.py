"""Platform health checks for Midday Workbench."""
from __future__ import annotations

from dataclasses import asdict, dataclass
import time

from .config import get_config
from .agent import AgentRun
from .delegation import DelegationPlanner
from .oss_tools import TOOLS, OssToolRegistry
from .output_templates import TEMPLATES
from .prompt_harness import build_system_prompt, prompt_registry
from .providers import provider_diagnostics
from .react_loop import ReactPlanner
from .repo_graph import build_repo_graph
from .routing_audit import routing_audit
from .router import IntentRouter
from .session import load_session_state
from .run_log import recent_runs
from .tool_schemas import oss_tool_schemas
from .execution_policy import decide, policy_manifest
from .indexer import index_stats
from .quality import required_quality_commands
from .sandbox import ExecutionSandbox
from .secret_scan import SECRET_PATTERNS


@dataclass(frozen=True)
class HealthCheck:
    """Represents one platform health check.

    Args:
        name: Check name.
        passed: Whether the check passed.
        detail: Human-readable detail.

    Returns:
        Immutable health check object.
    """

    name: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class ToolHealth:
    """Represents one OSS tool health result.

    Args:
        tool: Tool name.
        status: ok or failed.
        latency_ms: Execution latency.
        last_ok_at: Unix timestamp when successful.
        detail: Short detail string.

    Returns:
        Immutable tool health object.
    """

    tool: str
    status: str
    latency_ms: int
    last_ok_at: int | None
    detail: str


def run_health_checks() -> list[HealthCheck]:
    """Run platform-level wiring health checks.

    Args:
        None.

    Returns:
        List of HealthCheck results.
    """

    config = get_config()
    registry = OssToolRegistry(config)
    schemas = oss_tool_schemas()
    prompt = build_system_prompt(config)
    prompts = prompt_registry()
    sandbox = ExecutionSandbox(config.workspace_root)
    stats = index_stats(config.index_path)
    providers = provider_diagnostics(config)
    quality_commands = required_quality_commands()

    checks = [
        HealthCheck("tool_count", len(TOOLS) >= 9, f"{len(TOOLS)} tools registered"),
        HealthCheck("schema_count", len(schemas) == len(TOOLS), f"{len(schemas)} schemas for {len(TOOLS)} tools"),
        HealthCheck("template_count", len(TEMPLATES) >= 10, f"{len(TEMPLATES)} rich templates registered"),
        HealthCheck("prompt_harness", "Current Environment Context" in prompt, "dynamic environment context injected"),
        HealthCheck("prompt_guardrails", "Operational Guardrails" in prompt and "Routing Audit" in prompt, "routing and sandbox guardrails injected"),
        HealthCheck("provider_diagnostics", bool(providers["providers"]) and "route" in providers, "provider route diagnostics available"),
        HealthCheck("search_index", int(stats.get("chunk_count") or 0) > 0, f"{stats.get('chunk_count', 0)} indexed chunks across {stats.get('repo_count', 0)} repos"),
        HealthCheck("sub_agent_prompts", {"coordinator", "read_only_research", "implementation"}.issubset(prompts), "sub-agent templates available"),
        HealthCheck(
            "agent_run_contract",
            set(AgentRun.__dataclass_fields__) == {
                "run_id",
                "answer",
                "tools_used",
                "react_steps",
                "context_attached",
                "memory_items",
                "provider",
                "duration_ms",
                "fallback_used",
                "error",
                "provider_attempts",
                "verifier_reports",
                "plan",
                "file_writes",
                "usage",
            },
            "AgentRun metadata contract available",
        ),
        HealthCheck(
            "delegation_contract",
            bool(DelegationPlanner().as_dicts("fix code")) and "parallel_candidate" in DelegationPlanner().manifest()["modes"],
            "manager/executor/verifier delegation manifest is available",
        ),
        HealthCheck(
            "direct_tool_execution",
            registry.run_tool_by_name("rich_output_template_tool", "dashboard").name == "rich_output_template_tool",
            "direct tool execution by name works",
        ),
        HealthCheck(
            "repo_graph_builder",
            len(build_repo_graph(config.workspace_root).nodes) > 0,
            "repository graph builder returns nodes",
        ),
        HealthCheck(
            "intent_router_visual_graph",
            IntentRouter().classify("show me a graph").tools == ["rich_output_template_tool"],
            "visual graph requests route to renderable templates",
        ),
        HealthCheck(
            "routing_audit",
            bool(routing_audit()["passed"]),
            "routing contract probes pass",
        ),
        HealthCheck(
            "session_state_load",
            load_session_state() is not None,
            "session_state.json can be loaded or initialized",
        ),
        HealthCheck(
            "run_log_load",
            isinstance(recent_runs(limit=1), list),
            "run log can be loaded or initialized",
        ),
        HealthCheck(
            "execution_policy",
            decide("write_file").requires_confirmation and not decide("delete_file").allowed,
            "mutation and destructive action policies are enforced",
        ),
        HealthCheck(
            "policy_manifest",
            bool(policy_manifest().get("safe_actions")) and bool(policy_manifest().get("blocked_actions")),
            "execution policy manifest is available",
        ),
        HealthCheck(
            "quality_gates_allowlisted",
            all(sandbox.is_allowed(command) for command in quality_commands),
            "required quality gates can run through the sandbox",
        ),
        HealthCheck(
            "secret_scan",
            "python -m agent_core.secret_scan" in quality_commands and len(SECRET_PATTERNS) >= 2,
            "secret scan quality gate is configured",
        ),
        HealthCheck(
            "frontend_syntax_gate",
            "node --check web/app.js" in quality_commands and sandbox.is_allowed("node --check web/app.js"),
            "frontend JavaScript syntax quality gate is configured",
        ),
    ]

    probes = {
        "erpnext_tool_route": "ERPNext inventory stock valuation",
        "julia_tool_route": "Julia parser runtime performance",
        "cugraph_tool_route": "cuGraph dependency graph ranking",
        "system_design_tool_route": "system design caching architecture",
        "aider_tool_route": "Aider repository map for code agent",
        "repomix_tool_route": "Repomix context pack for repository",
        "gitingest_tool_route": "Gitingest ingest https://github.com/Aider-AI/aider",
        "last30days_tool_route": "last 30 days recent trend brief",
        "template_tool_route": "create dashboard template",
    }
    for name, query in probes.items():
        steps, results, _ = ReactPlanner(registry).run(query)
        checks.append(
            HealthCheck(
                name,
                bool(steps and results),
                f"{len(steps)} ReAct steps, tools: {', '.join(result.name for result in results) or 'none'}",
            )
        )
    return checks


def health_report(include_tools: bool = True) -> dict[str, object]:
    """Build a structured health report for API/UI consumers.

    Args:
        include_tools: Whether to run per-tool health probes.

    Returns:
        JSON-compatible health report.
    """

    checks = run_health_checks()
    providers = provider_diagnostics(get_config())
    return {
        "passed": all(check.passed for check in checks),
        "checks": [asdict(check) for check in checks],
        "provider_diagnostics": providers,
        "tools": [asdict(tool) for tool in run_tool_health_checks()] if include_tools else [],
        "tool_health_included": include_tools,
    }


def run_tool_health_checks() -> list[ToolHealth]:
    """Run lightweight direct checks against every registered OSS tool.

    Args:
        None.

    Returns:
        List of per-tool health results with latency.
    """

    config = get_config()
    registry = OssToolRegistry(config)
    now = int(time.time())
    probes = {
        "erpnext_business_tool": "inventory",
        "julia_language_tool": "parser",
        "cugraph_graph_tool": "dependency graph centrality",
        "system_design_tool": "cache architecture",
        "aider_git_native_tool": "repository map",
        "repomix_context_pack_tool": "context pack",
        "gitingest_remote_context_tool": "https://github.com/Aider-AI/aider",
        "last30days_research_tool": "recent comparison",
        "rich_output_template_tool": "dashboard mermaid",
    }
    results = []
    for tool_name, query in probes.items():
        started = time.perf_counter()
        try:
            result = registry.run_tool_by_name(tool_name, query)
            ok = bool(result.content)
            results.append(
                ToolHealth(
                    tool=tool_name,
                    status="ok" if ok else "failed",
                    latency_ms=int((time.perf_counter() - started) * 1000),
                    last_ok_at=now if ok else None,
                    detail=result.summary,
                )
            )
        except Exception as exc:
            results.append(
                ToolHealth(
                    tool=tool_name,
                    status="failed",
                    latency_ms=int((time.perf_counter() - started) * 1000),
                    last_ok_at=None,
                    detail=str(exc),
                )
            )
    return results
