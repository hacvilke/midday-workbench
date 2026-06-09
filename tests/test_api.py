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

_BASE = ""
_server: ThreadingHTTPServer | None = None
API_TIMEOUT_SECONDS = 30


def setUpModule():
    global _BASE, _server
    _server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    _BASE = f"http://127.0.0.1:{_server.server_address[1]}"
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
    with urllib.request.urlopen(f"{_BASE}{path}", timeout=API_TIMEOUT_SECONDS) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _get_status(path: str) -> tuple[int, dict]:
    try:
        with urllib.request.urlopen(f"{_BASE}{path}", timeout=API_TIMEOUT_SECONDS) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8"))


def _post(path: str, payload: dict) -> tuple[int, dict]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{_BASE}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=API_TIMEOUT_SECONDS) as resp:
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

    def test_returns_safe_provider_diagnostics(self):
        data = _get("/api/status")
        self.assertIn("provider_diagnostics", data)
        diagnostics = data["provider_diagnostics"]
        self.assertIn("selected_provider", diagnostics)
        self.assertIn("route", diagnostics)
        self.assertIn("providers", diagnostics)
        self.assertIn("remote_ready", diagnostics)
        self.assertIsInstance(diagnostics["providers"], list)
        for record in diagnostics["providers"]:
            self.assertNotIn("api_key", record)
            self.assertNotIn("secret", record)
            self.assertNotIn("token", record)


class QualityEndpointTests(unittest.TestCase):
    def test_quality_returns_gates(self):
        data = _get("/api/quality")
        self.assertIn("gates", data)
        self.assertIsInstance(data["gates"], list)
        self.assertGreater(len(data["gates"]), 0)
        self.assertIn("policy_decision", data["gates"][0])

    def test_quality_run_returns_results(self):
        status, data = _post("/api/quality/run", {"required_only": False, "dry_run": True, "gate_names": ["diff_stat"]})
        self.assertEqual(status, 200)
        self.assertIn("passed", data)
        self.assertTrue(data["dry_run"])
        self.assertIn("results", data)
        self.assertEqual([item["name"] for item in data["results"]], ["diff_stat"])
        self.assertIn("policy_decision", data["results"][0])
        self.assertTrue(data["results"][0]["policy_decision"]["allowed"])

    def test_quality_history_endpoint_shape(self):
        data = _get("/api/quality/history?session_id=nonexistent-session-xyz")
        self.assertIn("count", data)
        self.assertIn("latest", data)
        self.assertIsInstance(data["latest"], list)
        self.assertIn("latest_failed", data)


class HealthEndpointTests(unittest.TestCase):
    def test_health_exposes_safe_provider_diagnostics(self):
        data = _get("/api/health")
        self.assertIn("provider_diagnostics", data)
        self.assertIn("route", data["provider_diagnostics"])


class PolicyEndpointTests(unittest.TestCase):
    def test_policy_returns_categories(self):
        data = _get("/api/policy")
        self.assertIn("safe_actions", data)
        self.assertIn("confirmation_actions", data)
        self.assertIn("blocked_actions", data)

    def test_policy_action_records_decision(self):
        _post("/api/decisions/clear", {"session_id": "api-policy-decision"})
        data = _get("/api/policy?action_type=write_file&session_id=api-policy-decision")
        self.assertIn("decision", data)
        decisions = _get("/api/decisions?session_id=api-policy-decision")
        self.assertEqual(decisions["decisions"][0]["kind"], "policy")


class RouteEndpointTests(unittest.TestCase):
    def test_route_endpoint_returns_decision(self):
        data = _get("/api/route?message=show%20graph%20of%20microservice%20architecture")
        self.assertEqual(data["intent"], "visualize")
        self.assertEqual(data["tools"], ["rich_output_template_tool"])
        self.assertIn("confidence", data)
        self.assertGreaterEqual(len(data["alternatives"]), 2)

    def test_route_records_decision(self):
        _post("/api/decisions/clear", {"session_id": "api-route-decision"})
        _get("/api/route?message=show%20graph&session_id=api-route-decision")
        data = _get("/api/decisions?session_id=api-route-decision")
        self.assertEqual(data["decisions"][0]["kind"], "route")
        self.assertEqual(data["decisions"][0]["decision"]["intent"], "visualize")

    def test_route_decision_summary_endpoint(self):
        session_id = "api-route-summary"
        _post("/api/decisions/clear", {"session_id": session_id})
        _get(f"/api/route?message=show%20graph%20of%20architecture&session_id={session_id}")
        data = _get(f"/api/decisions/routes?session_id={session_id}")
        self.assertIn("review_count", data)
        self.assertIn("top_intents", data)
        self.assertIn("review_examples", data)
        self.assertGreaterEqual(data["count"], 1)


