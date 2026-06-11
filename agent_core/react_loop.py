"""ReAct loop: Planner + one-tool-per-turn execution + self-verification."""
from __future__ import annotations

from dataclasses import dataclass

from .context_window import ContextWindow
from .oss_tools import OssToolRegistry, ToolResult
from .router import IntentRouter
from .session import load_session_state, save_session_state
from .verifier import ReActVerifier, VerifierReport


@dataclass(frozen=True)
class ReactStep:
    """Represents one Thought -> Action -> Observation -> Verify step.

    Args:
        thought: Planning rationale for the action.
        action: Tool name that was executed.
        observation: Summary of the tool result, including VERIFY status.

    Returns:
        Immutable ReAct step metadata.
    """

    thought: str
    action: str
    observation: str


class ReactPlanner:
    """ReAct-style planner: one tool per turn, with post-step self-verification.

    Roles:
    - Manager (IntentRouter): classifies intent and selects the right tool chain.
    - Planner (ReactPlanner.run): builds the thought for each step and sequences execution.
    - Verifier (ReActVerifier): inspects each result before moving to the next step.

    The model still writes the final answer, but this planner gives it a visible
    Thought -> Action -> Observation -> Verify trace over local OSS tools first.
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
            Tuple of (ReAct steps, tool results, verifier reports). Empty lists
            when no tool is needed, such as greeting/plain chat.
        """

        route = self.router.classify(prompt)
        selected = [self.registry.get_tool(name) for name in route.tools]
        context_window = load_session_state()

        steps: list[ReactStep] = []
        results: list[ToolResult] = []
        reports: list[VerifierReport] = []

        for tool in selected:
            thought = (
                f"[{route.intent.upper()}] {route.rationale} "
                f"-> selecting {tool.name} (confidence {route.confidence:.2f})"
            )

            chained_prompt = (
                prompt
                if route.intent in {"visualize", "command_run"}
                else context_window.chained_query(prompt)
            )
            result = self.registry.run_tool(tool, chained_prompt)
            context_window.add_tool_result(result)

            report = self.verifier.verify_tool_result(len(steps), tool.name, result)
            reports.append(report)
            recovery = self.verifier.recovery_action(tool.name, report)

            if recovery.should_retry:
                retry_prompt = f"{prompt}\n\nVerifier recovery instruction: {recovery.prompt_suffix}"
                retry_result = self.registry.run_tool(tool, retry_prompt)
                context_window.add_tool_result(retry_result)
                retry_report = self.verifier.verify_tool_result(len(steps), tool.name, retry_result)
                reports.append(retry_report)
                result = retry_result
                report = retry_report

            verify_tag = "VERIFY:OK" if report.passed else f"VERIFY:{'; '.join(report.issues)}"
            recovery_note = f" Recovery: {recovery.reason}." if recovery.should_retry else ""
            observation = f"{result.summary} [{verify_tag}]{recovery_note}"

            steps.append(ReactStep(thought, tool.name, observation))
            results.append(result)

        save_session_state(context_window)
        return steps, results, reports


def format_react_trace(
    steps: list[ReactStep],
    verifier_reports: list[VerifierReport] | None = None,
) -> str:
    """Format ReAct steps as a Thought/Action/Observation/Verify trace.

    Args:
        steps: ReAct steps from the planner.
        verifier_reports: Optional verifier reports from the run. When a retry
            occurred, every report is preserved but the trace shows the final
            report for each visible step.

    Returns:
        Markdown-style trace text.
    """

    if not steps:
        return ""
    blocks = []
    aligned_reports = align_final_verifier_reports(steps, verifier_reports or [])
    for index, step in enumerate(steps, start=1):
        verify_line = ""
        if index - 1 < len(aligned_reports):
            report = aligned_reports[index - 1]
            status = "PASS" if report.passed else f"FAIL: {'; '.join(report.issues)}"
            verify_line = f"\nVerify: {status}"
        blocks.append(
            f"Step {index}\n"
            f"Thought: {step.thought}\n"
            f"Action: {step.action}\n"
            f"Observation: {step.observation}"
            f"{verify_line}"
        )
    return "\n\n".join(blocks)


def align_final_verifier_reports(
    steps: list[ReactStep],
    verifier_reports: list[VerifierReport],
) -> list[VerifierReport]:
    """Align visible ReAct steps with their final verifier report.

    Recoverable tools can produce multiple reports for one visible step: a
    failed first attempt and a final retry. Operator traces should display the
    final state for each action while run metadata still preserves every report.
    """

    aligned: list[VerifierReport] = []
    for step in steps:
        matching = [report for report in verifier_reports if report.action == step.action]
        if matching:
            aligned.append(matching[-1])
    return aligned
