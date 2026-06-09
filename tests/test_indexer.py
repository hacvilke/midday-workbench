import tempfile
import unittest
from pathlib import Path

from agent_core.indexer import index_stats, rebuild


class IndexerTests(unittest.TestCase):
    def test_index_stats_reports_chunks_and_repos(self):
        """Verify search index metadata is structured and useful."""

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = root / "sample-repo"
            repo.mkdir()
            (repo / "README.md").write_text("hello repo\n\nthis is searchable context", encoding="utf-8")
            index_path = root / "index.sqlite3"
            count = rebuild(root, index_path)
            stats = index_stats(index_path)
        self.assertGreaterEqual(count, 1)
        self.assertTrue(stats["exists"])
        self.assertGreaterEqual(stats["chunk_count"], 1)
        self.assertEqual(stats["repo_count"], 1)
        self.assertEqual(stats["top_repos"][0]["repo"], "sample-repo")


if __name__ == "__main__":
    unittest.main()
