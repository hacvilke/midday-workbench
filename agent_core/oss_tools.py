"""OSS tool registry with file editing and web search."""
from __future__ import annotations

import json
import re
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from .config import AgentConfig, PROJECT_ROOT
from .indexer import search
from .output_templates import TEMPLATES, template_manifest
from .repo_graph import build_repo_graph
from .rich_output_template_tool.render import normalize_mermaid_output
from .sandbox import ExecutionSandbox


@dataclass(frozen=True)
class ToolResult:
    name: str
    summary: str
    content: str


@dataclass(frozen=True)
class OssTool:
    name: str
    repo: str
    description: str
    triggers: tuple[str, ...]


TOOLS: tuple[OssTool, ...] = (
    OssTool(
        "erpnext_business_tool",
        "erpnext-develop",
        "Enterprise business workflows: accounting, stock, buying, selling, manufacturing, projects, Frappe doctypes.",
        ("erp", "erpnext", "frappe", "accounting", "inventory", "stock", "invoice", "supplier", "customer", "manufacturing", "buying", "selling"),
    ),
    OssTool(
        "julia_language_tool",
        "julia-master",
        "Programming-language, compiler, runtime, package, performance, parsing, and technical-computing reasoning.",
        ("julia", "compiler", "runtime", "language", "parser", "performance", "technical computing", "package", "stdlib"),
    ),
    OssTool(
        "cugraph_graph_tool",
        "cugraph-main",
        "Graph analytics, relationship ranking, dependency graphs, centrality, traversal, GPU-scale graph concepts.",
        ("graph", "cugraph", "dependency", "ranking", "centrality", "pagerank", "community", "network", "edge", "vertex"),
    ),
    OssTool(
        "system_design_tool",
        "system-design-primer-master",
        "Architecture, scale, caching, queues, reliability, API design, storage, distributed systems.",
        ("system design", "architecture", "scale", "cache", "queue", "reliability", "database", "api", "distributed", "latency"),
    ),
    OssTool(
        "aider_git_native_tool",
        "ai-agent-oss",
        "Aider-inspired Git-native coding workflow: repo maps, diffs, controlled edits, commit planning.",
        ("aider", "git", "commit", "diff", "edit", "code agent", "repository map", "repo map"),
    ),
    OssTool(
        "repomix_context_pack_tool",
        "ai-agent-oss",
        "Repomix-inspired repository packing: XML-style file boundaries, token clarity, sensitive-file filtering.",
        ("repomix", "pack repo", "repository pack", "context pack", "xml", "prompt file"),
    ),
    OssTool(
        "gitingest_remote_context_tool",
        "ai-agent-oss",
        "Gitingest-inspired URL ingestion plan for public GitHub repos and prompt-ready Markdown summaries.",
        ("gitingest", "github url", "ingest", "remote repo", "public repo"),
    ),
    OssTool(
        "last30days_research_tool",
        "last30days-skill-main",
        "Research synthesis patterns for recent-trend briefs, comparison writing, and sourced summaries.",
        ("last 30 days", "recent", "trend", "research", "brief", "summary", "compare", "comparison"),
    ),
    OssTool(
        "rich_output_template_tool",
        "ai-agent-oss",
        "Markdown and Mermaid output templates for repo maps, architecture diagrams, dependency graphs, dashboards, reports, Kanban, and sequence diagrams.",
        ("template", "dashboard", "diagram", "mermaid", "kanban", "mind map", "dependency graph", "repository map", "report", "sequence diagram", "rich output"),
    ),
    OssTool(
        "file_edit_tool",
        "local",
        "Read, write, create, and patch files in the local workspace. Reads the target file as context so the model can generate accurate new content.",
        ("write file", "create file", "edit file", "update file", "modify file", "make a file", "new file", "create a new", "write to file", "save file", "create a script", "write a script"),
    ),
    OssTool(
        "web_search_tool",
        "online",
        "Web search via DuckDuckGo Instant Answers. Returns summaries and related topics for research queries. No API key required.",
        ("search for", "look up", "find online", "google", "web search", "search the web", "find information"),
    ),
    OssTool(
        "command_runner_tool",
        "local",
        "Safe command execution through the allowlisted Midday sandbox for tests, compile checks, git status, repo search, and health probes.",
        ("run command", "run tests", "run test", "git status", "run git", "check command", "execute command", "pytest", "unittest", "compileall"),
    ),
)


