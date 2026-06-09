from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class IntentRoute:
    """Represents the classified user intent and the ordered tool chain.

    Args:
        intent: The high-level intent category.
        tools: The ordered tool names to execute.
        confidence: A deterministic confidence score from 0.0 to 1.0.
        rationale: Short explanation for audit/debug UI.

    Returns:
        Immutable route metadata for a ReAct run.
    """

    intent: str
    tools: list[str]
    confidence: float
    rationale: str


class IntentRouter:
    """Classifies user messages into explicit tool chains.

    Args:
        None.

    Returns:
        IntentRoute objects through classify().
    """

    VISUAL_WORDS = {
        "show",
        "draw",
        "visualize",
        "diagram",
        "mermaid",
        "dashboard",
        "kanban",
        "mind map",
        "repo map",
        "repository map",
        "chart",
    }
    GRAPH_ALGORITHM_WORDS = {
        "pagerank",
        "page rank",
        "bfs",
        "breadth first",
        "centrality",
        "traversal",
        "shortest path",
        "community",
        "ranking algorithm",
        "graph algorithm",
        "dependency ranking",
    }
    GREETING_WORDS = {
        "hi",
        "hello",
        "hey",
        "help",
        "thanks",
        "thank you",
        "what are you",
        "who are you",
    }

    def classify(self, message: str) -> IntentRoute:
        """Map a user message to an intent category and tool chain.

        Args:
            message: Raw user message.

        Returns:
            IntentRoute containing category, ordered tools, confidence, and rationale.
        """

        text = normalize(message)
        if is_greeting_or_identity(text):
            return IntentRoute("plain_chat", [], 0.96, "Greeting, help, thanks, or identity question needs no tool.")
        if is_graph_algorithm_request(text):
            return IntentRoute("analyze_graph", ["cugraph_graph_tool"], 0.9, "Graph algorithm or centrality request.")
        if is_visual_request(text):
            return IntentRoute(
                "visualize",
                ["rich_output_template_tool"],
                0.92,
                "Visual graph/chart/map request should render Markdown/Mermaid instead of invoking graph algorithms.",
            )
        if contains_any(text, ("purchase order", "invoice", "erp", "frappe", "doctype", "payroll", "stock")):
            return IntentRoute("business_workflow", ["erpnext_business_tool"], 0.86, "ERP/business workflow request.")
        if contains_any(text, ("julia", "compiler", "runtime", "juliasyntax", "package")):
            return IntentRoute("code_analysis", ["julia_language_tool"], 0.82, "Julia language/runtime request.")
        if contains_any(text, ("edit", "fix", "refactor", "commit", "diff", "patch", "write code")):
            return IntentRoute("code_edit", ["aider_git_native_tool"], 0.88, "Git-native code editing request.")
        if contains_any(text, ("pack", "summarize repo", "repo context")):
            return IntentRoute("repo_context", ["repomix_context_pack_tool"], 0.86, "Local repository packing/context request.")
        if contains_any(text, ("github.com", "ingest repo")):
            return IntentRoute("repo_context", ["gitingest_remote_context_tool"], 0.84, "Remote repository ingestion request.")
        if contains_any(text, ("last 30 days", "recent trend", "what happened", "latest news")):
            return IntentRoute("research", ["last30days_research_tool"], 0.82, "Recent research/news request.")
        if contains_any(text, ("architecture", "scale", "api design", "caching", "queues", "microservice")):
            return IntentRoute("system_design", ["system_design_tool"], 0.8, "Architecture/system design request.")
        return IntentRoute("general", [], 0.5, "No specialized OSS tool required.")


def normalize(message: str) -> str:
    """Normalize user text for deterministic intent checks.

    Args:
        message: Raw text.

    Returns:
        Lowercase text with compact whitespace.
    """

    return re.sub(r"\s+", " ", message.strip().lower())


def contains_any(text: str, needles: tuple[str, ...]) -> bool:
    """Check whether normalized text contains any phrase.

    Args:
        text: Normalized text.
        needles: Phrases to search for.

    Returns:
        True when at least one phrase is present.
    """

    return any(needle in text for needle in needles)


def is_visual_request(text: str) -> bool:
    """Determine whether the user wants a rendered visual artifact.

    Args:
        text: Normalized text.

    Returns:
        True for visual/report/chart/diagram/map requests.
    """

    visual_patterns = (
        "show a graph",
        "show me a graph",
        "show graph",
        "make a graph",
        "draw a graph",
        "show diagram",
        "make diagram",
        "draw diagram",
        "show chart",
        "make chart",
        "draw chart",
        "show map",
        "make map",
        "draw map",
    )
    return contains_any(text, visual_patterns) or any(word in text for word in ("diagram", "mermaid", "dashboard", "kanban", "mind map", "repo map", "repository map"))


def is_graph_algorithm_request(text: str) -> bool:
    """Determine whether the user wants graph analytics rather than a visual.

    Args:
        text: Normalized text.

    Returns:
        True for centrality, BFS, PageRank, traversal, and graph algorithm requests.
    """

    return "cugraph" in text or any(word in text for word in IntentRouter.GRAPH_ALGORITHM_WORDS)


def is_greeting_or_identity(text: str) -> bool:
    """Determine whether a prompt should be answered without tools.

    Args:
        text: Normalized text.

    Returns:
        True for short greetings, thanks, help, and identity questions.
    """

    if text in IntentRouter.GREETING_WORDS:
        return True
    return text in {"who are you?", "what are you?", "can you help?", "help me"}
