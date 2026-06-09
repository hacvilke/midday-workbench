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
        self.assertIn("next_action", review)
        self.assertIn("action_items", review)
        self.assertGreaterEqual(len(review["action_items"]), 1)
        self.assertIn("severity", review["action_items"][0])
        self.assertIn("category", review["action_items"][0])
        self.assertIn("metrics", review)

    def test_operational_review_accepts_precomputed_inputs(self):
        """Verify control-plane callers can avoid duplicate health/metrics probes."""

        health = {"passed": True, "checks": [], "tools": []}
        metrics = {
            "runs": {
                "count": 0,
                "fallback_count": 0,
                "ambiguous_routes": 0,
                "low_confidence_routes": 0,
                "average_duration_ms": 0,
                "providers": {},
                "tools": {},
            },
            "verifier": {"count": 0, "passed": 0, "failed": 0, "pass_rate": None},
            "provider_routes": {"count": 0, "failed": 0, "degraded": 0},
            "commands": {"count": 0, "failures": 0, "successes": 0},
            "usage": {"average_prompt_chars": 0, "average_answer_chars": 0, "average_context_chars": 0},
            "decisions": {"count": 0, "kinds": {}},
        }
        index = {"chunk_count": 1, "repo_count": 1, "age_seconds": 0}
        review = operational_review(health=health, metrics=metrics, index=index)
        self.assertEqual(review["score"], 100)
        self.assertEqual(review["grade"], "excellent")

    def test_empty_index_reduces_score(self):
        """Verify missing repo context is treated as an operational risk."""

        health = {"passed": True, "checks": [], "tools": []}
        metrics = {
            "runs": {
                "count": 0,
                "fallback_count": 0,
                "ambiguous_routes": 0,
                "low_confidence_routes": 0,
                "average_duration_ms": 0,
                "providers": {},
                "tools": {},
            },
            "verifier": {"count": 0, "passed": 0, "failed": 0, "pass_rate": None},
            "provider_routes": {"count": 0, "failed": 0, "degraded": 0},
            "commands": {"count": 0, "failures": 0, "successes": 0},
            "usage": {"average_prompt_chars": 0, "average_answer_chars": 0, "average_context_chars": 0},
            "decisions": {"count": 0, "kinds": {}},
        }
        review = operational_review(health=health, metrics=metrics, index={"chunk_count": 0, "repo_count": 0})
        self.assertLess(review["score"], 100)
        self.assertTrue(any("Search index is empty" in risk for risk in review["risks"]))
        self.assertIn("index", review)

    def test_stale_index_recommends_refresh(self):
        """Verify stale repo context gets a lower-severity warning."""

        health = {"passed": True, "checks": [], "tools": []}
        metrics = {
            "runs": {
                "count": 0,
                "fallback_count": 0,
                "ambiguous_routes": 0,
                "low_confidence_routes": 0,
                "average_duration_ms": 0,
                "providers": {},
                "tools": {},
            },
            "verifier": {"count": 0, "passed": 0, "failed": 0, "pass_rate": None},
            "provider_routes": {"count": 0, "failed": 0, "degraded": 0},
            "commands": {"count": 0, "failures": 0, "successes": 0},
            "usage": {"average_prompt_chars": 0, "average_answer_chars": 0, "average_context_chars": 0},
            "decisions": {"count": 0, "kinds": {}},
        }
        review = operational_review(
            health=health,
            metrics=metrics,
            index={"chunk_count": 10, "repo_count": 1, "age_seconds": 90000},
        )
        self.assertEqual(review["grade"], "excellent")
        self.assertTrue(any("older than 24 hours" in risk for risk in review["risks"]))

    def test_route_uncertainty_reduces_score(self):
        """Verify ambiguous and low-confidence routing is operationally visible."""

        health = {"passed": True, "checks": [], "tools": []}
        metrics = {
            "runs": {
                "count": 2,
                "fallback_count": 0,
                "ambiguous_routes": 1,
                "low_confidence_routes": 1,
                "average_duration_ms": 2,
                "providers": {"local": 2},
                "tools": {},
            },
            "verifier": {"count": 0, "passed": 0, "failed": 0, "pass_rate": None},
            "provider_routes": {"count": 0, "failed": 0, "degraded": 0},
            "commands": {"count": 0, "failures": 0, "successes": 0},
            "usage": {"average_prompt_chars": 0, "average_answer_chars": 0, "average_context_chars": 0},
            "files": {"count": 0, "created": 0, "patched": 0, "written": 0},
            "decisions": {"count": 0, "kinds": {}},
        }
        review = operational_review(
            health=health,
            metrics=metrics,
            index={"chunk_count": 10, "repo_count": 1, "age_seconds": 0},
        )
        self.assertLess(review["score"], 100)
        self.assertTrue(any("ambiguous route" in risk for risk in review["risks"]))
        self.assertTrue(any("low-confidence route" in risk for risk in review["risks"]))

    def test_inspected_route_decisions_reduce_score(self):
        """Verify route-inspector telemetry influences the operational scorecard."""

        health = {"passed": True, "checks": [], "tools": []}
        metrics = {
            "runs": {
                "count": 0,
                "fallback_count": 0,
                "ambiguous_routes": 0,
                "low_confidence_routes": 0,
                "average_duration_ms": 0,
                "providers": {},
                "tools": {},
            },
            "verifier": {"count": 0, "passed": 0, "failed": 0, "pass_rate": None},
            "provider_routes": {"count": 0, "failed": 0, "degraded": 0},
            "route_decisions": {
                "count": 2,
                "ambiguous": 1,
                "low_confidence": 1,
                "intents": {"visualize": 1},
                "tools": {"rich_output_template_tool": 1},
            },
            "quality_history": {"count": 0, "passed": 0, "failed": 0},
            "commands": {"count": 0, "failures": 0, "successes": 0},
            "usage": {"average_prompt_chars": 0, "average_answer_chars": 0, "average_context_chars": 0},
            "files": {"count": 0, "created": 0, "patched": 0, "written": 0},
            "decisions": {"count": 0, "kinds": {}},
            "memory": {"message_count": 0, "has_summary": False, "summary_chars": 0},
            "context_window": {"item_count": 0, "content_chars": 0},
        }
        review = operational_review(
            health=health,
            metrics=metrics,
            index={"chunk_count": 10, "repo_count": 1, "age_seconds": 0},
        )
        self.assertLess(review["score"], 100)
        self.assertTrue(any("inspected route decision" in risk for risk in review["risks"]))

    def test_usage_bloat_reduces_score(self):
        """Verify oversized answers and context become operational risks."""

        health = {"passed": True, "checks": [], "tools": []}
        metrics = {
            "runs": {
                "count": 2,
                "fallback_count": 0,
                "ambiguous_routes": 0,
                "low_confidence_routes": 0,
                "average_duration_ms": 2,
                "providers": {"local": 2},
                "tools": {},
            },
            "verifier": {"count": 0, "passed": 0, "failed": 0, "pass_rate": None},
            "provider_routes": {"count": 0, "failed": 0, "degraded": 0},
            "commands": {"count": 0, "failures": 0, "successes": 0},
            "usage": {
                "average_prompt_chars": 100,
                "average_answer_chars": 7000,
                "average_context_chars": 13000,
            },
            "files": {"count": 0, "created": 0, "patched": 0, "written": 0},
            "decisions": {"count": 0, "kinds": {}},
        }
        review = operational_review(
            health=health,
            metrics=metrics,
            index={"chunk_count": 10, "repo_count": 1, "age_seconds": 0},
        )
        self.assertLess(review["score"], 100)
        self.assertTrue(any("Average answer size is high" in risk for risk in review["risks"]))
        self.assertTrue(any("Average attached context is high" in risk for risk in review["risks"]))

    def test_provider_route_degradation_reduces_score(self):
        """Verify provider fallback chains become actionable scorecard risks."""

        health = {"passed": True, "checks": [], "tools": []}
        metrics = {
            "runs": {
                "count": 2,
                "fallback_count": 0,
                "ambiguous_routes": 0,
                "low_confidence_routes": 0,
                "average_duration_ms": 2,
                "providers": {"offline": 2},
                "tools": {},
            },
            "verifier": {"count": 2, "passed": 2, "failed": 0, "pass_rate": 1.0},
            "provider_routes": {"count": 2, "failed": 0, "degraded": 2},
            "quality_history": {"count": 0, "passed": 0, "failed": 0},
            "commands": {"count": 0, "failures": 0, "successes": 0},
            "usage": {"average_prompt_chars": 0, "average_answer_chars": 0, "average_context_chars": 0},
            "files": {"count": 0, "created": 0, "patched": 0, "written": 0},
            "decisions": {"count": 0, "kinds": {}},
        }
        review = operational_review(
            health=health,
            metrics=metrics,
            index={"chunk_count": 10, "repo_count": 1, "age_seconds": 0},
        )
        self.assertLess(review["score"], 100)
        self.assertTrue(any("provider route(s) used fallback" in risk for risk in review["risks"]))

    def test_quality_history_failures_reduce_score(self):
        """Verify failed quality gates are scored as explicit operational risks."""

        health = {"passed": True, "checks": [], "tools": []}
        metrics = {
            "runs": {
                "count": 0,
                "fallback_count": 0,
                "ambiguous_routes": 0,
                "low_confidence_routes": 0,
                "average_duration_ms": 0,
                "providers": {},
                "tools": {},
            },
            "verifier": {"count": 0, "passed": 0, "failed": 0, "pass_rate": None},
            "provider_routes": {"count": 0, "failed": 0, "degraded": 0},
            "quality_history": {
                "count": 2,
                "passed": 1,
                "failed": 1,
                "latest_failed": {"gate": "frontend_syntax"},
            },
            "commands": {"count": 2, "failures": 0, "successes": 2},
            "usage": {"average_prompt_chars": 0, "average_answer_chars": 0, "average_context_chars": 0},
            "files": {"count": 0, "created": 0, "patched": 0, "written": 0},
            "decisions": {"count": 0, "kinds": {}},
            "memory": {"message_count": 0, "has_summary": False, "summary_chars": 0},
        }
        review = operational_review(
            health=health,
            metrics=metrics,
            index={"chunk_count": 10, "repo_count": 1, "age_seconds": 0},
        )
        self.assertLess(review["score"], 100)
        self.assertTrue(any("quality gate run(s) failed" in risk for risk in review["risks"]))
        self.assertTrue(any("frontend_syntax" in item for item in review["recommendations"]))
        self.assertIn("frontend_syntax", review["next_action"])
        self.assertEqual(review["action_items"][0]["priority"], 1)
        self.assertEqual(review["action_items"][0]["category"], "quality")
        self.assertIn("frontend_syntax", review["action_items"][0]["recommendation"])

    def test_command_failure_recommendation_names_latest_command(self):
        """Verify command failures identify the newest failed command."""

        health = {"passed": True, "checks": [], "tools": []}
        metrics = {
            "runs": {
                "count": 0,
                "fallback_count": 0,
                "ambiguous_routes": 0,
                "low_confidence_routes": 0,
                "average_duration_ms": 0,
                "providers": {},
                "tools": {},
            },
            "verifier": {"count": 0, "passed": 0, "failed": 0, "pass_rate": None},
            "provider_routes": {"count": 0, "failed": 0, "degraded": 0},
            "quality_history": {"count": 0, "passed": 0, "failed": 0},
            "commands": {
                "count": 1,
                "failures": 1,
                "successes": 0,
                "latest_failed": {"command": "python -m unittest missing"},
            },
            "usage": {"average_prompt_chars": 0, "average_answer_chars": 0, "average_context_chars": 0},
            "files": {"count": 0, "created": 0, "patched": 0, "written": 0},
            "decisions": {"count": 0, "kinds": {}},
            "memory": {"message_count": 0, "has_summary": False, "summary_chars": 0},
            "context_window": {"item_count": 0, "content_chars": 0},
        }
        review = operational_review(
            health=health,
            metrics=metrics,
            index={"chunk_count": 10, "repo_count": 1, "age_seconds": 0},
        )
        self.assertLess(review["score"], 100)
        self.assertTrue(any("python -m unittest missing" in item for item in review["recommendations"]))
        self.assertEqual(review["action_items"][0]["category"], "commands")

    def test_context_window_bloat_reduces_score(self):
        """Verify oversized context windows are operationally visible."""

        health = {"passed": True, "checks": [], "tools": []}
        metrics = {
            "runs": {
                "count": 0,
                "fallback_count": 0,
                "ambiguous_routes": 0,
                "low_confidence_routes": 0,
                "average_duration_ms": 0,
                "providers": {},
                "tools": {},
            },
            "verifier": {"count": 0, "passed": 0, "failed": 0, "pass_rate": None},
            "provider_routes": {"count": 0, "failed": 0, "degraded": 0},
            "quality_history": {"count": 0, "passed": 0, "failed": 0},
            "commands": {"count": 0, "failures": 0, "successes": 0},
            "usage": {"average_prompt_chars": 0, "average_answer_chars": 0, "average_context_chars": 0},
            "files": {"count": 0, "created": 0, "patched": 0, "written": 0},
            "decisions": {"count": 0, "kinds": {}},
            "memory": {"message_count": 0, "has_summary": False, "summary_chars": 0},
            "context_window": {"item_count": 13, "content_chars": 21000},
        }
        review = operational_review(
            health=health,
            metrics=metrics,
            index={"chunk_count": 10, "repo_count": 1, "age_seconds": 0},
        )
        self.assertLess(review["score"], 100)
        self.assertTrue(any("Context window" in risk for risk in review["risks"]))

    def test_completion_evidence_review_reduces_score(self):
        """Verify missing or failed completion evidence becomes actionable."""

        health = {"passed": True, "checks": [], "tools": []}
        metrics = {
            "runs": {
                "count": 1,
                "fallback_count": 0,
                "ambiguous_routes": 0,
                "low_confidence_routes": 0,
                "average_duration_ms": 0,
                "providers": {"local": 1},
                "tools": {},
            },
            "verifier": {"count": 0, "passed": 0, "failed": 0, "pass_rate": None},
            "provider_routes": {"count": 0, "failed": 0, "degraded": 0},
            "completion_evidence": {
                "provider_verified": 0,
                "tools_verified": 0,
                "quality_ready": 0,
                "needs_review": 2,
            },
            "quality_history": {"count": 0, "passed": 0, "failed": 0},
            "commands": {"count": 0, "failures": 0, "successes": 0},
            "usage": {"average_prompt_chars": 0, "average_answer_chars": 0, "average_context_chars": 0},
            "files": {"count": 0, "created": 0, "patched": 0, "written": 0},
            "decisions": {"count": 0, "kinds": {}},
            "memory": {"message_count": 0, "has_summary": False, "summary_chars": 0},
            "context_window": {"item_count": 0, "content_chars": 0},
        }
        review = operational_review(
            health=health,
            metrics=metrics,
            index={"chunk_count": 10, "repo_count": 1, "age_seconds": 0},
        )
        self.assertLess(review["score"], 100)
        self.assertTrue(any("completion evidence" in risk for risk in review["risks"]))
        self.assertEqual(review["action_items"][0]["category"], "evidence")


if __name__ == "__main__":
    unittest.main()
