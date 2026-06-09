"""Deterministic delegation contracts for Midday Workbench agent roles."""
from __future__ import annotations

from dataclasses import asdict, dataclass

from .router import IntentRouter


@dataclass(frozen=True)
class DelegationAssignment:
    """One bounded role assignment for an agent turn.

    Args:
        agent_id: Stable short identifier for the internal role.
        role: Human-readable role name.
        mode: serial, parallel_candidate, or direct.
        objective: Narrow task objective.
        tools: Tool names allowed for the assignment.
        success_criteria: Observable completion condition.

    Returns:
        Immutable delegation assignment.
    """

    agent_id: str
    role: str
    mode: str
    objective: str
    tools: list[str]
    success_criteria: str


class DelegationPlanner:
    """Build manager/planner/verifier assignment manifests from a user message."""

    def __init__(self):
        self.router = IntentRouter()

    def build(self, message: str) -> list[DelegationAssignment]:
        """Return bounded assignments for the current turn.

        Args:
            message: User message.

        Returns:
            List of assignments. Parallel candidates are read-only/verifier work
            that can safely run beside the primary executor in future runtimes.
        """

        route = self.router.classify(message)
        tool = route.tools[0] if route.tools else None
        assignments = [
            DelegationAssignment(
                "manager",
                "Manager",
                "serial",
                f"classify request as {route.intent} and enforce one-tool routing",
                [],
                "route intent, confidence, and rationale are recorded",
            )
        ]
        if not tool:
            assignments.append(
                DelegationAssignment(
                    "responder",
                    "Direct Responder",
                    "direct",
                    "answer without tool execution",
                    [],
                    "plain response is concise and no tool/provider was required",
                )
            )
            return assignments

        assignments.append(
            DelegationAssignment(
                "executor",
                self._executor_role(route.intent),
                "serial",
                f"run exactly one selected tool: {tool}",
                [tool],
                "structured tool result is non-empty and attached to the run",
            )
        )
        assignments.append(
            DelegationAssignment(
                "verifier",
                "Verifier",
                "parallel_candidate",
                "check result shape, safety, and usefulness after execution",
                [],
                "verifier report records pass/fail status and any issues",
            )
        )
        if route.intent in {"code_edit", "repo_context", "general"}:
            assignments.append(
                DelegationAssignment(
                    "reviewer",
                    "Read-Only Code Reviewer",
                    "parallel_candidate",
                    "inspect relevant repository context for risks and missing validation",
                    ["repomix_context_pack_tool", "aider_git_native_tool"],
                    "review notes are bounded to relevant files and do not mutate the workspace",
                )
            )
        return assignments

    def manifest(self) -> dict[str, object]:
        """Return role metadata for control-plane consumers."""

        return {
            "roles": [
                "Manager",
                "Direct Responder",
                "Tool Executor",
                "Verifier",
                "Read-Only Code Reviewer",
            ],
            "modes": ["serial", "direct", "parallel_candidate"],
            "parallel_policy": "parallel_candidate assignments must be read-only or verifier-only until an isolated worker runtime is attached",
        }

    def as_dicts(self, message: str) -> list[dict[str, object]]:
        """Return JSON-compatible assignments for APIs and run metadata."""

        return [asdict(assignment) for assignment in self.build(message)]

    def _executor_role(self, intent: str) -> str:
        if intent == "visualize":
            return "Visual Renderer"
        if intent == "code_edit":
            return "Code Tool Executor"
        if intent == "research":
            return "Research Synthesizer"
        if intent == "system_design":
            return "Architecture Analyst"
        return "Tool Executor"
