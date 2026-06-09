"""Tool integration tests for Midday Workbench."""
from __future__ import annotations

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent_core.config import get_config
from agent_core.oss_tools import OssToolRegistry, ToolResult
from agent_core.oss_tools import OssTool
from agent_core.react_loop import ReactPlanner, align_final_verifier_reports, format_react_trace
from agent_core.sandbox import ExecutionSandbox
from agent_core.verifier import ReActVerifier
from agent_core.react_loop import ReactStep


class OssToolRegistryTests(unittest.TestCase):
    """Integration tests for OssToolRegistry — runs tools against real (empty) workspace."""

    def setUp(self):
        self.config = get_config()
        self.registry = OssToolRegistry(self.config)

    def test_tool_records_structure(self):
        records = self.registry.tool_records()
        self.assertGreater(len(records), 0)
        for record in records:
            self.assertIn("name", record)
            self.assertIn("description", record)
            self.assertIn("repo", record)
            self.assertIn("triggers", record)

    def test_manifest_lists_all_tools(self):
        manifest = self.registry.manifest()
        self.assertIn("rich_output_template_tool", manifest)
        self.assertIn("system_design_tool", manifest)
        self.assertIn("erpnext_business_tool", manifest)

    def test_run_rich_output_template_returns_mermaid(self):
        result = self.registry.run_tool_by_name("rich_output_template_tool", "architecture diagram")
        self.assertEqual(result.name, "rich_output_template_tool")
        self.assertIn("mermaid", result.content.lower())

    def test_run_system_design_tool_returns_content(self):
        result = self.registry.run_tool_by_name("system_design_tool", "caching architecture scale")
        self.assertEqual(result.name, "system_design_tool")
        self.assertIsInstance(result.content, str)

    def test_run_aider_tool_returns_content(self):
        result = self.registry.run_tool_by_name("aider_git_native_tool", "repository map overview")
        self.assertEqual(result.name, "aider_git_native_tool")
        self.assertIsInstance(result.content, str)

    def test_run_gitingest_no_url_returns_guidance(self):
        result = self.registry.run_tool_by_name("gitingest_remote_context_tool", "ingest this repo")
        self.assertEqual(result.name, "gitingest_remote_context_tool")
        self.assertIn("GitHub URL", result.content)

    def test_run_gitingest_with_url_returns_url(self):
        result = self.registry.run_tool_by_name(
            "gitingest_remote_context_tool",
            "ingest https://github.com/Aider-AI/aider",
        )
        self.assertIn("github.com", result.content)

    def test_run_unknown_tool_raises(self):
        with self.assertRaises(KeyError):
            self.registry.run_tool_by_name("does_not_exist", "query")

    def test_select_tools_returns_list(self):
        selected = self.registry.select_tools("show me an architecture diagram")
        self.assertIsInstance(selected, list)


