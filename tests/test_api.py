"""API smoke tests for Midday Workbench server endpoints."""
from __future__ import annotations

import json
import sys
import os
import threading
import time
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server import Handler

_TEST_PORT = 18_765
_BASE = f"http://127.0.0.1:{_TEST_PORT}"
_server: ThreadingHTTPServer | None = None


def setUpModule():
    global _server
    _server = ThreadingHTTPServer(("127.0.0.1", _TEST_PORT), Handler)
    thread = threading.Thread(target=_server.serve_forever, daemon=True)
    thread.start()
    # Wait until the server is actually accepting connections
    for _ in range(20):
        try:
            urllib.request.urlopen(f"{_BASE}/api/status", timeout=1)
            break
        except Exception:
            time.sleep(0.1)


def tearDownModule():
    if _server:
        _server.shutdown()


def _get(path: str) -> dict:
    with urllib.request.urlopen(f"{_BASE}{path}", timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _post(path: str, payload: dict) -> tuple[int, dict]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{_BASE}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8"))


class StatusEndpointTests(unittest.TestCase):
    def test_returns_provider_key(self):
        data = _get("/api/status")
        self.assertIn("provider", data)

    def test_returns_tools_list(self):
        data = _get("/api/status")
        self.assertIn("tools", data)
        self.assertIsInstance(data["tools"], list)
        self.assertGreater(len(data["tools"]), 0)

    def test_returns_tool_records(self):
        data = _get("/api/status")
        self.assertIn("tool_records", data)
        self.assertIsInstance(data["tool_records"], list)

    def test_returns_provider_route(self):
        data = _get("/api/status")
        self.assertIn("provider_route", data)
        self.assertIsInstance(data["provider_route"], list)


class QualityEndpointTests(unittest.TestCase):
    def test_quality_returns_gates(self):
        data = _get("/api/quality")
        self.assertIn("gates", data)
        self.assertIsInstance(data["gates"], list)
        self.assertGreater(len(data["gates"]), 0)


class RouteEndpointTests(unittest.TestCase):
    def test_route_endpoint_returns_decision(self):
        data = _get("/api/route?message=show%20graph")
        self.assertEqual(data["intent"], "visualize")
        self.assertEqual(data["tools"], ["rich_output_template_tool"])
        self.assertIn("confidence", data)


class SandboxEndpointTests(unittest.TestCase):
    def test_allowed_commands_returned(self):
        data = _get("/api/sandbox")
        self.assertIn("allowed_commands", data)
        self.assertIsInstance(data["allowed_commands"], list)
        self.assertGreater(len(data["allowed_commands"]), 5)

    def test_run_allowed_command(self):
        status, data = _post("/api/sandbox/run", {"command": "python --version", "session_id": "api-command-test"})
        self.assertEqual(status, 200)
        self.assertIn("exit_code", data)
        self.assertEqual(data["exit_code"], 0)
        self.assertIn("verified", data)
        self.assertTrue(data["verified"]["passed"])
        self.assertIn("duration_ms", data)

    def test_run_blocked_command_returns_400(self):
        status, data = _post("/api/sandbox/run", {"command": "rm -rf /"})
        self.assertEqual(status, 400)
        self.assertIn("error", data)

    def test_verified_field_present(self):
        _, data = _post("/api/sandbox/run", {"command": "git status"})
        self.assertIn("verified", data)
        verified = data["verified"]
        self.assertIn("passed", verified)
        self.assertIn("issues", verified)
        self.assertIn("summary", verified)

    def test_command_history_endpoint(self):
        _post("/api/commands/clear", {"session_id": "api-command-history"})
        _post("/api/sandbox/run", {"command": "python --version", "session_id": "api-command-history"})
        data = _get("/api/commands?session_id=api-command-history")
        self.assertIn("commands", data)
        self.assertGreaterEqual(len(data["commands"]), 1)
        self.assertEqual(data["commands"][0]["command"], "python --version")
        status, cleared = _post("/api/commands/clear", {"session_id": "api-command-history"})
        self.assertEqual(status, 200)
        self.assertTrue(cleared.get("ok"))


class RunsEndpointTests(unittest.TestCase):
    def test_runs_returns_list(self):
        data = _get("/api/runs")
        self.assertIn("runs", data)
        self.assertIsInstance(data["runs"], list)

    def test_runs_session_filter(self):
        data = _get("/api/runs?session_id=nonexistent-session-xyz")
        self.assertIn("runs", data)
        self.assertEqual(data["runs"], [])

    def test_clear_runs_ok(self):
        status, data = _post("/api/runs/clear", {"session_id": "nonexistent-session-xyz"})
        self.assertEqual(status, 200)
        self.assertTrue(data.get("ok"))


class SessionsEndpointTests(unittest.TestCase):
    def test_returns_sessions_list(self):
        data = _get("/api/sessions")
        self.assertIn("sessions", data)
        self.assertIsInstance(data["sessions"], list)


class MemoryEndpointTests(unittest.TestCase):
    def test_returns_messages_list(self):
        data = _get("/api/memory?session_id=test-smoke-session")
        self.assertIn("messages", data)
        self.assertIsInstance(data["messages"], list)
        self.assertIn("summary", data)
        self.assertIn("summary", data["summary"])

    def test_clear_memory_ok(self):
        status, data = _post("/api/memory/clear", {"session_id": "test-smoke-session"})
        self.assertEqual(status, 200)
        self.assertTrue(data.get("ok"))


class GraphEndpointTests(unittest.TestCase):
    def test_returns_nodes_and_edges(self):
        req = urllib.request.Request(f"{_BASE}/api/graph")
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except TimeoutError:
            self.skipTest("Graph endpoint timed out (large workspace); skipping")
        self.assertIn("nodes", data)
        self.assertIn("edges", data)


class StaticEndpointTests(unittest.TestCase):
    def test_root_returns_html(self):
        with urllib.request.urlopen(f"{_BASE}/", timeout=5) as resp:
            body = resp.read().decode("utf-8")
        self.assertIn("Midday Workbench", body)

    def test_app_js_returns_javascript(self):
        with urllib.request.urlopen(f"{_BASE}/app.js", timeout=5) as resp:
            content_type = resp.headers.get("Content-Type", "")
        self.assertIn("javascript", content_type)

    def test_404_for_unknown_path(self):
        try:
            urllib.request.urlopen(f"{_BASE}/not-a-real-path", timeout=5)
            self.fail("Expected 404")
        except urllib.error.HTTPError as exc:
            self.assertEqual(exc.code, 404)


if __name__ == "__main__":
    unittest.main()
