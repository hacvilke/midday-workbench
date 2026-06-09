"""Midday Workbench — local-first AI agent HTTP server."""
from __future__ import annotations

import json
import os
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from agent_core.agent import Agent, AgentRun
from agent_core.config import PROJECT_ROOT, get_config
from agent_core.file_editor import FileEditorTool
from agent_core.health import health_report
from agent_core.memory import add_message, clear_session, get_recent_messages
from agent_core.oss_tools import OssToolRegistry
from agent_core.output_templates import template_registry
from agent_core.prompt_harness import prompt_registry
from agent_core.repo_graph import build_repo_graph
from agent_core.tool_schemas import oss_tool_schemas
from agent_core.providers import configured_providers
from agent_core.run_log import (
    add_command_run,
    add_run,
    clear_command_runs,
    clear_runs,
    get_sessions,
    recent_command_runs,
    recent_runs,
)
from agent_core.sandbox import ExecutionSandbox
from agent_core.verifier import ReActVerifier


WEB_ROOT = PROJECT_ROOT / "web"


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        pass

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/api/status":
            config = get_config()
            registry = OssToolRegistry(config)
            return self.send_json(
                {
                    "provider": config.provider,
                    "provider_route": [p.name for p in configured_providers(config)],
                    "has_groq_key": bool(config.groq_api_key),
                    "has_openrouter_key": bool(config.openrouter_api_key),
                    "tools": registry.manifest().splitlines(),
                    "tool_records": registry.tool_records(),
                    "tool_schemas": oss_tool_schemas(),
                }
            )

        if parsed.path == "/api/prompts":
            return self.send_json(prompt_registry())

        if parsed.path == "/api/templates":
            return self.send_json(template_registry())

        if parsed.path == "/api/health":
            return self.send_json(health_report())

        if parsed.path == "/api/graph":
            return self.send_json(build_repo_graph(get_config().workspace_root).to_dict())

        if parsed.path == "/api/memory":
            session_id = _query_param(parsed.query, "session_id") or "default"
            return self.send_json({"messages": get_recent_messages(session_id, limit=20)})

        if parsed.path == "/api/runs":
            session_id = _query_param(parsed.query, "session_id")
            return self.send_json({"runs": recent_runs(session_id=session_id, limit=20)})

        if parsed.path == "/api/sessions":
            return self.send_json({"sessions": get_sessions(limit=50)})

        if parsed.path == "/api/commands":
            session_id = _query_param(parsed.query, "session_id")
            return self.send_json({"commands": recent_command_runs(session_id=session_id, limit=20)})

        if parsed.path == "/api/sandbox":
            sandbox = ExecutionSandbox(get_config().workspace_root)
            return self.send_json({"allowed_commands": sandbox.allowed_commands()})

        if parsed.path == "/api/files/read":
            path = _query_param(parsed.query, "path") or ""
            if not path:
                return self.send_json({"error": "path parameter required"}, status=400)
            editor = FileEditorTool(get_config().workspace_root)
            try:
                content = editor.read_file(path)
                return self.send_json({"path": path, "content": content, "size": len(content)})
            except FileNotFoundError as exc:
                return self.send_json({"error": str(exc)}, status=404)
            except ValueError as exc:
                return self.send_json({"error": str(exc)}, status=403)

        if parsed.path == "/api/files/list":
            pattern = _query_param(parsed.query, "pattern") or "**/*.py"
            editor = FileEditorTool(get_config().workspace_root)
            return self.send_json({"files": editor.list_files(pattern)})

        if parsed.path == "/":
            return self.send_file(WEB_ROOT / "index.html", "text/html")

        if parsed.path == "/app.js":
            return self.send_file(WEB_ROOT / "app.js", "application/javascript")

        if parsed.path == "/style.css":
            return self.send_file(WEB_ROOT / "style.css", "text/css")

        self.send_error(404)

    def do_POST(self):
        if self.path == "/api/memory/clear":
            body = self._read_json()
            clear_session(body.get("session_id", "default"))
            return self.send_json({"ok": True})

        if self.path == "/api/runs/clear":
            body = self._read_json()
            clear_runs(body.get("session_id"))
            return self.send_json({"ok": True})

        if self.path == "/api/commands/clear":
            body = self._read_json()
            clear_command_runs(body.get("session_id"))
            return self.send_json({"ok": True})

        if self.path == "/api/tools/run":
            body = self._read_json()
            registry = OssToolRegistry(get_config())
            try:
                result = registry.run_tool_by_name(body.get("tool", ""), body.get("query", ""))
            except KeyError as exc:
                return self.send_json({"error": str(exc)}, status=400)
            return self.send_json({"name": result.name, "summary": result.summary, "content": result.content})

        if self.path == "/api/sandbox/run":
            body = self._read_json()
            sandbox = ExecutionSandbox(get_config().workspace_root)
            command = str(body.get("command", ""))
            session_id = str(body.get("session_id", "default"))
            started = time.perf_counter()
            try:
                result = sandbox.run_read_only(command, timeout=20)
            except Exception as exc:
                return self.send_json({"error": str(exc)}, status=400)
            verifier = ReActVerifier()
            report = verifier.verify_command_result(result.command, result.exit_code, result.output)
            duration_ms = int((time.perf_counter() - started) * 1000)
            verified = {"passed": report.passed, "issues": report.issues, "summary": report.summary}
            add_command_run(session_id, result.command, result.exit_code, result.output, verified, duration_ms)
            return self.send_json(
                {
                    "command": result.command,
                    "exit_code": result.exit_code,
                    "output": result.output,
                    "verified": verified,
                    "duration_ms": duration_ms,
                }
            )

        if self.path == "/api/files/write":
            body = self._read_json()
            path = body.get("path", "")
            content = body.get("content", "")
            if not path:
                return self.send_json({"error": "path required"}, status=400)
            editor = FileEditorTool(get_config().workspace_root)
            try:
                msg = editor.write_file(path, content)
                return self.send_json({"ok": True, "message": msg})
            except (ValueError, OSError) as exc:
                return self.send_json({"error": str(exc)}, status=400)

        if self.path == "/api/files/patch":
            body = self._read_json()
            path = body.get("path", "")
            search = body.get("search", "")
            replace = body.get("replace", "")
            if not path or not search:
                return self.send_json({"error": "path and search required"}, status=400)
            editor = FileEditorTool(get_config().workspace_root)
            try:
                msg = editor.patch_file(path, search, replace)
                return self.send_json({"ok": True, "message": msg})
            except (FileNotFoundError, ValueError, OSError) as exc:
                return self.send_json({"error": str(exc)}, status=400)

        if self.path == "/api/chat/stream":
            body = self._read_json()
            session_id = body.get("session_id", "default")
            prompt = body.get("prompt", "")
            history = get_recent_messages(session_id, limit=8)
            add_message(session_id, "user", prompt)

            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("X-Accel-Buffering", "no")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

            def write_event(data: dict) -> bool:
                try:
                    msg = f"data: {json.dumps(data)}\n\n".encode("utf-8")
                    self.wfile.write(msg)
                    self.wfile.flush()
                    return True
                except (BrokenPipeError, ConnectionResetError, OSError):
                    return False

            full_answer = ""
            metadata = None
            try:
                agent = Agent()
                for event in agent.stream_with_events(prompt, history=history):
                    if event.get("type") == "token":
                        full_answer += event.get("token", "")
                    if event.get("type") == "done":
                        metadata = event.get("metadata", {})
                    if not write_event(event):
                        break
            except Exception as exc:
                write_event({"type": "error", "error": str(exc)})

            if full_answer:
                add_message(session_id, "agent", full_answer)
            if metadata:
                try:
                    run = AgentRun(
                        run_id=metadata.get("run_id", ""),
                        answer=full_answer or metadata.get("answer", ""),
                        tools_used=metadata.get("tools_used", []),
                        react_steps=metadata.get("react_steps", []),
                        context_attached=metadata.get("context_attached", False),
                        memory_items=metadata.get("memory_items", 0),
                        provider=metadata.get("provider", "offline"),
                        duration_ms=metadata.get("duration_ms", 0),
                        fallback_used=metadata.get("fallback_used", False),
                        error=metadata.get("error"),
                        provider_attempts=metadata.get("provider_attempts", []),
                        verifier_reports=metadata.get("verifier_reports", []),
                        plan=metadata.get("plan"),
                    )
                    add_run(session_id, prompt, run)
                except Exception:
                    pass
            return

        if self.path != "/api/chat":
            return self.send_error(404)

        body = self._read_json()
        session_id = body.get("session_id", "default")
        prompt = body.get("prompt", "")
        history = get_recent_messages(session_id, limit=8)
        add_message(session_id, "user", prompt)
        run = Agent().run_with_metadata(prompt, history=history)
        add_run(session_id, prompt, run)
        add_message(session_id, "agent", run.answer)
        self.send_json(
            {
                "answer": run.answer,
                "metadata": {
                    "run_id": run.run_id,
                    "tools_used": run.tools_used,
                    "react_steps": run.react_steps,
                    "context_attached": run.context_attached,
                    "memory_items": run.memory_items,
                    "provider": run.provider,
                    "duration_ms": run.duration_ms,
                    "fallback_used": run.fallback_used,
                    "error": run.error,
                    "provider_attempts": run.provider_attempts,
                    "verifier_reports": run.verifier_reports,
                    "plan": run.plan,
                },
            }
        )

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8") if length else "{}"
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {}

    def send_json(self, payload: dict, status: int = 200):
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(data)

    def send_file(self, path: Path, content_type: str):
        try:
            data = path.read_bytes()
        except FileNotFoundError:
            return self.send_error(404)
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def _query_param(query_string: str, key: str) -> str | None:
    for part in (query_string or "").split("&"):
        if "=" in part:
            k, v = part.split("=", 1)
            if k == key:
                return v
    return None


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8765))
    host = os.environ.get("HOST", "127.0.0.1")
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"Midday Workbench running at http://{host}:{port}")
    server.serve_forever()
