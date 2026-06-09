from __future__ import annotations

import re
import time
import uuid
from dataclasses import asdict, dataclass

from .config import get_config
from .indexer import search
from .oss_tools import OssToolRegistry
from .prompt_harness import build_system_prompt
from .providers import Message, ProviderError, build_provider
from .react_loop import ReactPlanner, format_react_trace
from .rich_output_template_tool.render import extract_mermaid_blocks, is_valid_mermaid
from .router import IntentRouter
from .tool_schemas import schema_markdown
from .tools import ToolBox


CASUAL_PATTERNS = {
    "hi", "hello", "hey", "yo", "sup", "thanks", "thank you", "ok", "okay", "cool",
}

REPO_CONTEXT_HINTS = {
    "code", "repo", "repository", "file", "function", "class", "bug", "fix", "implement",
    "erpnext", "frappe", "julia", "cugraph", "system design", "architecture", "oss",
    "aider", "gitingest", "repomix", "git", "commit", "diff", "read", "search",
}

ACCOUNTING_HINTS = {"accounting", "erp", "chart of accounts", "ledger", "debit", "credit"}


@dataclass(frozen=True)
class AgentRun:
    run_id: str
    answer: str
    tools_used: list[str]
    react_steps: list[dict[str, str]]
    context_attached: bool
    memory_items: int
    provider: str
    duration_ms: int
    fallback_used: bool
    error: str | None
    provider_attempts: list[dict[str, object]]


