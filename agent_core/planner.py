"""Structured planning artifacts for Midday Workbench agent runs."""
from __future__ import annotations

from dataclasses import dataclass

from .delegation import DelegationPlanner
from .router import IntentRoute, IntentRouter
from .skill_registry import best_skill_for_message


@dataclass(frozen=True)
class PlanStep:
    """Single planned action before execution.

    Args:
        role: Responsible internal role.
        action: Planned action.
        expected: Expected outcome or artifact.

    Returns:
        Immutable plan step.
    """

    role: str
    action: str
    expected: str


@dataclass(frozen=True)
class AgentPlan:
    """Structured manager/planner output for a user request.

    Args:
        intent: Classified intent.
        tool: Selected tool, if any.
        reason: Routing rationale.
        steps: Ordered planning steps.
        verification: Verification action the agent should perform.
        stop_condition: Concrete condition that completes the turn.
        delegations: Role assignments for future parallel/sub-agent execution.
        concurrency: Safe serial and parallel-candidate ordering metadata.
        confidence: Selected route confidence from 0.0 to 1.0.
        ambiguous: Whether multiple route candidates matched this prompt.
        alternatives: Other matching route candidates for audit/ambiguity review.
        specialist: Selected bounded specialist profile for this turn.

    Returns:
        Immutable JSON-serializable plan metadata through asdict().
    """

    intent: str
    tool: str | None
    reason: str
    steps: list[PlanStep]
    verification: str
    stop_condition: str
    delegations: list[dict[str, object]]
    concurrency: dict[str, object]
    confidence: float
    ambiguous: bool
    alternatives: list[dict[str, object]]
    specialist: dict[str, object]


class AgentPlanner:
    """Build deterministic manager/planner artifacts from router decisions."""

    def __init__(self):
        self.router = IntentRouter()
        self.delegation = DelegationPlanner()

    def build_plan(self, prompt: str) -> AgentPlan:
        """Create a plan for a prompt before tool execution.

        Args:
            prompt: User prompt.

        Returns:
            AgentPlan describing intent, tool, execution steps, and verification.
        """

        route = self.router.classify(prompt)
        tool = route.tools[0] if route.tools else None
        specialist = best_skill_for_message(route.intent, prompt)
        return AgentPlan(
            intent=route.intent,
            tool=tool,
            reason=route.rationale,
            steps=self._steps_for_route(route, tool),
            verification=self._verification_for_route(route, tool),
            stop_condition=self._stop_condition_for_route(route),
            delegations=self.delegation.as_dicts(prompt),
            concurrency=self.delegation.concurrency_plan(prompt),
            confidence=route.confidence,
            ambiguous=len(route.alternatives or []) > 1,
            alternatives=route.alternatives or [],
            specialist={
                "identifier": specialist.identifier,
                "role": specialist.role,
                "permissions": list(specialist.permissions),
                "system_focus": specialist.system_focus,
                "success_criteria": specialist.success_criteria,
            },
        )

    def _steps_for_route(self, route: IntentRoute, tool: str | None) -> list[PlanStep]:
        """Map route metadata to role-based plan steps."""

        steps = [
            PlanStep("manager", f"classify request as {route.intent}", route.rationale),
        ]
        if tool:
            steps.append(PlanStep("planner", f"select specialist and exactly one tool: {tool}", "one focused tool call"))
            steps.append(PlanStep("executor", f"run {tool}", "structured tool result"))
            steps.append(PlanStep("verifier", "verify result shape and usefulness", "pass/fail verifier report"))
        else:
            steps.append(PlanStep("responder", "answer directly", "short no-tool response"))
        return steps

    def _verification_for_route(self, route: IntentRoute, tool: str | None) -> str:
        """Return the verification method for a route."""

        if route.intent == "visualize":
            return "confirm exactly one valid Mermaid block and no provider call"
        if tool:
            return "confirm non-empty structured tool output and record verifier report"
        return "confirm no tool/provider was required"

    def _stop_condition_for_route(self, route: IntentRoute) -> str:
        """Return a concrete stop condition for the current turn."""

        if route.intent == "visualize":
            return "return renderable visual output"
        if route.intent == "plain_chat":
            return "return concise plain text"
        return "return answer grounded in selected tool result and verifier status"
