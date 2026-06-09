import unittest

from agent_core.routing_audit import routing_audit


class RoutingAuditTests(unittest.TestCase):
    def test_routing_audit_passes_contract_probes(self):
        """Verify core routing contracts remain green."""

        audit = routing_audit()
        self.assertTrue(audit["passed"])
        self.assertGreaterEqual(audit["probe_count"], 6)
        names = {result["name"] for result in audit["results"]}
        self.assertIn("greeting_fast_path", names)
        self.assertIn("ambiguous_visual_design", names)

    def test_ambiguous_probe_records_alternatives(self):
        """Verify the ambiguity probe exposes ranked route alternatives."""

        audit = routing_audit()
        ambiguous = next(result for result in audit["results"] if result["name"] == "ambiguous_visual_design")
        self.assertGreaterEqual(len(ambiguous["alternatives"]), 2)
        self.assertEqual(ambiguous["alternatives"][0]["intent"], "visualize")


if __name__ == "__main__":
    unittest.main()