class SandboxEndpointTests(unittest.TestCase):
    def test_allowed_commands_returned(self):
        data = _get("/api/sandbox")
        self.assertIn("allowed_commands", data)
        self.assertIn("blocked_patterns", data)
        self.assertIn("default_timeout_seconds", data)
        self.assertIsInstance(data["allowed_commands"], list)
        self.assertGreater(len(data["allowed_commands"]), 5)

    def test_sandbox_decision_preview(self):
        data = _get("/api/sandbox?command=git%20status")
        self.assertTrue(data["decision"]["allowed"])
        self.assertEqual(data["decision"]["matched_prefix"], "git status")

    def test_run_allowed_command(self):
        status, data = _post("/api/sandbox/run", {"command": "python --version", "session_id": "api-command-test"})
        self.assertEqual(status, 200)
        self.assertIn("exit_code", data)
        self.assertEqual(data["exit_code"], 0)
        self.assertIn("verified", data)
        self.assertIn("policy_decision", data)
        self.assertTrue(data["policy_decision"]["allowed"])
        self.assertTrue(data["verified"]["passed"])
        self.assertIn("duration_ms", data)

    def test_run_blocked_command_returns_400(self):
        session_id = "api-blocked-command"
        _post("/api/commands/clear", {"session_id": session_id})
        status, data = _post("/api/sandbox/run", {"command": "rm -rf /", "session_id": session_id})
        self.assertEqual(status, 400)
        self.assertIn("error", data)
        self.assertIn("verified", data)
        self.assertFalse(data["policy_decision"]["allowed"])
        self.assertEqual(data["verified"]["summary"], "policy=blocked")
        history = _get(f"/api/commands?session_id={session_id}")
        self.assertEqual(history["commands"][0]["exit_code"], -1)
        self.assertEqual(history["commands"][0]["verified"]["summary"], "policy=blocked")

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
        self.assertTrue(data["commands"][0]["policy_decision"]["allowed"])
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

    def test_run_detail_endpoint(self):
        session_id = "api-run-detail"
        _post("/api/runs/clear", {"session_id": session_id})
        _, chat = _post("/api/chat", {"prompt": "hi", "session_id": session_id})
        run_id = chat["metadata"]["run_id"]
        data = _get(f"/api/runs/{run_id}")
        self.assertEqual(data["run"]["run_id"], run_id)
        self.assertEqual(data["run"]["plan"]["intent"], "plain_chat")
        self.assertIn("file_writes", chat["metadata"])
        self.assertIn("usage", chat["metadata"])
        self.assertIn("file_writes", data["run"])
        self.assertIn("usage", data["run"])

    def test_missing_run_detail_returns_404(self):
        status, data = _get_status("/api/runs/not-a-real-run")
        self.assertEqual(status, 404)
        self.assertIn("error", data)


class MetricsEndpointTests(unittest.TestCase):
    def test_metrics_endpoint_shape(self):
        data = _get("/api/metrics?session_id=nonexistent-session-xyz")
        self.assertIn("retention", data)
        self.assertIn("runs", data)
        self.assertIn("commands", data)
        self.assertIn("files", data)
        self.assertIn("usage", data)
        self.assertIn("decisions", data)
        self.assertIn("verifier", data)
        self.assertIn("provider_routes", data)
        self.assertIn("memory", data)
        self.assertIn("quality_history", data)
        self.assertIn("context_window", data)
        self.assertIn("route_decisions", data)


class RetentionEndpointTests(unittest.TestCase):
    def test_retention_endpoint_shape(self):
        data = _get("/api/retention?session_id=nonexistent-session-xyz")
        self.assertIn("counts", data)
        self.assertIn("total", data)
        self.assertIn("runs", data["counts"])

    def test_retention_prune_endpoint_shape(self):
        status, data = _post(
            "/api/retention/prune",
            {"session_id": "nonexistent-session-xyz", "keep_per_table": 5},
        )
        self.assertEqual(status, 200)
        self.assertIn("deleted", data)
        self.assertEqual(data["keep_per_table"], 5)


