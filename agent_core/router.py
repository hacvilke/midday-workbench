"""Intent router: maps user messages to ordered tool chains."""
from __future__ import annotations

import re
from dataclasses import dataclass

from .turn_policy import classify_turn_policy


@dataclass(frozen=True)
class IntentRoute:
    """Represents the classified user intent and the ordered tool chain.

    Args:
        intent: The high-level intent category.
        tools: The ordered tool names to execute.
        confidence: A deterministic confidence score from 0.0 to 1.0.
        rationale: Short explanation for audit/debug UI.
        alternatives: Other matching route candidates for ambiguity review.

    Returns:
        Immutable route metadata for a ReAct run.
    """

    intent: str
    tools: list[str]
    confidence: float
    rationale: str
    alternatives: list[dict[str, object]] | None = None


class IntentRouter:
    """Classifies user messages into explicit tool chains."""

    VISUAL_WORDS = {
        "show", "draw", "visualize", "diagram", "mermaid", "dashboard",
        "kanban", "mind map", "repo map", "repository map", "chart",
    }
    GRAPH_ALGORITHM_WORDS = {
        "pagerank", "page rank", "bfs", "breadth first", "centrality",
        "traversal", "shortest path", "community", "ranking algorithm",
        "graph algorithm", "dependency ranking",
    }
    GREETING_WORDS = {
        "hi", "hello", "hey", "help", "thanks", "thank you",
        "what are you", "who are you",
    }

    def classify(self, message: str) -> IntentRoute:
        """Map a user message to an intent category and tool chain.

        Args:
            message: Raw user message.

        Returns:
            IntentRoute with category, ordered tools, confidence, and rationale.
        """

        text = normalize(message)
        alternatives = route_alternatives(text)
        policy = classify_turn_policy(message)
        if policy.block_tools:
            return IntentRoute("plain_chat", [], 0.97, f"{policy.reason}; tools blocked for this turn.", alternatives)
        if is_greeting_or_identity(text):
            return IntentRoute("plain_chat", [], 0.96, "Greeting, help, thanks, or identity question needs no tool.", alternatives)
        if is_graph_algorithm_request(text):
            return IntentRoute("analyze_graph", ["cugraph_graph_tool"], 0.9, "Graph algorithm or centrality request.", alternatives)
        if is_visual_request(text):
            return IntentRoute(
                "visualize",
                ["rich_output_template_tool"],
                0.92,
                "Visual graph/chart/map request: render Markdown/Mermaid.",
                alternatives,
            )
        if is_file_edit_request(text):
            return IntentRoute(
                "code_edit",
                ["file_edit_tool"],
                0.91,
                "File write, create, or edit request: read file context and let the model generate new content.",
                alternatives,
            )
        if is_command_request(text):
            return IntentRoute(
                "command_run",
                ["command_runner_tool"],
                0.9,
                "Command/test/status request: run one allowlisted sandbox command.",
                alternatives,
            )
        if is_web_search_request(text):
            return IntentRoute(
                "web_search",
                ["web_search_tool"],
                0.85,
                "Web search or look-up request: use DuckDuckGo Instant Answers.",
                alternatives,
            )
        if contains_any(text, ("purchase order", "invoice", "erp", "frappe", "doctype", "payroll", "stock")):
            return IntentRoute("business_workflow", ["erpnext_business_tool"], 0.86, "ERP/business workflow request.", alternatives)
        if contains_any(text, ("julia", "compiler", "runtime", "juliasyntax", "package")):
            return IntentRoute("code_analysis", ["julia_language_tool"], 0.82, "Julia language/runtime request.", alternatives)
        if contains_any(text, ("fix", "refactor", "commit", "diff", "patch", "write code")):
            return IntentRoute("code_edit", ["aider_git_native_tool"], 0.88, "Git-native code editing request.", alternatives)
        if contains_any(text, ("pack", "summarize repo", "repo context")):
            return IntentRoute("repo_context", ["repomix_context_pack_tool"], 0.86, "Local repository packing/context request.", alternatives)
        if contains_any(text, ("github.com", "ingest repo")):
            return IntentRoute("repo_context", ["gitingest_remote_context_tool"], 0.84, "Remote repository ingestion request.", alternatives)
        if contains_any(text, ("last 30 days", "recent trend", "what happened", "latest news")):
            return IntentRoute("research", ["last30days_research_tool"], 0.82, "Recent research/news request.", alternatives)
        if contains_any(text, ("architecture", "scale", "api design", "caching", "queues", "microservice")):
            return IntentRoute("system_design", ["system_design_tool"], 0.8, "Architecture/system design request.", alternatives)
        return IntentRoute("general", [], 0.5, "No specialized OSS tool required.", alternatives)


def normalize(message: str) -> str:
    return re.sub(r"\s+", " ", message.strip().lower())


