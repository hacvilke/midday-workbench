"""ReAct loop: Planner + one-tool-per-turn execution + self-verification."""
from __future__ import annotations

from dataclasses import dataclass

from .context_window import ContextWindow
from .oss_tools import OssToolRegistry, ToolResult
from .router import IntentRoute, IntentRouter
from .session import load_session_state, save_session_state
from .verifier import ReActVerifier, VerifierReport


@dataclass(frozen=True)
class ReactStep:
    """Represents one Thought -> Action -> Observation -> Verify step.

    Args:
        thought: Planning rationale for the action.
        action: Tool name that was executed.
        observation: Summary of the tool result (may include VERIFY status).

    Returns:
        Immutable ReAct step metadata.
    """

    thought: str
    action: str
    observation: str


class ReactPlanner:
    """ReAct-style planner: one tool per turn, with post-step self-verification.

    Roles:
    - **Manager** (IntentRouter): classifies intent and selects the right tool chain.
    - **Planner** (ReactPlanner.run): builds the thought for each step and sequences execution.
    - **Verifier** (ReActVerifier): inspects each result before moving to the next step.

    The model still writes the final answer, but this planner gives it a visible
    Thought → Action → Observation → Verify trace over local OSS tools first.
    """

    def __init__(self, registry: OssToolRegistry):
        self.registry = registry
        self.router = IntentRouter()
        self.verifier = ReActVerifier()

    def run(
        self, prompt: str
    ) -> tuple[list[ReactStep], list[ToolResult], list[VerifierReport]]:
        """Execute an intent-routed ReAct tool chain with self-verification.

        Args:
            prompt: User prompt.

        Returns:
            Tuple of (ReAct steps, tool results, verifier reports). One entry per
            tool invoked. Empty lists when no tool is needed (greeting / plain chat).
        """
        route = self.router.classify(prompt)
        selected = [self.registry.get_tool(name) for name in route.tools]
        context_window = load_session_state()

        steps: list[ReactStep] = []
        results: list[ToolResult] = []
        reports: list[VerifierReport] = []

        for tool in selected:
            # PLAN: build a rich thought from route metadata
            thought = (
                f"[{route.intent.upper()}] {route.rationale} "
                f"→ selecting {tool.name} (confidence {route.confidence:.2f})"
            )

            # One tool per turn
            chained_prompt = (
                prompt
                if route.intent == "visualize"
                else context_window.chained_query(prompt)
            )
            result = self.registry.run_tool(tool, chained_prompt)
            context_window.add_tool_result(result)

            # VERIFY: self-check the result before recording the step
            report = self.verifier.verify_tool_result(len(steps), tool.name, result)
            reports.append(report)

            verify_tag = "✓ VERIFY:OK" if report.passed else f"✗ VERIFY:{'; '.join(report.issues)}"
            observation = f"{result.summary} [{verify_tag}]"

            steps.append(ReactStep(thought, tool.name, observation))
            results.append(result)

        save_session_state(context_window)
        return steps, results, reports


def format_react_trace(
    steps: list[ReactStep],
    verifier_reports: list[VerifierReport] | None = None,
) -> str:
    """Format ReAct steps as a Thought/Action/Observation/Verify trace for model context.

    Args:
        steps: ReAct steps from the planner.
        verifier_reports: Optional verifier reports aligned with each step.

    Returns:
        Markdown-style trace text.
    """
    if not steps:
        return ""
    blocks = []
    for index, step in enumerate(steps, start=1):
        verify_line = ""
        if verifier_reports and index - 1 < len(verifier_reports):
            report = verifier_reports[index - 1]
            status = "PASS" if report.passed else f"FAIL — {'; '.join(report.issues)}"
            verify_line = f"\nVerify: {status}"
        blocks.append(
            f"Step {index}\n"
            f"Thought: {step.thought}\n"
            f"Action: {step.action}\n"
            f"Observation: {step.observation}"
            f"{verify_line}"
        )
    return "\n\n".join(blocks)
