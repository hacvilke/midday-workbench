"""Safe file editor for the Midday Workbench agent workspace."""
from __future__ import annotations

import re
from pathlib import Path


_SENSITIVE = (
    ".env",
    "secret",
    "password",
    "credential",
    "token",
    ".key",
    ".pem",
    ".p12",
    ".pfx",
)

_MAX_WRITE_BYTES = 200 * 1024  # 200 KB
_MAX_READ_CHARS = 12_000


class FileEditorTool:
    """Read, write, patch, and create files within the agent workspace.

    All paths are validated to stay inside the workspace root.
    Sensitive-file patterns are blocked on every operation.
    """

    def __init__(self, workspace_root: Path):
        self.root = workspace_root.resolve()

    # ------------------------------------------------------------------
    # Safety helpers
    # ------------------------------------------------------------------

    def _resolve(self, path: str) -> Path:
        target = (self.root / path).resolve()
        try:
            target.relative_to(self.root)
        except ValueError:
            raise ValueError(f"Path escapes workspace: {path!r}")
        lowered = str(target).lower()
        if any(pat in lowered for pat in _SENSITIVE):
            raise ValueError(f"Access to sensitive file is blocked: {path!r}")
        return target

    def _is_sensitive(self, rel: str) -> bool:
        lowered = rel.lower()
        return any(pat in lowered for pat in _SENSITIVE)

    # ------------------------------------------------------------------
    # File operations
    # ------------------------------------------------------------------

    def read_file(self, path: str, max_chars: int = _MAX_READ_CHARS) -> str:
        """Read a workspace file.

        Args:
            path: Relative path from workspace root.
            max_chars: Maximum characters to return.

        Returns:
            File content (truncated if large).

        Raises:
            FileNotFoundError: If the file does not exist.
            ValueError: If path escapes root or is sensitive.
        """
        target = self._resolve(path)
        if not target.exists():
            raise FileNotFoundError(f"File not found: {path}")
        return target.read_text(encoding="utf-8", errors="ignore")[:max_chars]

    def write_file(self, path: str, content: str) -> str:
        """Overwrite or create a file with new content.

        Args:
            path: Relative path from workspace root.
            content: Full new content.

        Returns:
            Human-readable confirmation string.

        Raises:
            ValueError: If path is unsafe or content exceeds the size limit.
        """
        target = self._resolve(path)
        encoded = content.encode("utf-8")
        if len(encoded) > _MAX_WRITE_BYTES:
            raise ValueError(
                f"Content exceeds {_MAX_WRITE_BYTES // 1024} KB write limit "
                f"({len(encoded) // 1024} KB given)"
            )
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        lines = content.count("\n") + 1
        return f"Written {len(encoded):,} bytes ({lines} lines) → {path}"

    def patch_file(self, path: str, search: str, replace: str) -> str:
        """Search-and-replace one occurrence in a file.

        Args:
            path: Relative path from workspace root.
            search: Exact string to find.
            replace: Replacement string.

        Returns:
            Confirmation with char-delta.

        Raises:
            ValueError: If search string not found or path is unsafe.
            FileNotFoundError: If file does not exist.
        """
        content = self.read_file(path, max_chars=_MAX_WRITE_BYTES)
        if search not in content:
            raise ValueError(f"Search string not found in {path!r}")
        new_content = content.replace(search, replace, 1)
        delta = len(new_content) - len(content)
        self.write_file(path, new_content)
        sign = "+" if delta >= 0 else ""
        return f"Patched {path}: replaced 1 occurrence ({sign}{delta} chars)"

    def create_file(self, path: str, content: str = "") -> str:
        """Create a new file (fails if it already exists).

        Args:
            path: Relative path from workspace root.
            content: Initial file content.

        Returns:
            Confirmation string.

        Raises:
            FileExistsError: If file already exists.
            ValueError: If path is unsafe.
        """
        target = self._resolve(path)
        if target.exists():
            raise FileExistsError(f"File already exists: {path}. Use write_file to overwrite.")
        return self.write_file(path, content)

    def delete_file(self, path: str) -> str:
        """Delete a workspace file.

        Args:
            path: Relative path from workspace root.

        Returns:
            Confirmation string.

        Raises:
            FileNotFoundError: If the file does not exist.
            ValueError: If path is unsafe.
        """
        target = self._resolve(path)
        if not target.exists():
            raise FileNotFoundError(f"File not found: {path}")
        target.unlink()
        return f"Deleted {path}"

    def list_files(self, pattern: str = "**/*.py") -> list[str]:
        """List workspace files matching a glob pattern.

        Args:
            pattern: Glob pattern relative to workspace root.

        Returns:
            Sorted list of relative file paths (max 60).
        """
        matches = []
        for p in self.root.glob(pattern):
            if p.is_file():
                rel = str(p.relative_to(self.root))
                if not self._is_sensitive(rel):
                    matches.append(rel)
        return sorted(matches)[:60]

    # ------------------------------------------------------------------
    # Prompt parsing helpers
    # ------------------------------------------------------------------

    def extract_filename_from_prompt(self, prompt: str) -> str | None:
        """Heuristically extract a target filename from a user prompt.

        Args:
            prompt: Raw user prompt.

        Returns:
            Relative file path if detected, otherwise None.
        """
        patterns = [
            r'(?:edit|update|fix|modify|change|refactor|rewrite|write|create|open|read|patch)\s+([\w./-]+\.[\w]+)',
            r'(?:file|path)\s+["\']?([\w./-]+\.[\w]+)["\']?',
            r'([\w./-]+\.(?:py|js|ts|html|css|json|md|yaml|yml|txt|sh|toml|cfg|ini))',
        ]
        for pattern in patterns:
            match = re.search(pattern, prompt, re.IGNORECASE)
            if match:
                candidate = match.group(1)
                if not self._is_sensitive(candidate):
                    return candidate
        return None


def extract_code_block(text: str) -> str | None:
    """Extract the first fenced code block from model output.

    Args:
        text: Model response text.

    Returns:
        Code content without the fence lines, or None if no block found.
    """
    match = re.search(r"```(?:\w+)?\n(.*?)```", text, re.DOTALL)
    if match:
        return match.group(1).rstrip("\n")
    return None
