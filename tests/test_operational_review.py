"""Operational review tests for Midday Workbench."""

import unittest

from agent_core.operational_review import operational_review


class OperationalReviewTests(unittest.TestCase):
    def test_operational_review_shape(self):
        """Verify operational review produces a bounded scorecard."""

        review = operational_review(session_id="missing-review-session")
        self.assertGreaterEqual(review["score"], 0)
        self.assertLessEqual(review["score"], 100)
        self.assertIn(review["grade"], {"excellent", "good", "needs_attention", "unstable"})
        self.assertIn("risks", review)
        self.assertIn("recommendations", review)
        self.assertIn("metrics", review)

    def test_operational_review_accepts_precomputed_inputs(self):
        """Verify control-plane callers can avoid duplicate health/metrics probes."""

        health = {"passed": True, "checks": [], "tools": []}
        metrics = {
            "runs": {"count": 0, "fallback_count": 0, "average_duration_ms": 0, "providers": {}, "tools": {}},
            "verifier": {"count": 0, "passed": 0, "failed": 0, "pass_rate": None},
            "commands": {"count": 0, "failures": 0, "successes": 0},
            "decisions": {"count": 0, "kinds": {}},
        }
        review = operational_review(health=health, metrics=metrics)
        self.assertEqual(review["score"], 100)
        self.assertEqual(review["grade"], "excellent")


if __name__ == "__main__":
    unittest.main()
