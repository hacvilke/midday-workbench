"""Operational review scoring for Midday Workbench control-plane telemetry."""
from __future__ import annotations

from .health import health_report
from .run_log import operational_metrics


def operational_review(
    session_id: str | None = None,
    health: dict[str, object] | None = None,
    metrics: dict[str, object] | None = None,
) -> dict[str, object]:
    """Build a deterministic scorecard from health and runtime telemetry.

    Args:
        session_id: Optional session filter.
        health: Optional precomputed health report.
        metrics: Optional precomputed operational metrics.

    Returns:
        JSON-compatible scorecard with risks and recommended next actions.
    """

    health = health or health_report()
    metrics = metrics or operational_metrics(session_id=session_id)
    risks: list[str] = []
    recommendations: list[str] = []
    score = 100

    failed_health = [check for check in health["checks"] if not check.get("passed")]
    if failed_health:
        score -= min(40, len(failed_health) * 8)
        risks.append(f"{len(failed_health)} platform health check(s) failing")
        recommendations.append("Open /api/health and fix failed platform checks before extending automation.")

    failed_tools = [tool for tool in health["tools"] if tool.get("status") != "ok"]
    if failed_tools:
        score -= min(25, len(failed_tools) * 5)
        risks.append(f"{len(failed_tools)} tool health probe(s) failing")
        recommendations.append("Inspect tool health details and repair broken OSS tool adapters.")

    verifier = metrics["verifier"]
    if verifier["count"] and verifier["failed"]:
        score -= min(20, int(verifier["failed"]) * 4)
        risks.append(f"{verifier['failed']} verifier report(s) failed")
        recommendations.append("Review failed verifier reports in run details and improve recovery rules.")

    commands = metrics["commands"]
    if commands["failures"]:
        score -= min(15, int(commands["failures"]) * 3)
        risks.append(f"{commands['failures']} sandbox command run(s) failed")
        recommendations.append("Inspect command history and convert repeated failures into quality gates or fixes.")

    runs = metrics["runs"]
    if runs["fallback_count"]:
        score -= min(15, int(runs["fallback_count"]) * 3)
        risks.append(f"{runs['fallback_count']} provider fallback(s) recorded")
        recommendations.append("Check provider configuration and keep local fallback outputs concise.")

    if not risks:
        risks.append("No immediate operational risks detected")
    if not recommendations:
        recommendations.append("Continue expanding tests, tool coverage, and verifier recovery rules.")

    score = max(0, min(100, score))
    return {
        "session_id": session_id,
        "score": score,
        "grade": _grade(score),
        "risks": risks,
        "recommendations": recommendations,
        "metrics": metrics,
        "health_passed": bool(health["passed"]),
    }


def _grade(score: int) -> str:
    if score >= 90:
        return "excellent"
    if score >= 75:
        return "good"
    if score >= 60:
        return "needs_attention"
    return "unstable"