class OssToolRegistry:
    def __init__(self, config: AgentConfig):
        self.config = config

    def manifest(self) -> str:
        return "\n".join(f"- {tool.name}: {tool.description}" for tool in TOOLS)

    def tool_records(self) -> list[dict[str, object]]:
        return [
            {
                "name": tool.name,
                "repo": tool.repo,
                "description": tool.description,
                "triggers": list(tool.triggers),
            }
            for tool in TOOLS
        ]

    def get_tool(self, name: str) -> OssTool:
        for tool in TOOLS:
            if tool.name == name:
                return tool
        raise KeyError(f"Unknown OSS tool: {name}")

    def select_tools(self, prompt: str) -> list[OssTool]:
        normalized = prompt.lower()
        selected = [
            tool for tool in TOOLS
            if any(trigger in normalized for trigger in tool.triggers)
        ]
        if "trading chart" in normalized and not any(word in normalized for word in ("accounting", "erp", "ledger")):
            return selected
        if not selected and len(normalized.split()) >= 7:
            selected = [TOOLS[3]]
        return selected[:4]

    def run_for_prompt(self, prompt: str) -> list[ToolResult]:
        from .router import IntentRouter
        results = []
        route = IntentRouter().classify(prompt)
        for tool_name in route.tools:
            results.append(self.run_tool_by_name(tool_name, prompt))
        return results

    def run_tool(self, tool: OssTool, prompt: str) -> ToolResult:
        if tool.name == "cugraph_graph_tool" and self._wants_repo_graph(prompt):
            return self.repo_dependency_graph_tool(prompt)
        if tool.name == "aider_git_native_tool":
            return self.repo_map_tool(prompt)
        if tool.name == "repomix_context_pack_tool":
            return self.repo_pack_tool(prompt)
        if tool.name == "gitingest_remote_context_tool":
            return self.remote_ingest_tool(prompt)
        if tool.name == "rich_output_template_tool":
            return self.output_template_tool(prompt)
        if tool.name == "file_edit_tool":
            return self.file_context_tool(prompt)
        if tool.name == "web_search_tool":
            return self.web_search_tool(prompt)
        if tool.name == "command_runner_tool":
            return self.command_runner_tool(prompt)
        return self.scoped_search_tool(tool, prompt)

    def _wants_repo_graph(self, prompt: str) -> bool:
        normalized = prompt.lower()
        return any(
            term in normalized
            for term in ("dependency graph", "repo graph", "repository graph", "centrality", "ranking", "mermaid graph")
        )

    def run_tool_by_name(self, name: str, prompt: str) -> ToolResult:
        return self.run_tool(self.get_tool(name), prompt)

    def scoped_search_tool(self, tool: OssTool, prompt: str) -> ToolResult:
        hits = search(self.config.index_path, prompt, limit=6, repo=tool.repo)
        content = json.dumps(hits, indent=2)
        return ToolResult(
            tool.name,
            f"Used {tool.repo} as an active domain tool.",
            content if hits else f"No focused hits found in {tool.repo}.",
        )

    def repo_map_tool(self, prompt: str) -> ToolResult:
        paths = self._interesting_paths(prompt, limit=80)
        tree = "\n".join(paths)
        return ToolResult(
            "aider_git_native_tool",
            "Generated an Aider-style compact repository map for code navigation.",
            tree or "No repository map entries matched.",
        )

    def repo_pack_tool(self, prompt: str) -> ToolResult:
        files = self._interesting_paths(prompt, limit=5)
        packed = []
        for relative in files:
            path = (self.config.workspace_root / relative).resolve()
            if not self._safe_to_pack(path):
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")[:3000]
            except OSError:
                continue
            escaped = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            packed.append(f'<file path="{relative}">\n{escaped}\n</file>')
        return ToolResult(
            "repomix_context_pack_tool",
            "Packed selected files with explicit XML-style file boundaries.",
            "\n\n".join(packed) or "No safe files were selected for packing.",
        )

    def remote_ingest_tool(self, prompt: str) -> ToolResult:
        urls = re.findall(r"https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", prompt)
        if urls:
            content = "\n".join(f"- Ready to ingest public repo URL: {url}" for url in urls)
        else:
            content = "No GitHub URL found. Provide a public GitHub URL to ingest as prompt-ready context."
        return ToolResult(
            "gitingest_remote_context_tool",
            "Prepared a Gitingest-style remote repository ingestion action.",
            content,
        )

    def output_template_tool(self, prompt: str) -> ToolResult:
        normalized = prompt.lower()
        if "potential energy" in normalized or "kinetic energy" in normalized:
            content = f"## Template: energy_graph\n\n{TEMPLATES['energy_graph']}"
            return ToolResult(
                "rich_output_template_tool",
                "Selected energy graph Mermaid template for potential-vs-kinetic comparison.",
                normalize_mermaid_output(content),
            )
        aliases = {
            "repository_map": ("repository map", "repo map"),
            "mermaid_architecture": ("architecture diagram", "mermaid"),
            "dependency_graph": ("dependency graph",),
            "energy_graph": ("potential energy", "kinetic energy", "energy against", "energy graph"),
            "mind_map": ("mind map", "mindmap"),
            "system_architecture": ("system architecture", "ascii architecture"),
            "dashboard": ("dashboard",),
            "collapsible": ("collapsible", "details"),
            "kanban": ("kanban",),
            "sequence": ("sequence", "sequence diagram"),
            "analysis_report": ("report", "analysis report"),
        }
        selected = []
        for name, triggers in aliases.items():
            if any(trigger in normalized for trigger in triggers):
                selected.append(name)
        if not selected:
            selected = ["mermaid_architecture"]
        content = "\n\n---\n\n".join(f"## Template: {name}\n\n{TEMPLATES[name]}" for name in selected)
        return ToolResult(
            "rich_output_template_tool",
            "Selected rich Markdown/Mermaid output template. Follow this structure closely.",
            normalize_mermaid_output(content or template_manifest()),
        )

    def repo_dependency_graph_tool(self, prompt: str) -> ToolResult:
        graph = build_repo_graph(self.config.workspace_root)
        payload = {
            "summary": {
                "nodes": len(graph.nodes),
                "edges": len(graph.edges),
                "top_centrality": graph.centrality,
            },
            "mermaid": graph.mermaid,
            "edges": [edge.__dict__ for edge in graph.edges[:40]],
        }
        return ToolResult(
            "cugraph_graph_tool",
            "Generated a workspace dependency graph using import/include relationships and lightweight centrality ranking.",
            json.dumps(payload, indent=2),
        )

    def file_context_tool(self, prompt: str) -> ToolResult:
        """Read the target file (if mentioned) to provide editing context for the model.

        Args:
            prompt: User prompt.

        Returns:
            ToolResult with existing file content or workspace listing.
        """
        from .file_editor import FileEditorTool
        editor = FileEditorTool(self.config.workspace_root)
        filename = editor.extract_filename_from_prompt(prompt)
        if not filename:
            files = editor.list_files("**/*.py") + editor.list_files("**/*.js")
            sample = files[:24]
            return ToolResult(
                "file_edit_tool",
                "No specific file mentioned — providing workspace listing as context.",
                "Workspace files:\n" + "\n".join(sample) if sample else "No files found.",
            )
        try:
            content = editor.read_file(filename)
            return ToolResult(
                "file_edit_tool",
                f"Read {filename} ({len(content)} chars) as editing context.",
                f"File: {filename}\n\n{content}",
            )
        except FileNotFoundError:
            return ToolResult(
                "file_edit_tool",
                f"File {filename!r} does not exist yet — will be created.",
                f"Creating new file: {filename}",
            )
        except (ValueError, OSError) as exc:
            return ToolResult(
                "file_edit_tool",
                f"Cannot read {filename}: {exc}",
                str(exc),
            )

    def web_search_tool(self, prompt: str) -> ToolResult:
        """Search using DuckDuckGo Instant Answers API (no API key required).

        Args:
            prompt: User prompt including the search query.

        Returns:
            ToolResult with search summary and related topics.
        """
        import urllib.parse
        # Extract the actual query
        query = prompt.strip()
        for prefix in ("search for", "look up", "find online", "google", "web search",
                        "search the web", "find information about", "search"):
            if query.lower().startswith(prefix):
                query = query[len(prefix):].strip().lstrip(":").strip()
                break

        if not query:
            return ToolResult("web_search_tool", "Empty search query.", "No query provided.")

        encoded = urllib.parse.quote_plus(query[:200])
        url = f"https://api.duckduckgo.com/?q={encoded}&format=json&no_html=1&skip_disambig=1"
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "MidDayWorkbench/1.0 (local agent)"},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            return ToolResult("web_search_tool", "Web search failed.", f"Error: {exc}")

        parts = []
        if data.get("AbstractText"):
            parts.append(f"**Summary:** {data['AbstractText']}")
            if data.get("AbstractURL"):
                parts.append(f"**Source:** {data['AbstractURL']}")
        for topic in data.get("RelatedTopics", [])[:6]:
            if isinstance(topic, dict) and topic.get("Text"):
                parts.append(f"- {topic['Text']}")
        for result in data.get("Results", [])[:3]:
            if isinstance(result, dict) and result.get("Text"):
                parts.append(f"- {result['Text']}")

        content = "\n\n".join(parts) if parts else f"No results found for: {query}"
        return ToolResult(
            "web_search_tool",
            f"Web search: {query[:60]}",
            content,
        )

    def command_runner_tool(self, prompt: str) -> ToolResult:
        """Run one safe command inferred from the prompt through the sandbox."""

        command = self._extract_command(prompt)
        sandbox = ExecutionSandbox(PROJECT_ROOT)
        decision = sandbox.decide(command, timeout=20)
        if not decision.allowed:
            payload = {
                "command": command,
                "allowed": False,
                "reason": decision.reason,
                "matched_prefix": decision.matched_prefix,
                "blocked_pattern": decision.blocked_pattern,
                "allowed_examples": sandbox.allowed_commands()[:12],
            }
            return ToolResult(
                "command_runner_tool",
                "Command was blocked by the sandbox policy.",
                json.dumps(payload, indent=2),
            )

        result = sandbox.run_read_only(command, timeout=20)
        payload = {
            "command": result.command,
            "allowed": True,
            "exit_code": result.exit_code,
            "output": result.output,
        }
        return ToolResult(
            "command_runner_tool",
            f"Ran sandbox command `{command}` with exit code {result.exit_code}.",
            json.dumps(payload, indent=2),
        )

    def _extract_command(self, prompt: str) -> str:
        """Extract a portable sandbox command from a natural-language request."""

        fenced = re.search(r"`([^`]+)`", prompt)
        if fenced:
            return fenced.group(1).strip()

        normalized = prompt.lower().strip()
        if "git status" in normalized:
            return "git status"
        if "git diff" in normalized:
            return "git diff --stat"
        if "secret scan" in normalized:
            return "python -m agent_core.secret_scan"
        if "eval" in normalized:
            return "python -m agent_core.evals"
        if "frontend" in normalized or "javascript" in normalized or "js syntax" in normalized:
            return "node --check web/app.js"
        if "compile" in normalized:
            return "python -m compileall agent_core"
        if "pytest" in normalized:
            return "python -m pytest tests/ -v"
        if "unittest" in normalized or "test" in normalized:
            return "python -m unittest tests.test_router tests.test_tools"
        if normalized.startswith("run "):
            return prompt[4:].strip()
        if normalized.startswith("execute "):
            return prompt[8:].strip()
        return prompt.strip()

    def _interesting_paths(self, prompt: str, limit: int) -> list[str]:
        hits = search(self.config.index_path, prompt, limit=limit)
        seen = []
        for hit in hits:
            path = hit["path"]
            if path not in seen and self._safe_relative(path):
                seen.append(path)
        return seen

    def _safe_relative(self, relative: str) -> bool:
        lowered = relative.lower()
        blocked = (".env", "secret", "token", "key", "password", "credential", "__pycache__")
        return not any(part in lowered for part in blocked)

    def _safe_to_pack(self, path: Path) -> bool:
        try:
            path.relative_to(self.config.workspace_root)
        except ValueError:
            return False
        return self._safe_relative(str(path.relative_to(self.config.workspace_root)))
