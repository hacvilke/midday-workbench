"""Midday Workbench main agent with streaming and file-editing support."""
from __future__ import annotations

import re
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Iterator

from .config import get_config
from .execution_policy import decide
from .file_editor import FileEditorTool, extract_code_block
from .indexer import search
from .oss_tools import OssToolRegistry
from .planner import AgentPlanner
from .prompt_harness import build_system_prompt
from .providers import Message, ProviderError, build_provider
from .react_loop import ReactPlanner, format_react_trace
from .rich_output_template_tool.render import extract_mermaid_blocks, is_valid_mermaid
from .router import IntentRouter
from .tool_schemas import schema_markdown
from .tools import ToolBox
from .turn_policy import classify_turn_policy
from .verifier import ReActVerifier


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
    verifier_reports: list[dict] = field(default_factory=list)
    plan: dict | None = None
    file_writes: list[dict[str, object]] = field(default_factory=list)
    usage: dict[str, int] = field(default_factory=dict)
    completion_evidence: dict[str, object] = field(default_factory=dict)


class Agent:
    def __init__(self):
        self.config = get_config()
        self.provider = build_provider(self.config)
        self.tools = ToolBox(self.config)
        self.oss_tools = OssToolRegistry(self.config)
        self.react = ReactPlanner(self.oss_tools)
        self.router = IntentRouter()
        self.planner = AgentPlanner()
        self.editor = FileEditorTool(self.config.workspace_root)
        self.verifier = ReActVerifier()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self, prompt: str, history: list[dict[str, object]] | None = None) -> str:
        return self.run_with_metadata(prompt, history=history).answer

    def run_with_metadata(self, prompt: str, history: list[dict[str, object]] | None = None) -> AgentRun:
        """Run the agent and return a complete AgentRun (non-streaming).

        Args:
            prompt: User message.
            history: Prior conversation messages.

        Returns:
            AgentRun with answer and full run metadata.
        """
        started = time.perf_counter()
        run_id = uuid.uuid4().hex[:12]
        plan = asdict(self.planner.build_plan(prompt))

        # Fast path: greetings / identity
        direct = self.direct_answer(prompt)
        if direct is not None:
            return AgentRun(
                run_id=run_id,
                answer=direct,
                tools_used=[],
                react_steps=[],
                context_attached=False,
                memory_items=len(history or []),
                provider="local",
                duration_ms=int((time.perf_counter() - started) * 1000),
                fallback_used=False,
                error=None,
                provider_attempts=[{"provider": "local", "ok": True, "duration_ms": 0, "error": None}],
                verifier_reports=[],
                plan=plan,
                usage=self._usage(prompt, direct, history=history or []),
                completion_evidence=self._completion_evidence([], [], [], direct=True),
            )

        route = self.router.classify(prompt)

        # Fast path: visual diagram — Mermaid only, no provider call
        if route.intent == "visualize":
            react_steps, tool_results, v_reports = self.react.run(prompt)
            visual = self.visual_tool_answer(tool_results)
            if visual is not None:
                return AgentRun(
                    run_id=run_id,
                    answer=visual,
                    tools_used=[r.name for r in tool_results],
                    react_steps=[asdict(s) for s in react_steps],
                    context_attached=False,
                    memory_items=len(history or []),
                    provider="local",
                    duration_ms=int((time.perf_counter() - started) * 1000),
                    fallback_used=False,
                    error=None,
                    provider_attempts=[{"provider": "local", "ok": True, "duration_ms": 0, "error": None}],
                    verifier_reports=[asdict(r) for r in v_reports],
                    plan=plan,
                    usage=self._usage(prompt, visual, tool_results=tool_results, history=history or []),
                    completion_evidence=self._completion_evidence(tool_results, v_reports, [], direct=True),
                )

        # General path
        context = self.retrieve_context(prompt)
        react_steps, tool_results, v_reports = self.react.run(prompt)

        visual = self.visual_tool_answer(tool_results)
        if visual is not None:
            return AgentRun(
                run_id=run_id,
                answer=visual,
                tools_used=[r.name for r in tool_results],
                react_steps=[asdict(s) for s in react_steps],
                context_attached=bool(context),
                memory_items=len(history or []),
                provider="local",
                duration_ms=int((time.perf_counter() - started) * 1000),
                fallback_used=False,
                error=None,
                provider_attempts=[{"provider": "local", "ok": True, "duration_ms": 0, "error": None}],
                verifier_reports=[asdict(r) for r in v_reports],
                plan=plan,
                usage=self._usage(prompt, visual, context=context, tool_results=tool_results, history=history or []),
                completion_evidence=self._completion_evidence(tool_results, v_reports, [], direct=True),
            )

        messages = self._build_messages(prompt, context, react_steps, tool_results, v_reports, history or [])

        if hasattr(self.provider, "complete_with_metadata"):
            result = self.provider.complete_with_metadata(messages)
            answer = result.answer
            provider_name = result.provider
            fallback_used = result.fallback_used
            error = result.error
            provider_attempts = [asdict(a) for a in result.attempts]
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
                oss_block = self.format_tool_results(tool_results)
                answer = f"Provider failed: {exc}\n\nFallback:\n{oss_block or context}"

        v_reports = [*v_reports, self.verifier.verify_provider_attempts(provider_attempts)]
        answer, file_writes = self._maybe_write_file_with_metadata(prompt, tool_results, answer)

        return AgentRun(
            run_id=run_id,
            answer=answer,
            tools_used=[r.name for r in tool_results],
            react_steps=[asdict(s) for s in react_steps],
            context_attached=bool(context),
            memory_items=len(history or []),
            provider=provider_name,
            duration_ms=int((time.perf_counter() - started) * 1000),
            fallback_used=fallback_used,
            error=error,
            provider_attempts=provider_attempts,
            verifier_reports=[asdict(r) for r in v_reports],
            plan=plan,
            file_writes=file_writes,
            usage=self._usage(prompt, answer, context=context, tool_results=tool_results, history=history or []),
            completion_evidence=self._completion_evidence(tool_results, v_reports, file_writes),
        )

    def stream_with_events(
        self,
        prompt: str,
        history: list[dict[str, object]] | None = None,
    ) -> Iterator[dict]:
        """Stream agent response as SSE-style event dicts.

        Yields event dicts with keys:
        - {"type": "tool", "tool": name, "summary": text}
        - {"type": "token", "token": text}
        - {"type": "file_written", "path": path}
        - {"type": "done", "metadata": {...}}
        - {"type": "error", "error": text}

        Args:
            prompt: User message.
            history: Prior conversation messages.

        Yields:
            Event dicts for streaming consumption.
        """
        started = time.perf_counter()
        run_id = uuid.uuid4().hex[:12]
        plan = asdict(self.planner.build_plan(prompt))

        # Fast path: greetings
        direct = self.direct_answer(prompt)
        if direct is not None:
            for word in direct.split(" "):
                yield {"type": "token", "token": word + " "}
            yield {
                "type": "done",
                "metadata": self._make_stream_metadata(
                    run_id, direct, [], [], False, False, None,
                    [{"provider": "local", "ok": True, "duration_ms": 0, "error": None}],
                    "local", started, [], plan, usage=self._usage(prompt, direct, history=history or []),
                ),
            }
            return

        route = self.router.classify(prompt)

        # Fast path: visual
        if route.intent == "visualize":
            react_steps, tool_results, v_reports = self.react.run(prompt)
            for r in tool_results:
                yield {"type": "tool", "tool": r.name, "summary": r.summary}
            visual = self.visual_tool_answer(tool_results)
            if visual is not None:
                for word in visual.split(" "):
                    yield {"type": "token", "token": word + " "}
                yield {
                    "type": "done",
                    "metadata": self._make_stream_metadata(
                        run_id, visual, [r.name for r in tool_results],
                        [asdict(s) for s in react_steps], False, False, None,
                        [{"provider": "local", "ok": True, "duration_ms": 0, "error": None}],
                        "local", started, [asdict(r) for r in v_reports], plan,
                        usage=self._usage(prompt, visual, tool_results=tool_results, history=history or []),
                    ),
                }
                return

        # General path
        context = self.retrieve_context(prompt)
        react_steps, tool_results, v_reports = self.react.run(prompt)

        for r in tool_results:
            yield {"type": "tool", "tool": r.name, "summary": r.summary}

        visual = self.visual_tool_answer(tool_results)
        if visual is not None:
            for word in visual.split(" "):
                yield {"type": "token", "token": word + " "}
            yield {
                "type": "done",
                "metadata": self._make_stream_metadata(
                    run_id, visual, [r.name for r in tool_results],
                    [asdict(s) for s in react_steps], bool(context), False, None,
                    [{"provider": "local", "ok": True, "duration_ms": 0, "error": None}],
                    "local", started, [asdict(r) for r in v_reports], plan,
                    usage=self._usage(prompt, visual, context=context, tool_results=tool_results, history=history or []),
                ),
            }
            return

        messages = self._build_messages(prompt, context, react_steps, tool_results, v_reports, history or [])

        full_answer = ""
        provider_name = "offline"
        fallback_used = False
        error = None
        provider_attempts = []

        if hasattr(self.provider, "stream_with_metadata"):
            for event in self.provider.stream_with_metadata(messages):
                if event.get("type") == "token":
                    token = str(event.get("token", ""))
                    full_answer += token
                    yield {"type": "token", "token": token}
                elif event.get("type") == "metadata":
                    provider_name = str(event.get("provider", "offline"))
                    fallback_used = bool(event.get("fallback_used"))
                    error = event.get("error")
                    provider_attempts = [asdict(attempt) for attempt in event.get("attempts", [])]
        else:
            try:
                t0 = time.perf_counter()
                for token in self.provider.stream(messages):
                    full_answer += token
                    yield {"type": "token", "token": token}
                latency = int((time.perf_counter() - t0) * 1000)
                pname = getattr(self.provider, "name", self.config.provider)
                provider_name = pname
                provider_attempts = [{"provider": pname, "ok": True, "duration_ms": latency, "error": None}]
            except ProviderError as exc:
                error = str(exc)
                fallback_used = True
                provider_name = "offline"
                provider_attempts = [{"provider": self.config.provider, "ok": False, "duration_ms": 0, "error": error}]
                oss_block = self.format_tool_results(tool_results)
                full_answer = f"Provider failed: {exc}\n\nFallback:\n{oss_block or context}"
                for word in full_answer.split(" "):
                    yield {"type": "token", "token": word + " "}

        v_reports = [*v_reports, self.verifier.verify_provider_attempts(provider_attempts)]

        # Auto file-write post-processing
        write_result, file_writes = self._maybe_write_file_with_metadata(prompt, tool_results, full_answer)
        if write_result != full_answer:
            suffix = write_result[len(full_answer):]
            full_answer = write_result
            yield {"type": "token", "token": suffix}
            for write in file_writes:
                yield {"type": "file_written", "path": write.get("path"), "write": write}

        yield {
            "type": "done",
            "metadata": self._make_stream_metadata(
                run_id, full_answer, [r.name for r in tool_results],
                [asdict(s) for s in react_steps], bool(context), fallback_used, error,
                provider_attempts, provider_name, started, [asdict(r) for r in v_reports], plan, file_writes,
                usage=self._usage(prompt, full_answer, context=context, tool_results=tool_results, history=history or []),
            ),
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def should_retrieve(self, prompt: str) -> bool:
        normalized = re.sub(r"\s+", " ", prompt.strip().lower())
        if not normalized or normalized in CASUAL_PATTERNS:
            return False
        if "trading chart" in normalized and not any(h in normalized for h in ACCOUNTING_HINTS):
            return False
        if len(normalized.split()) <= 3 and not any(h in normalized for h in REPO_CONTEXT_HINTS):
            return False
        return any(h in normalized for h in REPO_CONTEXT_HINTS) or len(normalized.split()) >= 7

    def retrieve_context(self, prompt: str) -> str:
        if not self.should_retrieve(prompt):
            return ""
        results = search(self.config.index_path, prompt, limit=10)
        if not results:
            return ""
        context = "\n\n".join(f"[{r['repo']}] {r['path']}\n{r['snippet']}" for r in results)
        budget = max(0, int(self.config.context_char_budget or 0))
        if budget and len(context) > budget:
            return context[:budget].rstrip() + "\n\n[context trimmed by AGENT_CONTEXT_CHAR_BUDGET]"
        return context

    def direct_answer(self, prompt: str) -> str | None:
        route = self.router.classify(prompt)
        if route.intent != "plain_chat":
            return None
        normalized = re.sub(r"\s+", " ", prompt.strip().lower())
        policy = classify_turn_policy(prompt)
        if policy.block_tools and not any(word in normalized for word in ("hi", "hello", "thanks", "thank you")):
            return "I will answer directly without tools for this turn. Tell me the specific question or task you want handled in guide-only mode."
        if "who are you" in normalized or "what are you" in normalized or "what can you do" in normalized or "help" in normalized:
            return (
                "I am Midday Workbench — a local-first engineering agent. "
                "I use OSS tools, web search, and file editing when needed, "
                "verify each result, and keep everything on-device."
            )
        if "thank" in normalized:
            return "You are welcome. I am ready to keep building."
        return "Hi. I am Midday Workbench, ready to help."

    def visual_tool_answer(self, tool_results) -> str | None:
        if len(tool_results) != 1 or tool_results[0].name != "rich_output_template_tool":
            return None
        blocks = [b for b in extract_mermaid_blocks(tool_results[0].content) if is_valid_mermaid(b)]
        if not blocks:
            return None
        return f"```mermaid\n{blocks[0]}\n```"

    def format_tool_results(self, tool_results) -> str:
        return "\n\n".join(
            f"## {r.name}\n{r.summary}\n{r.content}" for r in tool_results
        )

    def format_history(self, history: list[dict[str, object]]) -> str:
        safe = []
        for item in history[-8:]:
            role = str(item.get("role", "unknown"))
            content = str(item.get("content", ""))[:1200]
            label = "condensed_session_memory" if role == "summary" else role
            safe.append(f"{label}: {content}")
        return "\n".join(safe)

    def _build_messages(self, prompt, context, react_steps, tool_results, v_reports, history) -> list[Message]:
        tool_overview = self.tools.workspace_map() if context else ""
        oss_block = self.format_tool_results(tool_results)
        trace = format_react_trace(react_steps, v_reports)
        context_block = (
            f"\n\nWorkspace map:\n{tool_overview}\n\nRetrieved local OSS context:\n{context}"
            if context
            else "\n\nNo local repository context was attached — request does not need it."
        )
        if trace:
            context_block += f"\n\nReAct tool trace:\n{trace}"
        if oss_block:
            context_block += f"\n\nActive OSS tool results:\n{oss_block}"
        else:
            context_block += f"\n\nAvailable OSS tool schemas:\n{schema_markdown()}"
        history_block = self.format_history(history)
        if history_block:
            context_block += f"\n\nRecent conversation memory:\n{history_block}"
        return [
            Message("system", build_system_prompt(self.config)),
            Message("user", f"User request:\n{prompt}{context_block}"),
        ]

    def _maybe_write_file(self, prompt: str, tool_results, answer: str) -> str:
        """Auto-write a file if file_edit_tool was used and model produced a code block."""
        return self._maybe_write_file_with_metadata(prompt, tool_results, answer)[0]

    def _maybe_write_file_with_metadata(self, prompt: str, tool_results, answer: str) -> tuple[str, list[dict[str, object]]]:
        """Auto-write a file and return structured audit metadata when applied."""

        if "file_edit_tool" not in [r.name for r in tool_results]:
            return answer, []
        policy = decide("write_file")
        if policy.requires_confirmation and "confirmed write" not in prompt.lower():
            return (
                answer
                + f"\n\n> File write prepared but not applied: {policy.reason}. Say `confirmed write` with the target file path to apply it.",
                [],
            )
        filename = self.editor.extract_filename_from_prompt(prompt)
        if not filename:
            return answer, []
        code = extract_code_block(answer)
        if not code:
            return answer, []
        try:
            result = self.editor.write_file_with_metadata(filename, code)
            write = result.to_dict()
            return answer + f"\n\n**{result.message}**", [write]
        except (ValueError, OSError) as exc:
            return answer + f"\n\n> File write failed: {exc}", []

    def _usage(
        self,
        prompt: str,
        answer: str,
        context: str = "",
        tool_results=None,
        history: list[dict[str, object]] | None = None,
    ) -> dict[str, int]:
        """Return lightweight character-count telemetry for run observability."""

        tool_results = tool_results or []
        history = history or []
        tool_chars = sum(len(str(getattr(result, "content", ""))) for result in tool_results)
        history_chars = sum(len(str(item.get("content", ""))) for item in history)
        return {
            "prompt_chars": len(prompt),
            "answer_chars": len(answer),
            "context_chars": len(context),
            "tool_result_chars": tool_chars,
            "history_items": len(history),
            "history_chars": history_chars,
        }

    def _make_stream_metadata(
        self, run_id, answer, tools_used, react_steps,
        context_attached, fallback_used, error,
        provider_attempts, provider_name, started, verifier_reports, plan,
        file_writes: list[dict[str, object]] | None = None,
        usage: dict[str, int] | None = None,
    ) -> dict:
        return {
            "run_id": run_id,
            "answer": answer,
            "tools_used": tools_used,
            "react_steps": react_steps,
            "context_attached": context_attached,
            "memory_items": 0,
            "provider": provider_name,
            "duration_ms": int((time.perf_counter() - started) * 1000),
            "fallback_used": fallback_used,
            "error": error,
            "provider_attempts": provider_attempts,
            "verifier_reports": verifier_reports,
            "plan": plan,
            "file_writes": file_writes or [],
            "usage": usage or self._usage("", answer),
            "completion_evidence": self._completion_evidence_from_metadata(
                tools_used, verifier_reports, file_writes or [], provider_attempts, direct=provider_name == "local"
            ),
        }

    def _completion_evidence(
        self,
        tool_results,
        verifier_reports,
        file_writes: list[dict[str, object]] | None = None,
        direct: bool = False,
    ) -> dict[str, object]:
        """Build compact evidence flags for run completion claims."""

        reports = [asdict(report) for report in verifier_reports]
        return self._completion_evidence_from_metadata(
            [result.name for result in tool_results],
            reports,
            file_writes or [],
            [],
            direct=direct,
        )

    def _completion_evidence_from_metadata(
        self,
        tools_used: list[str],
        verifier_reports: list[dict[str, object]],
        file_writes: list[dict[str, object]],
        provider_attempts: list[dict[str, object]],
        direct: bool = False,
    ) -> dict[str, object]:
        """Summarize whether a run has observable completion evidence."""

        from .quality import quality_readiness

        readiness = quality_readiness()
        failed_verifiers = [report for report in verifier_reports if not report.get("passed")]
        provider_verified = bool(direct or any(attempt.get("ok") for attempt in provider_attempts))
        tools_verified = not tools_used or (
            len([report for report in verifier_reports if report.get("action") in tools_used]) >= len(tools_used)
            and not failed_verifiers
        )
        return {
            "provider_verified": provider_verified,
            "tools_verified": tools_verified,
            "failed_verifier_count": len(failed_verifiers),
            "file_write_count": len(file_writes),
            "quality_ready": bool(readiness.get("ready")),
            "quality_missing_required": len(readiness.get("missing_required", [])),
            "quality_failed_required": len(readiness.get("failed_required", [])),
        }
