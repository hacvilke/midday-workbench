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
        "python -c \"import",
        # Node version check
        "node --version",
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
        stripped = command.strip()
        if not stripped.startswith(self.READ_ONLY_PREFIXES):
            return False
        if any(pattern in stripped for pattern in self.BLOCKED_PATTERNS):
            return False
        return True

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
        if not self.is_allowed(command):
            raise ValueError(
                f"Command is outside the read-only sandbox policy: {command!r}. "
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