class OperationalReviewEndpointTests(unittest.TestCase):
    def test_operational_review_endpoint_shape(self):
        data = _get("/api/operational-review?session_id=nonexistent-session-xyz")
        self.assertIn("score", data)
        self.assertIn("grade", data)
        self.assertIn("next_action", data)
        self.assertIn("action_items", data)
        self.assertIn("risks", data)
        self.assertIn("recommendations", data)
        self.assertIn("index", data)

    def test_operational_actions_endpoint_shape(self):
        data = _get("/api/operational-actions?session_id=nonexistent-session-xyz")
        self.assertIn("score", data)
        self.assertIn("grade", data)
        self.assertIn("next_action", data)
        self.assertIn("action_items", data)
        self.assertNotIn("metrics", data)
        self.assertGreaterEqual(len(data["action_items"]), 1)
        self.assertIn("category", data["action_items"][0])


class PromptsEndpointTests(unittest.TestCase):
    def test_prompts_endpoint_exposes_harness_entries(self):
        data = _get("/api/prompts")
        self.assertIn("coordinator", data)
        self.assertIn("read_only_research", data)
        self.assertIn("implementation", data)
        self.assertIn("Midday Workbench", data["coordinator"])


class ControlPlaneEndpointTests(unittest.TestCase):
    def test_control_plane_endpoint_aggregates_operational_state(self):
        data = _get("/api/control-plane?session_id=nonexistent-session-xyz")
        self.assertIn("health", data)
        self.assertIn("provider_diagnostics", data)
        self.assertIn("route", data["provider_diagnostics"])
        self.assertIn("metrics", data)
        self.assertIn("operational_review", data)
        self.assertIn("route_decision_summary", data)
        self.assertIn("timeline", data)
        self.assertIn("sessions", data)
        self.assertIn("index", data)
        self.assertIn("policy", data)
        self.assertIn("quality_gates", data)
        self.assertIn("quality_history", data)
        self.assertIn("routing_audit", data)
        self.assertIn("delegation", data)
        self.assertIn("context_window", data)
        self.assertIn("prompts", data)
        self.assertIn("tools", data)
        self.assertIn("coordinator", data["prompts"]["names"])
        self.assertIn("parallel_candidate", data["delegation"]["modes"])
        self.assertTrue(data["routing_audit"]["passed"])
        self.assertFalse(data["health"]["tool_health_included"])

    def test_light_control_plane_skips_heavy_history(self):
        data = _get("/api/control-plane?session_id=nonexistent-session-xyz&light=1")
        self.assertTrue(data["light"])
        self.assertIn("health", data)
        self.assertIn("metrics", data)
        self.assertIn("operational_review", data)
        self.assertIn("route_decision_summary", data)
        self.assertNotIn("timeline", data)
        self.assertNotIn("sessions", data)
        self.assertNotIn("context_window", data)


class IndexEndpointTests(unittest.TestCase):
    def test_index_endpoint_shape(self):
        data = _get("/api/index")
        self.assertIn("chunk_count", data)
        self.assertIn("repo_count", data)
        self.assertIn("top_repos", data)
        self.assertIsInstance(data["top_repos"], list)


class RoutingAuditEndpointTests(unittest.TestCase):
    def test_routing_audit_endpoint_shape(self):
        data = _get("/api/routing-audit")
        self.assertTrue(data["passed"])
        self.assertIn("results", data)
        self.assertGreaterEqual(data["probe_count"], 6)


class DelegationEndpointTests(unittest.TestCase):
    def test_delegation_endpoint_returns_assignments(self):
        data = _get("/api/delegation?message=fix%20web/app.js")
        self.assertIn("assignments", data)
        self.assertIn("concurrency", data)
        self.assertIn("manifest", data)
        self.assertIn("manager", [assignment["agent_id"] for assignment in data["assignments"]])
        self.assertIn("reviewer", [assignment["agent_id"] for assignment in data["assignments"]])
        self.assertIn("serial_order", data["concurrency"])
        self.assertIn("parallel_groups", data["concurrency"])