class SandboxTests(unittest.TestCase):
    """Tests for ExecutionSandbox allowlist enforcement."""

    def setUp(self):
        config = get_config()
        self.sandbox = ExecutionSandbox(config.workspace_root)

    def test_allowed_commands_not_empty(self):
        cmds = self.sandbox.allowed_commands()
        self.assertIsInstance(cmds, list)
        self.assertGreater(len(cmds), 5)

    def test_git_status_allowed(self):
        result = self.sandbox.run_read_only("git status")
        self.assertIsNotNone(result)
        self.assertIsInstance(result.output, str)

    def test_python_version_allowed(self):
        result = self.sandbox.run_read_only("python --version")
        self.assertEqual(result.exit_code, 0)

    def test_ls_allowed(self):
        result = self.sandbox.run_read_only("ls")
        self.assertEqual(result.exit_code, 0)

    def test_destructive_rm_blocked(self):
        with self.assertRaises(ValueError):
            self.sandbox.run_read_only("rm -rf /")

    def test_curl_blocked(self):
        with self.assertRaises(ValueError):
            self.sandbox.run_read_only("curl http://example.com")

    def test_arbitrary_write_blocked(self):
        with self.assertRaises(ValueError):
            self.sandbox.run_read_only("touch output.txt")

    def test_pipe_in_cat_blocked(self):
        with self.assertRaises(ValueError):
            self.sandbox.run_read_only("cat README.md | grep foo")

    def test_redirect_blocked(self):
        with self.assertRaises(ValueError):
            self.sandbox.run_read_only("echo hello > out.txt")

    def test_is_allowed_echo_with_pipe_false(self):
        self.assertFalse(self.sandbox.is_allowed("echo test | rm -rf /"))

    def test_is_allowed_git_status_true(self):
        self.assertTrue(self.sandbox.is_allowed("git status"))

    def test_is_allowed_git_log_true(self):
        self.assertTrue(self.sandbox.is_allowed("git log --oneline -5"))

    def test_secret_scan_allowed(self):
        self.assertTrue(self.sandbox.is_allowed("python -m agent_core.secret_scan"))

    def test_project_health_commands_allowed(self):
        self.assertTrue(self.sandbox.is_allowed("pytest tests"))
        self.assertTrue(self.sandbox.is_allowed("npm test"))
        self.assertTrue(self.sandbox.is_allowed("npm run build"))

    def test_npm_install_blocked(self):
        self.assertFalse(self.sandbox.is_allowed("npm install"))
        decision = self.sandbox.decide("npm install")
        self.assertEqual(decision.blocked_pattern, "npm install")

    def test_decide_allowed_command_explains_prefix(self):
        decision = self.sandbox.decide("git status")
        self.assertTrue(decision.allowed)
        self.assertEqual(decision.matched_prefix, "git status")
        self.assertIsNone(decision.blocked_pattern)

    def test_decide_blocked_command_explains_pattern(self):
        decision = self.sandbox.decide("cat README.md | grep foo")
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.matched_prefix, "cat ")
        self.assertEqual(decision.blocked_pattern, "|")

    def test_is_allowed_sudo_false(self):
        self.assertFalse(self.sandbox.is_allowed("sudo git status"))


class VerifierTests(unittest.TestCase):
    """Tests for ReActVerifier post-execution checks."""

    def setUp(self):
        self.verifier = ReActVerifier()

    def test_empty_content_fails(self):
        result = ToolResult("some_tool", "summary", "")
        report = self.verifier.verify_tool_result(0, "some_tool", result)
        self.assertFalse(report.passed)
        self.assertTrue(len(report.issues) > 0)

    def test_null_string_content_fails(self):
        result = ToolResult("some_tool", "summary", "null")
        report = self.verifier.verify_tool_result(0, "some_tool", result)
        self.assertFalse(report.passed)

    def test_good_result_passes(self):
        result = ToolResult("some_tool", "summary", "This is a valid output with enough content to pass.")
        report = self.verifier.verify_tool_result(0, "some_tool", result)
        self.assertTrue(report.passed)

    def test_mermaid_tool_without_mermaid_fails(self):
        result = ToolResult("rich_output_template_tool", "summary", "No diagram here at all.")
        report = self.verifier.verify_tool_result(0, "rich_output_template_tool", result)
        self.assertFalse(report.passed)
        self.assertTrue(any("Mermaid" in issue or "mermaid" in issue for issue in report.issues))

    def test_mermaid_tool_with_valid_mermaid_passes(self):
        content = "```mermaid\ngraph TD\n  A --> B\n```"
        result = ToolResult("rich_output_template_tool", "summary", content)
        report = self.verifier.verify_tool_result(0, "rich_output_template_tool", result)
        self.assertTrue(report.passed)

    def test_command_exit_zero_passes(self):
        report = self.verifier.verify_command_result("git status", 0, "On branch main")
        self.assertTrue(report.passed)
        self.assertEqual(report.issues, [])

    def test_command_nonzero_exit_fails(self):
        report = self.verifier.verify_command_result("git log", 1, "fatal: not a git repo")
        self.assertFalse(report.passed)
        self.assertGreater(len(report.issues), 0)

    def test_sandbox_policy_verifier_accepts_consistent_block(self):
        decision = ExecutionSandbox(get_config().workspace_root).decide("rm -rf /")
        report = self.verifier.verify_sandbox_policy(decision)
        self.assertTrue(report.passed)
        self.assertEqual(report.summary, "policy=blocked")

    def test_sandbox_policy_verifier_rejects_inconsistent_allow(self):
        class BadDecision:
            command = "git status"
            allowed = True
            reason = "allowed"
            matched_prefix = None
            blocked_pattern = None

        report = self.verifier.verify_sandbox_policy(BadDecision())
        self.assertFalse(report.passed)
        self.assertIn("matched allowlist prefix", report.summary)

    def test_provider_attempt_verifier_passes_with_successful_fallback(self):
        attempts = [
            {"provider": "openrouter", "ok": False, "duration_ms": 10, "error": "timeout"},
            {"provider": "groq", "ok": True, "duration_ms": 20, "error": None},
        ]
        report = self.verifier.verify_provider_attempts(attempts)
        self.assertTrue(report.passed)
        self.assertIn("provider=groq", report.summary)
        self.assertIn("failed=openrouter", report.summary)

    def test_provider_attempt_verifier_fails_without_success(self):
        attempts = [{"provider": "openrouter", "ok": False, "duration_ms": 10, "error": "timeout"}]
        report = self.verifier.verify_provider_attempts(attempts)
        self.assertFalse(report.passed)
        self.assertIn("all provider attempts failed", report.summary)

    def test_provider_attempt_verifier_fails_when_missing(self):
        report = self.verifier.verify_provider_attempts([])
        self.assertFalse(report.passed)
        self.assertIn("no provider attempts recorded", report.summary)

    def test_verify_all_length_matches(self):
        steps_actions = ["tool_a", "tool_b"]
        results = [
            ToolResult("tool_a", "s", "valid content for tool a"),
            ToolResult("tool_b", "s", "valid content for tool b"),
        ]
        reports = self.verifier.verify_all(steps_actions, results)
        self.assertEqual(len(reports), 2)

    def test_verify_all_empty(self):
        reports = self.verifier.verify_all([], [])
        self.assertEqual(reports, [])

    def test_recovery_action_for_bad_mermaid(self):
        result = ToolResult("rich_output_template_tool", "summary", "plain text")
        report = self.verifier.verify_tool_result(0, "rich_output_template_tool", result)
        recovery = self.verifier.recovery_action("rich_output_template_tool", report)
        self.assertTrue(recovery.should_retry)
        self.assertIn("Mermaid", recovery.prompt_suffix)


