"""Safe read-only command sandbox with an explicit allowlist."""
from __future__ import annotations

import subprocess
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SandboxResult:
    command: str
    exit_code: int
    output: str


@dataclass(frozen=True)
class SandboxDecision:
    command: str
    allowed: bool
    reason: str
    matched_prefix: str | None = None
    blocked_pattern: str | None = None
    timeout_seconds: int = 30


class ExecutionSandbox:
    """Conservative local sandbox facade with an explicit command allowlist.

    Only commands whose prefix appears in READ_ONLY_PREFIXES can run.
    This is intentionally narrow — no writes, no network, no privilege ops.
    The sandbox can be swapped for Docker/VM/remote worker in production.
    """

    READ_ONLY_PREFIXES = (
        # Ripgrep search
        "rg",
        # Python introspection
        "python --version",
        "python3 --version",
        "python -m compileall",
        "python -m py_compile",
        "python -m unittest",
        "python -m pytest",
        "python -m agent_core.evals",
        "python -m agent_core.secret_scan",
        "python -c \"import",
        "pytest",
        # Node version check
        "node --version",
        "npm --version",
        "npm test",
        "npm run test",
        "npm run lint",
        "npm run build",
        # Git read-only
        "git status",
        "git diff --stat",
        "git diff --name-only",
        "git diff",
        "git log --oneline",
        "git log --stat",
        "git log",
        "git branch",
        "git show --stat",
        "git show --name-only",
        "git remote -v",
        "git rev-parse",
        # File listing / inspection
        "ls",
        "find . -name",
        "find . -type f",
        "find . -type d",
        "wc -l",
        # Safe echo / version checks
        "echo ",
        "cat ",
        "head ",
        "tail ",
    )

    # Commands that must NOT run even if they match a prefix above.
    # Used as an extra safety net for ambiguous prefixes like "cat ".
    BLOCKED_PATTERNS = (
        ">",      # output redirection
        "&&",     # command chaining
        "||",     # conditional chaining
        ";",      # command separator
        "|",      # pipe to another process
        "`",      # command substitution
        "$(",     # command substitution
        "sudo",   # privilege escalation
        "chmod",  # permission change
        "chown",  # ownership change
        "rm ",    # deletion
        "rmdir",  # directory deletion
        "mv ",    # move/rename
        "cp ",    # copy (could overwrite)
        "dd ",    # disk dump
        "mkfs",   # format filesystem
        "curl",   # network
        "wget",   # network
        "nc ",    # netcat
        "ssh",    # remote shell
        "npm install",
        "npm add",
        "npm publish",
    )

    def __init__(self, workspace_root: Path):
        self.workspace_root = workspace_root

    def allowed_commands(self) -> list[str]:
        """List command prefixes permitted in this sandbox.

        Returns:
            Sorted list of allowed read-only command prefixes.
        """
        return list(self.READ_ONLY_PREFIXES)

    def is_allowed(self, command: str) -> bool:
        """Check whether a command passes the allowlist and blocklist.

        Args:
            command: Raw command string.

        Returns:
            True when the command is safe to run.
        """
        return self.decide(command).allowed

    def decide(self, command: str, timeout: int = 30) -> SandboxDecision:
        """Return a structured sandbox policy decision for a command.

        Args:
            command: Raw command string.
            timeout: Proposed execution timeout in seconds.

        Returns:
            SandboxDecision with allow/block reason and matched policy details.
        """

        stripped = command.strip()
        if not stripped:
            return SandboxDecision(command, False, "empty command", timeout_seconds=timeout)
        blocked_pattern = next((pattern for pattern in self.BLOCKED_PATTERNS if pattern in stripped), None)
        if blocked_pattern is not None:
            matched_prefix = next((prefix for prefix in self.READ_ONLY_PREFIXES if stripped.startswith(prefix)), None)
            return SandboxDecision(
                command,
                False,
                "command contains a blocked shell pattern",
                matched_prefix=matched_prefix,
                blocked_pattern=blocked_pattern,
                timeout_seconds=timeout,
            )
        matched_prefix = next((prefix for prefix in self.READ_ONLY_PREFIXES if stripped.startswith(prefix)), None)
        if matched_prefix is None:
            return SandboxDecision(
                command,
                False,
                "command prefix is not allowlisted",
                timeout_seconds=timeout,
            )
        return SandboxDecision(
            command,
            True,
            "command is allowlisted and passed blocklist checks",
            matched_prefix=matched_prefix,
            timeout_seconds=timeout,
        )

    def run_read_only(self, command: str, timeout: int = 30) -> SandboxResult:
        """Execute an allowlisted command in the workspace.

        Args:
            command: Command string to run.
            timeout: Maximum execution seconds.

        Returns:
            SandboxResult with exit code and truncated output.

        Raises:
            ValueError: If the command is outside the sandbox policy.
        """
        decision = self.decide(command, timeout=timeout)
        if not decision.allowed:
            raise ValueError(
                f"Command blocked by sandbox policy: {decision.reason}. "
                f"Allowed prefixes: {', '.join(self.READ_ONLY_PREFIXES[:6])} ..."
            )
        runnable = self._platform_command(command)
        completed = subprocess.run(
            runnable,
            cwd=self.workspace_root,
            shell=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
        )
        return SandboxResult(command, completed.returncode, completed.stdout[:8000])

    def _platform_command(self, command: str) -> str:
        """Translate portable allowlisted commands to the host shell.

        Args:
            command: Allowlisted command requested by the agent.

        Returns:
            Host-shell command that preserves the requested read-only intent.
        """

        stripped = command.strip()
        if os.name == "nt" and stripped == "ls":
            return "dir /b"
        return command
