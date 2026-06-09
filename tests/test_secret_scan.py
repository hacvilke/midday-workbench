import tempfile
import unittest
from pathlib import Path

from agent_core.secret_scan import git_tracked_files, scan_text, scan_workspace


class SecretScanTests(unittest.TestCase):
    def test_scan_text_detects_provider_key_patterns(self):
        """Verify configured provider key patterns are detected without printing values."""

        findings = scan_text(
            "sample.txt",
            "openrouter " + "sk-or-v1-" + "example_key\nand groq " + "gsk_" + "example_key",
        )
        self.assertEqual({finding.pattern for finding in findings}, {"openrouter_api_key", "groq_api_key"})
        self.assertEqual(findings[0].path, "sample.txt")

    def test_scan_workspace_skips_data_directory(self):
        """Verify generated database/storage paths are not scanned."""

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "data").mkdir()
            (root / "data" / "memory.txt").write_text("gsk_" + "should_be_skipped", encoding="utf-8")
            (root / "src.py").write_text("print('clean')", encoding="utf-8")
            self.assertEqual(scan_workspace(root), [])

    def test_scan_workspace_reports_relative_path(self):
        """Verify findings use relative paths for safe reporting."""

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "leak.txt").write_text("sk-or-v1-" + "example_key", encoding="utf-8")
            findings = scan_workspace(root)
            self.assertEqual(len(findings), 1)
            self.assertEqual(findings[0].path, "leak.txt")
            self.assertEqual(findings[0].line, 1)

    def test_git_tracked_files_returns_list_for_repo(self):
        """Verify the scanner can use Git-tracked files for speed."""

        files = git_tracked_files(Path(__file__).resolve().parents[1])
        self.assertTrue(any(path.name == "server.py" for path in files))


if __name__ == "__main__":
    unittest.main()