class Agent:
    def __init__(self):
        self.config = get_config()
        self.provider = build_provider(self.config)
        self.tools = ToolBox(self.config)
        self.oss_tools = OssToolRegistry(self.config)
        self.react = ReactPlanner(self.oss_tools)
        self.router = IntentRouter()

    def should_retrieve(self, prompt: str) -> bool:
        normalized = re.sub(r"\s+", " ", prompt.strip().lower())
        if not normalized:
            return False
        if normalized in CASUAL_PATTERNS:
            return False
        if "trading chart" in normalized and not any(hint in normalized for hint in ACCOUNTING_HINTS):
            return False
        if len(normalized.split()) <= 3 and not any(hint in normalized for hint in REPO_CONTEXT_HINTS):
            return False
        return any(hint in normalized for hint in REPO_CONTEXT_HINTS) or len(normalized.split()) >= 7

    def retrieve_context(self, prompt: str) -> str:
        if not self.should_retrieve(prompt):
            return ""
        results = search(self.config.index_path, prompt, limit=10)
        if not results:
            return ""
        lines = []
        for item in results:
            lines.append(f"[{item['repo']}] {item['path']}\n{item['snippet']}")
        return "\n\n".join(lines)

    def run(self, prompt: str, history: list[dict[str, object]] | None = None) -> str:
        return self.run_with_metadata(prompt, history=history).answer

    def run_with_metadata(self, prompt: str, history: list[dict[str, object]] | None = None) -> AgentRun:
        started = time.perf_counter()
        run_id = uuid.uuid4().hex[:12]
        direct_answer = self.direct_answer(prompt)
        if direct_answer is not None:
            return AgentRun(
                run_id=run_id,
                answer=direct_answer,
                tools_used=[],
                react_steps=[],
                context_attached=False,
                memory_items=len(history or []),
                provider="local",
                duration_ms=int((time.perf_counter() - started) * 1000),
                fallback_used=False,
                error=None,
                provider_attempts=[{"provider": "local", "ok": True, "duration_ms": 0, "error": None}],
            )
        route = self.router.classify(prompt)
        if route.intent == "visualize":
            react_steps, tool_results = self.react.run(prompt)
            visual_answer = self.visual_tool_answer(tool_results)
            if visual_answer is not None:
                return AgentRun(
                    run_id=run_id,
                    answer=visual_answer,
                    tools_used=[result.name for result in tool_results],
                    react_steps=[asdict(step) for step in react_steps],
                    context_attached=False,
                    memory_items=len(history or []),
                    provider="local",
                    duration_ms=int((time.perf_counter() - started) * 1000),
                    fallback_used=False,
                    error=None,
                    provider_attempts=[{"provider": "local", "ok": True, "duration_ms": 0, "error": None}],
                )
        context = self.retrieve_context(prompt)
        react_steps, tool_results = self.react.run(prompt)
        visual_answer = self.visual_tool_answer(tool_results)
        if visual_answer is not None:
            return AgentRun(
                run_id=run_id,
                answer=visual_answer,
                tools_used=[result.name for result in tool_results],
                react_steps=[asdict(step) for step in react_steps],
                context_attached=bool(context),
                memory_items=len(history or []),
                provider="local",
                duration_ms=int((time.perf_counter() - started) * 1000),
                fallback_used=False,
                error=None,
                provider_attempts=[{"provider": "local", "ok": True, "duration_ms": 0, "error": None}],
            )
        tool_overview = self.tools.workspace_map() if context else ""
        oss_tool_block = self.format_tool_results(tool_results)
        react_trace = format_react_trace(react_steps)
        context_block = (
            f"\n\nWorkspace map:\n{tool_overview}\n\nRetrieved local OSS context:\n{context}"
            if context
            else "\n\nNo local repository context was attached because this request does not need it."
        )
        if react_trace:
            context_block += f"\n\nReAct tool trace:\n{react_trace}"
        if oss_tool_block:
            context_block += f"\n\nActive OSS tool results:\n{oss_tool_block}"
        else:
            context_block += f"\n\nAvailable OSS tool schemas:\n{schema_markdown()}"
        history_block = self.format_history(history or [])
        if history_block:
            context_block += f"\n\nRecent conversation memory:\n{history_block}"
        messages = [
            Message("system", build_system_prompt(self.config)),
            Message(
                "user",
                f"User request:\n{prompt}{context_block}",
            ),
        ]
        if hasattr(self.provider, "complete_with_metadata"):
            provider_result = self.provider.complete_with_metadata(messages)
            answer = provider_result.answer
            provider_name = provider_result.provider
            fallback_used = provider_result.fallback_used
            error = provider_result.error
            provider_attempts = [asdict(attempt) for attempt in provider_result.attempts]
        else:
            try:
                answer = self.provider.complete(messages)
                provider_name = getattr(self.provider, "name", self.config.provider)
                fallback_used = False
                error = None
                provider_attempts = [{"provider": provider_name, "ok": True, "duration_ms": 0, "error": None}]
            except ProviderError as exc:
                provider_name = "offline"
                fallback_used = True
                error = str(exc)
                provider_attempts = [{"provider": self.config.provider, "ok": False, "duration_ms": 0, "error": error}]
                answer = (
                    f"Provider failed: {exc}\n\n"
                    "Fallback local tool/context output:\n\n"
                    f"{oss_tool_block or context}"
                )
        return AgentRun(
            run_id=run_id,
            answer=answer,
            tools_used=[result.name for result in tool_results],
            react_steps=[asdict(step) for step in react_steps],
            context_attached=bool(context),
            memory_items=len(history or []),
            provider=provider_name,
            duration_ms=int((time.perf_counter() - started) * 1000),
            fallback_used=fallback_used,
            error=error,
            provider_attempts=provider_attempts,
        )

    def direct_answer(self, prompt: str) -> str | None:
        """Return local plain-text answers for no-tool identity/greeting prompts.

        Args:
            prompt: User prompt.

        Returns:
            A plain answer for no-tool prompts, otherwise None.
        """

        route = self.router.classify(prompt)
        if route.intent != "plain_chat":
            return None
        normalized = re.sub(r"\s+", " ", prompt.strip().lower())
        if "who are you" in normalized or "what are you" in normalized or "help" in normalized:
            return "I am OSS Agent Workbench, a local-first engineering agent that can use your OSS tools when a request clearly needs them."
        if "thank" in normalized:
            return "You are welcome. I am here and ready to keep building."
        return "Hi. I am OSS Agent Workbench, ready to help with the project."

    def visual_tool_answer(self, tool_results) -> str | None:
        """Return only Mermaid for visual template requests.

        Args:
            tool_results: Tool results produced by the ReAct planner.

        Returns:
            A single Mermaid fenced block when the rich template tool is the only tool, otherwise None.
        """

        if len(tool_results) != 1 or tool_results[0].name != "rich_output_template_tool":
            return None
        blocks = [block for block in extract_mermaid_blocks(tool_results[0].content) if is_valid_mermaid(block)]
        if not blocks:
            return None
        return f"```mermaid\n{blocks[0]}\n```"

    def format_tool_results(self, tool_results) -> str:
        blocks = []
        for result in tool_results:
            blocks.append(f"## {result.name}\n{result.summary}\n{result.content}")
        return "\n\n".join(blocks)

    def format_history(self, history: list[dict[str, object]]) -> str:
        safe = []
        for item in history[-8:]:
            role = str(item.get("role", "unknown"))
            content = str(item.get("content", ""))[:1200]
            safe.append(f"{role}: {content}")
        return "\n".join(safe)
