from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SandboxResult:
    command: str
    exit_code: int
    output: str


class ExecutionSandbox:
    """Conservative local sandbox facade.

    This is intentionally narrow today. It gives the agent a stable execution boundary
    that can later be swapped for Docker, a VM, or a remote Replit-style worker.
    """

    READ_ONLY_PREFIXES = (
        "rg",
        "python -m compileall",
        "python -m unittest",
        "python --version",
        "node --version",
        "git status",
        "git diff --stat",
    )

    def allowed_commands(self) -> list[str]:
        """List command prefixes allowed in the sandbox.

        Args:
            None.

        Returns:
            Allowed read-only command prefixes.
        """

        return list(self.READ_ONLY_PREFIXES)

    def __init__(self, workspace_root: Path):
        self.workspace_root = workspace_root

    def run_read_only(self, command: str, timeout: int = 30) -> SandboxResult:
        if not command.startswith(self.READ_ONLY_PREFIXES):
            raise ValueError(f"Command is outside the read-only sandbox policy: {command}")
        completed = subprocess.run(
            command,
            cwd=self.workspace_root,
            shell=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
        )
        return SandboxResult(command, completed.returncode, completed.stdout[:8000])