def contains_any(text: str, needles: tuple[str, ...]) -> bool:
    return any(needle in text for needle in needles)


def is_visual_request(text: str) -> bool:
    visual_patterns = (
        "show a graph", "show me a graph", "show graph", "make a graph",
        "draw a graph", "show diagram", "make diagram", "draw diagram",
        "show chart", "make chart", "draw chart", "show map", "make map", "draw map",
    )
    return bool(re.search(r"\b(show|make|draw|plot|visualize)\b.*\b(graph|chart|diagram|map)\b", text)) or contains_any(text, visual_patterns) or any(
        word in text for word in ("diagram", "mermaid", "dashboard", "kanban", "mind map", "repo map", "repository map")
    )


def is_graph_algorithm_request(text: str) -> bool:
    return "cugraph" in text or any(word in text for word in IntentRouter.GRAPH_ALGORITHM_WORDS)


def is_greeting_or_identity(text: str) -> bool:
    if text in IntentRouter.GREETING_WORDS:
        return True
    return text in {"who are you?", "what are you?", "can you help?", "help me", "what can you do"}


def is_file_edit_request(text: str) -> bool:
    """Detect file write, create, edit, or update requests.

    Args:
        text: Normalized text.

    Returns:
        True when the user wants to read/write/create a workspace file.
    """

    explicit_patterns = (
        "write file", "create file", "edit file", "update file", "modify file",
        "make a file", "new file", "create a new file", "write to file",
        "save to file", "save as", "create a script", "write a script",
        "write a function", "write me a", "create a class", "create a module",
        "write the code for", "write code that", "make a python", "make a js",
        "create a config", "create a json", "write a test",
    )
    if contains_any(text, explicit_patterns):
        return True
    if re.search(r"\b(?:make|create|write)\s+\d+\s+files?\b", text):
        return True
    # Match "edit <filename>" or "update <filename.ext>"
    if re.search(r"(?:edit|update|modify|fix|create|write)\s+[\w./-]+\.\w+", text):
        return True
    return False


def is_web_search_request(text: str) -> bool:
    """Detect web search or look-up requests.

    Args:
        text: Normalized text.

    Returns:
        True when the user wants to search the web.
    """

    search_patterns = (
        "search for", "look up", "find online", "google", "web search",
        "search the web", "find information about", "search online",
    )
    return contains_any(text, search_patterns)


def is_command_request(text: str) -> bool:
    """Detect safe command execution requests."""

    command_patterns = (
        "run command", "execute command", "run tests", "run test",
        "run unittest", "run pytest", "run eval", "run secret scan",
        "git status", "git diff", "node --check", "compileall",
        "check frontend syntax", "run health check",
    )
    if contains_any(text, command_patterns):
        return True
    return bool(re.search(r"\b(run|execute)\b\s+`[^`]+`", text))


def route_alternatives(text: str) -> list[dict[str, object]]:
    """Return matching route candidates for audit and ambiguity display."""

    checks = (
        ("plain_chat", [], 0.96, is_greeting_or_identity(text)),
        ("visualize", ["rich_output_template_tool"], 0.92, is_visual_request(text)),
        ("code_edit", ["file_edit_tool"], 0.91, is_file_edit_request(text)),
        ("command_run", ["command_runner_tool"], 0.9, is_command_request(text)),
        ("analyze_graph", ["cugraph_graph_tool"], 0.9, is_graph_algorithm_request(text)),
        ("code_edit", ["aider_git_native_tool"], 0.88, contains_any(text, ("fix", "refactor", "commit", "diff", "patch", "write code"))),
        ("business_workflow", ["erpnext_business_tool"], 0.86, contains_any(text, ("purchase order", "invoice", "erp", "frappe", "doctype", "payroll", "stock"))),
        ("repo_context", ["repomix_context_pack_tool"], 0.86, contains_any(text, ("pack", "summarize repo", "repo context"))),
        ("web_search", ["web_search_tool"], 0.85, is_web_search_request(text)),
        ("repo_context", ["gitingest_remote_context_tool"], 0.84, contains_any(text, ("github.com", "ingest repo"))),
        ("code_analysis", ["julia_language_tool"], 0.82, contains_any(text, ("julia", "compiler", "runtime", "juliasyntax", "package"))),
        ("research", ["last30days_research_tool"], 0.82, contains_any(text, ("last 30 days", "recent trend", "what happened", "latest news"))),
        ("system_design", ["system_design_tool"], 0.8, contains_any(text, ("architecture", "scale", "api design", "caching", "queues", "microservice"))),
    )
    candidates = [
        {"intent": intent, "tools": tools, "confidence": confidence}
        for intent, tools, confidence, matched in checks
        if matched
    ]
    return sorted(candidates, key=lambda item: float(item["confidence"]), reverse=True)
