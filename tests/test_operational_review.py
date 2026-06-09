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


if __name__ == "__main__":
    unittest.main()