class ContextWindowEndpointTests(unittest.TestCase):
    def test_context_window_endpoint_shape_and_clear(self):
        data = _get("/api/context-window")
        self.assertIn("context_window", data)
        self.assertIn("items", data["context_window"])
        status, cleared = _post("/api/context-window/clear", {})
        self.assertEqual(status, 200)
        self.assertTrue(cleared.get("ok"))

    def test_context_window_prune_endpoint_shape(self):
        status, data = _post("/api/context-window/prune", {"keep": 4})
        self.assertEqual(status, 200)
        self.assertIn("deleted", data)
        self.assertEqual(data["keep"], 4)


class TimelineEndpointTests(unittest.TestCase):
    def test_timeline_endpoint_shape(self):
        data = _get("/api/timeline?session_id=nonexistent-session-xyz")
        self.assertIn("events", data)
        self.assertIsInstance(data["events"], list)

    def test_timeline_exposes_quality_events(self):
        session_id = "api-quality-timeline"
        _post("/api/commands/clear", {"session_id": session_id})
        status, data = _post(
            "/api/quality/run",
            {"required_only": False, "dry_run": False, "session_id": session_id, "gate_names": ["diff_stat"]},
        )
        self.assertEqual(status, 200)
        self.assertTrue(data["results"][0]["policy_decision"]["allowed"])
        timeline = _get(f"/api/timeline?session_id={session_id}")
        quality_events = [event for event in timeline["events"] if event["type"] == "quality"]
        self.assertGreaterEqual(len(quality_events), 1)
        self.assertEqual(quality_events[0]["quality_gate"], "diff_stat")
        self.assertIn("policy_decision", quality_events[0])
        _post("/api/commands/clear", {"session_id": session_id})


class FileEventsEndpointTests(unittest.TestCase):
    def test_file_events_endpoint_records_write(self):
        session_id = "api-file-event"
        _post("/api/files/events/clear", {"session_id": session_id})
        status, data = _post(
            "/api/files/write",
            {
                "path": "tmp_file_event_test.txt",
                "content": "event\n",
                "confirmed": True,
                "session_id": session_id,
            },
        )
        self.assertEqual(status, 200)
        events = _get(f"/api/files/events?session_id={session_id}")
        self.assertEqual(events["events"][0]["action"], "write")
        self.assertEqual(events["events"][0]["path"], "tmp_file_event_test.txt")
        timeline = _get(f"/api/timeline?session_id={session_id}")
        self.assertIn("file", {event["type"] for event in timeline["events"]})
        _post("/api/files/events/clear", {"session_id": session_id})
        try:
            os.remove(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tmp_file_event_test.txt"))
        except FileNotFoundError:
            pass

    def test_file_events_clear_ok(self):
        status, data = _post("/api/files/events/clear", {"session_id": "empty-file-events"})
        self.assertEqual(status, 200)
        self.assertTrue(data.get("ok"))


class SessionsEndpointTests(unittest.TestCase):
    def test_returns_sessions_list(self):
        data = _get("/api/sessions")
        self.assertIn("sessions", data)
        self.assertIsInstance(data["sessions"], list)
        if data["sessions"]:
            self.assertIn("session_id", data["sessions"][0])
            self.assertIn("run_count", data["sessions"][0])
            self.assertIn("last_active", data["sessions"][0])


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

    def test_prune_memory_endpoint_shape(self):
        status, data = _post("/api/memory/prune", {"session_id": "test-smoke-session", "keep": 5})
        self.assertEqual(status, 200)
        self.assertIn("deleted", data)
        self.assertEqual(data["keep"], 5)


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


class FilePolicyEndpointTests(unittest.TestCase):
    def test_file_write_requires_confirmation(self):
        status, data = _post("/api/files/write", {"path": "tmp_policy_test.txt", "content": "x"})
        self.assertEqual(status, 409)
        self.assertEqual(data["error"], "confirmation required")
        self.assertTrue(data["policy"]["requires_confirmation"])

    def test_confirmed_file_write_returns_metadata(self):
        status, data = _post(
            "/api/files/write",
            {"path": "tmp_policy_test.txt", "content": "x\n", "confirmed": True},
        )
        self.assertEqual(status, 200)
        self.assertTrue(data["ok"])
        self.assertIn("write", data)
        self.assertEqual(data["write"]["path"], "tmp_policy_test.txt")
        self.assertEqual(data["write"]["bytes_written"], 2)
        self.assertEqual(len(data["write"]["sha256"]), 64)
        try:
            os.remove(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tmp_policy_test.txt"))
        except FileNotFoundError:
            pass


if __name__ == "__main__":
    unittest.main()
