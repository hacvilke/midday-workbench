"""Self-verifier for ReAct tool and command runs."""
from __future__ import annotations

from dataclasses import dataclass

from .oss_tools import ToolResult
from .rich_output_template_tool.render import extract_mermaid_blocks, is_valid_mermaid


@dataclass(frozen=True)
class VerifierReport:
    """Result of a self-verification step after a tool or command run.

    Args:
        step_index: Zero-based index of the step being verified.
        action: Tool name or command string.
        passed: Whether verification passed.
        issues: List of issue descriptions.
        summary: Human-readable one-line summary.

    Returns:
        Immutable verification result.
    """

    step_index: int
    action: str
    passed: bool
    issues: list[str]
    summary: str


@dataclass(frozen=True)
class RecoveryAction:
    """Bounded self-correction instruction after a verifier failure.

    Args:
        should_retry: Whether the planner should retry the same tool once.
        prompt_suffix: Extra instruction appended to the retry prompt.
        reason: Why this recovery path was chosen.

    Returns:
        Immutable recovery instruction.
    """

    should_retry: bool
    prompt_suffix: str
    reason: str


class ReActVerifier:
    """Post-execution self-verifier for the ReAct loop.

    Checks that tool outputs are non-empty, structurally valid, and
    semantically consistent with the requested tool. For visual tools it
    confirms at least one valid Mermaid block was produced. For command
    runs it checks the exit code and error indicators.
    """

    MIN_CONTENT_LEN = 20

    def verify_tool_result(
        self,
        step_index: int,
        action: str,
        result: ToolResult,
    ) -> VerifierReport:
        """Verify a single tool result after execution.

        Args:
            step_index: Zero-based step index.
            action: Tool name.
            result: ToolResult from the registry.

        Returns:
            VerifierReport with pass/fail status and any issues found.
        """
        issues: list[str] = []

        if not result.content or result.content.strip() in ("", "null", "[]", "{}"):
            issues.append("tool returned empty content")
        elif len(result.content.strip()) < self.MIN_CONTENT_LEN:
            issues.append(f"content suspiciously short ({len(result.content)} chars)")

        if result.name == "rich_output_template_tool":
            blocks = extract_mermaid_blocks(result.content)
            valid_blocks = [b for b in blocks if is_valid_mermaid(b)]
            if not valid_blocks:
                issues.append("no valid Mermaid block found in visual tool output")

        if result.name in ("aider_git_native_tool", "repomix_context_pack_tool"):
            if result.content and len(result.content.strip()) < self.MIN_CONTENT_LEN:
                issues.append("repo tool output is too short to be useful")

        if result.name == "gitingest_remote_context_tool":
            if result.content and "No GitHub URL" in result.content:
                issues.append("no GitHub URL was found in the prompt")

        passed = len(issues) == 0
        summary = "OK" if passed else "; ".join(issues)
        return VerifierReport(step_index, action, passed, issues, summary)

    def verify_command_result(
        self,
        command: str,
        exit_code: int,
        output: str,
    ) -> VerifierReport:
        """Verify a sandbox command result.

        Args:
            command: Command string that was run.
            exit_code: Process exit code.
            output: Combined stdout/stderr text.

        Returns:
            VerifierReport with pass/fail status and issues.
        """
        issues: list[str] = []

        if exit_code != 0:
            issues.append(f"command exited with code {exit_code}")

        lower_output = output.lower()
        if exit_code != 0 and any(word in lower_output for word in ("error", "traceback", "exception", "failed")):
            issues.append("output contains error indicators")

        passed = len(issues) == 0
        summary = f"exit={exit_code}" if passed else "; ".join(issues)
        return VerifierReport(0, command[:60], passed, issues, summary)

    def verify_sandbox_policy(self, decision) -> VerifierReport:
        """Verify a sandbox allow/block decision is internally consistent."""

        issues: list[str] = []
        command = str(getattr(decision, "command", ""))
        allowed = bool(getattr(decision, "allowed", False))
        reason = str(getattr(decision, "reason", ""))
        matched_prefix = getattr(decision, "matched_prefix", None)
        blocked_pattern = getattr(decision, "blocked_pattern", None)

        if not command.strip():
            issues.append("sandbox decision has empty command")
        if not reason:
            issues.append("sandbox decision has no reason")
        if allowed and not matched_prefix:
            issues.append("allowed command has no matched allowlist prefix")
        if allowed and blocked_pattern:
            issues.append("allowed command still has a blocked pattern")

        passed = len(issues) == 0
        summary = "policy=allowed" if passed and allowed else "policy=blocked" if passed else "; ".join(issues)
        return VerifierReport(0, command[:60], passed, issues, summary)

    def verify_provider_attempts(self, attempts: list[dict[str, object]]) -> VerifierReport:
        """Verify provider failover metadata has at least one successful route."""

        issues: list[str] = []
        if not attempts:
            issues.append("no provider attempts recorded")
        ok_attempts = [attempt for attempt in attempts if attempt.get("ok")]
        if attempts and not ok_attempts:
            issues.append("all provider attempts failed")
        failed = [str(attempt.get("provider", "unknown")) for attempt in attempts if not attempt.get("ok")]
        provider = str(ok_attempts[-1].get("provider", "unknown")) if ok_attempts else "none"
        passed = len(issues) == 0
        summary = (
            f"provider={provider}; failed={','.join(failed) if failed else 'none'}"
            if passed
            else "; ".join(issues)
        )
        return VerifierReport(0, "provider_route", passed, issues, summary)

    def verify_all(
        self,
        step_actions: list[str],
        results: list[ToolResult],
    ) -> list[VerifierReport]:
        """Verify all steps in a ReAct run.

        Args:
            step_actions: Ordered list of action/tool names.
            results: Corresponding tool results.

        Returns:
            One VerifierReport per step.
        """
        return [
            self.verify_tool_result(i, action, result)
            for i, (action, result) in enumerate(zip(step_actions, results))
        ]

    def recovery_action(self, action: str, report: VerifierReport) -> RecoveryAction:
        """Decide whether a failed verifier report can be corrected automatically.

        Args:
            action: Tool name that failed verification.
            report: Failed verifier report.

        Returns:
            RecoveryAction describing a bounded retry, or no retry.
        """

        if report.passed:
            return RecoveryAction(False, "", "verification passed")
        joined = " ".join(report.issues).lower()
        if action == "rich_output_template_tool" and "mermaid" in joined:
            return RecoveryAction(
                True,
                "Return exactly one valid Mermaid diagram fence. Use graph TD if no better chart type fits.",
                "visual output can be repaired by tightening the Mermaid format",
            )
        if "empty content" in joined or "suspiciously short" in joined:
            return RecoveryAction(
                True,
                "Return a fuller, structured result with enough concrete detail to be useful.",
                "short or empty output can be retried with a stricter detail requirement",
            )
        return RecoveryAction(False, "", "failure is not safely recoverable with an automatic retry")
