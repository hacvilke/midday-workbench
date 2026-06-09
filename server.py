from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from agent_core.agent import Agent
from agent_core.config import PROJECT_ROOT, get_config
from agent_core.health import health_report
from agent_core.memory import add_message, clear_session, get_recent_messages
from agent_core.oss_tools import OssToolRegistry
from agent_core.output_templates import template_registry
from agent_core.prompt_harness import prompt_registry
from agent_core.repo_graph import build_repo_graph
from agent_core.tool_schemas import oss_tool_schemas
from agent_core.providers import configured_providers
from agent_core.run_log import add_run, clear_runs, recent_runs
from agent_core.sandbox import ExecutionSandbox


WEB_ROOT = PROJECT_ROOT / "web"


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/status":
            config = get_config()
            registry = OssToolRegistry(config)
            return self.send_json(
                {
                    "provider": config.provider,
                    "provider_route": [provider.name for provider in configured_providers(config)],
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
            session_id = parsed.query.split("session_id=", 1)[-1] if "session_id=" in parsed.query else "default"
            return self.send_json({"messages": get_recent_messages(session_id, limit=20)})
        if parsed.path == "/api/runs":
            session_id = parsed.query.split("session_id=", 1)[-1] if "session_id=" in parsed.query else None
            return self.send_json({"runs": recent_runs(session_id=session_id, limit=20)})
        if parsed.path == "/api/sandbox":
            sandbox = ExecutionSandbox(get_config().workspace_root)
            return self.send_json({"allowed_commands": sandbox.allowed_commands()})
        if parsed.path == "/":
            return self.send_file(WEB_ROOT / "index.html", "text/html")
        if parsed.path == "/app.js":
            return self.send_file(WEB_ROOT / "app.js", "application/javascript")
        if parsed.path == "/style.css":
            return self.send_file(WEB_ROOT / "style.css", "text/css")
        self.send_error(404)

    def do_POST(self):
        if self.path == "/api/memory/clear":
            length = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
            clear_session(body.get("session_id", "default"))
            return self.send_json({"ok": True})
        if self.path == "/api/runs/clear":
            length = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
            clear_runs(body.get("session_id"))
            return self.send_json({"ok": True})
        if self.path == "/api/tools/run":
            length = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
            registry = OssToolRegistry(get_config())
            try:
                result = registry.run_tool_by_name(body.get("tool", ""), body.get("query", ""))
            except KeyError as exc:
                return self.send_json({"error": str(exc)}, status=400)
            return self.send_json(
                {
                    "name": result.name,
                    "summary": result.summary,
                    "content": result.content,
                }
            )
        if self.path == "/api/sandbox/run":
            length = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
            sandbox = ExecutionSandbox(get_config().workspace_root)
            try:
                result = sandbox.run_read_only(str(body.get("command", "")), timeout=20)
            except Exception as exc:
                return self.send_json({"error": str(exc)}, status=400)
            return self.send_json(
                {
                    "command": result.command,
                    "exit_code": result.exit_code,
                    "output": result.output,
                }
            )
        if self.path != "/api/chat":
            return self.send_error(404)
        length = int(self.headers.get("Content-Length", "0"))
        body = json.loads(self.rfile.read(length).decode("utf-8"))
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
                },
            }
        )

    def send_json(self, payload: dict, status: int = 200):
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def send_file(self, path: Path, content_type: str):
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", 8765), Handler)
    print("OSS Agent Workbench running at http://127.0.0.1:8765")
    server.serve_forever()