class ReactRecoveryTests(unittest.TestCase):
    def test_planner_retries_recoverable_bad_visual_output(self):
        """Verify a failed visual verifier report gets one corrective retry."""

        class FakeRegistry:
            def __init__(self):
                self.calls = 0
                self.tool = OssTool("rich_output_template_tool", "fake", "fake", ("graph",))

            def get_tool(self, name):
                return self.tool

            def run_tool(self, tool, prompt):
                self.calls += 1
                if self.calls == 1:
                    return ToolResult(tool.name, "bad visual", "plain text without a diagram")
                return ToolResult(tool.name, "fixed visual", "```mermaid\ngraph TD\nA --> B\n```")

        registry = FakeRegistry()
        steps, results, reports = ReactPlanner(registry).run("show graph")
        self.assertEqual(registry.calls, 2)
        self.assertEqual(results[0].summary, "fixed visual")
        self.assertEqual(len(reports), 2)
        self.assertTrue(reports[-1].passed)
        self.assertIn("Recovery:", steps[0].observation)

    def test_recovered_trace_uses_final_verifier_report(self):
        """Verify traces show recovered PASS while retaining all reports."""

        class FakeRegistry:
            def __init__(self):
                self.calls = 0
                self.tool = OssTool("rich_output_template_tool", "fake", "fake", ("graph",))

            def get_tool(self, name):
                return self.tool

            def run_tool(self, tool, prompt):
                self.calls += 1
                if self.calls == 1:
                    return ToolResult(tool.name, "bad visual", "plain text without a diagram")
                return ToolResult(tool.name, "fixed visual", "```mermaid\ngraph TD\nA --> B\n```")

        steps, _, reports = ReactPlanner(FakeRegistry()).run("show graph")
        aligned = align_final_verifier_reports(steps, reports)
        trace = format_react_trace(steps, reports)
        self.assertEqual(len(aligned), 1)
        self.assertTrue(aligned[0].passed)
        self.assertIn("Verify: PASS", trace)
        self.assertNotIn("Verify: FAIL", trace)


if __name__ == "__main__":
    unittest.main()
