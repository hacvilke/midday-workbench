"""Deterministic routing audits for Midday Workbench."""
from __future__ import annotations

from dataclasses import asdict, dataclass

from .router import IntentRouter


@dataclass(frozen=True)
class RoutingProbe:
    """One routing contract probe.

    Args:
        name: Stable probe identifier.
        prompt: Prompt to classify.
        expected_intent: Required intent.
        expected_tool: Required single tool, or None for direct response.
        requires_alternatives: Whether the route should expose ambiguity metadata.

    Returns:
        Immutable routing probe definition.
    """

    name: str
    prompt: str
    expected_intent: str
    expected_tool: str | None
    requires_alternatives: bool = False


@dataclass(frozen=True)
class RoutingAuditResult:
    """One routing audit result."""

    name: str
    passed: bool
    prompt: str
    intent: str
    tool: str | None
    expected_intent: str
    expected_tool: str | None
    alternatives: list[dict[str, object]]
    detail: str


PROBES = (
    RoutingProbe("greeting_fast_path", "hi", "plain_chat", None),
    RoutingProbe("visual_fast_path", "show graph of potential energy against kinetic", "visualize", "rich_output_template_tool"),
    RoutingProbe("graph_algorithm", "run pagerank centrality on the repository graph", "analyze_graph", "cugraph_graph_tool"),
    RoutingProbe("code_edit", "fix web/app.js", "code_edit", "file_edit_tool"),
    RoutingProbe("system_design", "microservice caching architecture", "system_design", "system_design_tool"),
    RoutingProbe("ambiguous_visual_design", "show graph of microservice architecture", "visualize", "rich_output_template_tool", True),
)


def routing_audit() -> dict[str, object]:
    """Run contract probes against the intent router.

    Args:
        None.

    Returns:
        JSON-compatible audit report with pass/fail results.
    """

    router = IntentRouter()
    results: list[RoutingAuditResult] = []
    for probe in PROBES:
        route = router.classify(probe.prompt)
        tool = route.tools[0] if route.tools else None
        alternatives = route.alternatives or []
        passed = (
            route.intent == probe.expected_intent
            and tool == probe.expected_tool
            and len(route.tools) <= 1
            and (not probe.requires_alternatives or len(alternatives) >= 2)
        )
        detail = "ok" if passed else _failure_detail(probe, route.intent, tool, alternatives)
        results.append(
            RoutingAuditResult(
                name=probe.name,
                passed=passed,
                prompt=probe.prompt,
                intent=route.intent,
                tool=tool,
                expected_intent=probe.expected_intent,
                expected_tool=probe.expected_tool,
                alternatives=alternatives,
                detail=detail,
            )
        )
    return {
        "passed": all(result.passed for result in results),
        "probe_count": len(results),
        "results": [asdict(result) for result in results],
    }


def _failure_detail(
    probe: RoutingProbe,
    intent: str,
    tool: str | None,
    alternatives: list[dict[str, object]],
) -> str:
    if intent != probe.expected_intent:
        return f"expected intent {probe.expected_intent}, got {intent}"
    if tool != probe.expected_tool:
        return f"expected tool {probe.expected_tool or 'direct'}, got {tool or 'direct'}"
    if probe.requires_alternatives and len(alternatives) < 2:
        return "expected at least 2 route alternatives for ambiguous prompt"
    return "route uses more than one tool"
