"""Local secret-pattern scanner for Midday Workbench quality gates."""
from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from .config import PROJECT_ROOT


SECRET_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("openrouter_api_key", re.compile(r"sk-or-v1-[A-Za-z0-9_-]+")),
    ("groq_api_key", re.compile(r"gsk_[A-Za-z0-9_-]+")),
)

SKIP_DIRS = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    "node_modules",
    "data",
}

SKIP_SUFFIXES = {
    ".pyc",
    ".sqlite",
    ".sqlite3",
    ".db",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".ico",
}


@dataclass(frozen=True)
class SecretFinding:
    path: str
    line: int
    pattern: str


def scan_text(path: str, text: str) -> list[SecretFinding]:
    """Scan text and return redacted secret findings."""

    findings: list[SecretFinding] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        for name, pattern in SECRET_PATTERNS:
            if pattern.search(line):
                findings.append(SecretFinding(path, line_no, name))
    return findings


def iter_files(root: Path) -> list[Path]:
    """Return candidate text files under root."""

    tracked = git_tracked_files(root)
    if tracked:
        return tracked

    files: list[Path] = []
    for path in root.rglob("*"):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.is_file() and path.suffix.lower() not in SKIP_SUFFIXES:
            files.append(path)
    return files


def git_tracked_files(root: Path) -> list[Path]:
    """Return Git-tracked files when root is a repository."""

    try:
        completed = subprocess.run(
            ["git", "ls-files"],
            cwd=root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=10,
        )
    except Exception:
        return []
    if completed.returncode != 0:
        return []
    files = []
    for line in completed.stdout.splitlines():
        path = root / line
        if path.is_file() and path.suffix.lower() not in SKIP_SUFFIXES:
            files.append(path)
    return files


def scan_workspace(root: Path = PROJECT_ROOT) -> list[SecretFinding]:
    """Scan workspace files for configured secret patterns."""

    findings: list[SecretFinding] = []
    for path in iter_files(root):
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        rel = path.relative_to(root).as_posix()
        findings.extend(scan_text(rel, text))
    return findings


def main() -> int:
    findings = scan_workspace()
    if not findings:
        print("secret_scan: OK no configured secret patterns found")
        return 0
    print(f"secret_scan: FAIL {len(findings)} finding(s)")
    for finding in findings[:50]:
        print(f"{finding.path}:{finding.line}: {finding.pattern}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
