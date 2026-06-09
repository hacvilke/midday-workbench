from __future__ import annotations

from dataclasses import dataclass

from .context_window import ContextWindow
from .oss_tools import OssToolRegistry, ToolResult
from .router import IntentRoute, IntentRouter
from .session import load_session_state, save_session_state


@dataclass(frozen=True)
class ReactStep:
    """Represents one Thought -> Action -> Observation step.

    Args:
        thought: Why the action was chosen.
        action: Tool name.
        observation: Tool result summary.

    Returns:
        Immutable ReAct step metadata.
    """

    thought: str
    action: str
    observation: str


class ReactPlanner:
    """Small ReAct-style planner for deterministic OSS tool use.

    The model still writes the final answer, but this planner gives the agent a visible
    Thought -> Action -> Observation trace over local OSS tools before that answer.
    """

    def __init__(self, registry: OssToolRegistry):
        self.registry = registry
        self.router = IntentRouter()

    def run(self, prompt: str) -> tuple[list[ReactStep], list[ToolResult]]:
        """Execute an intent-routed ReAct tool chain.

        Args:
            prompt: User prompt.

        Returns:
            Tuple of ReAct steps and tool results.
        """

        route = self.router.classify(prompt)
        selected = [self.registry.get_tool(name) for name in route.tools]
        context_window = load_session_state()
        steps: list[ReactStep] = []
        results: list[ToolResult] = []
        for tool in selected:
            thought = f"Intent {route.intent}: {route.rationale}"
            chained_prompt = prompt if route.intent == "visualize" else context_window.chained_query(prompt)
            result = self.registry.run_tool(tool, chained_prompt)
            context_window.add_tool_result(result)
            observation = result.summary
            steps.append(ReactStep(thought, tool.name, observation))
            results.append(result)
        save_session_state(context_window)
        return steps, results


def format_react_trace(steps: list[ReactStep]) -> str:
    """Format ReAct steps for the model context.

    Args:
        steps: ReAct steps.

    Returns:
        Markdown-ish trace text.
    """

    if not steps:
        return ""
    blocks = []
    for index, step in enumerate(steps, start=1):
        blocks.append(
            f"Step {index}\nThought: {step.thought}\nAction: {step.action}\nObservation: {step.observation}"
        )
    return "\n\n".join(blocks)
