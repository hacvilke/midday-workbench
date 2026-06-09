"""Operational review scoring for Midday Workbench control-plane telemetry."""
from __future__ import annotations

from .config import get_config
from .health import health_report
from .indexer import index_stats
from .run_log import operational_metrics


def operational_review(
    session_id: str | None = None,
    health: dict[str, object] | None = None,
    metrics: dict[str, object] | None = None,
    index: dict[str, object] | None = None,
) -> dict[str, object]:
    """Build a deterministic scorecard from health and runtime telemetry.

    Args:
        session_id: Optional session filter.
        health: Optional precomputed health report.
        metrics: Optional precomputed operational metrics.
        index: Optional precomputed search-index stats.

    Returns:
        JSON-compatible scorecard with risks and recommended next actions.
    """

    health = health or health_report()
    metrics = metrics or operational_metrics(session_id=session_id)
    index = index or index_stats(get_config().index_path)
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
    quality = metrics.get("quality_history", {})
    if quality.get("failed"):
        score -= min(24, int(quality["failed"]) * 6)
        risks.append(f"{quality['failed']} quality gate run(s) failed")
        recommendations.append("Run required gates again after fixes and inspect /api/quality/history for repeated failures.")

    runs = metrics["runs"]
    if runs["fallback_count"]:
        score -= min(15, int(runs["fallback_count"]) * 3)
        risks.append(f"{runs['fallback_count']} provider fallback(s) recorded")
        recommendations.append("Check provider configuration and keep local fallback outputs concise.")
    provider_routes = metrics.get("provider_routes", {})
    if provider_routes.get("failed"):
        score -= min(16, int(provider_routes["failed"]) * 4)
        risks.append(f"{provider_routes['failed']} provider route verifier failure(s)")
        recommendations.append("Inspect provider_route verifier reports and repair provider configuration or fallback order.")
    if provider_routes.get("degraded"):
        score -= min(12, int(provider_routes["degraded"]) * 3)
        risks.append(f"{provider_routes['degraded']} provider route(s) used fallback after failed attempts")
        recommendations.append("Review provider diagnostics for missing keys, unreachable local models, or rate-limited remote providers.")
    if runs.get("ambiguous_routes"):
        score -= min(12, int(runs["ambiguous_routes"]) * 2)
        risks.append(f"{runs['ambiguous_routes']} ambiguous route decision(s) need review")
        recommendations.append("Inspect route alternatives in run details and tighten router keywords for repeated ambiguity.")
    if runs.get("low_confidence_routes"):
        score -= min(18, int(runs["low_confidence_routes"]) * 3)
        risks.append(f"{runs['low_confidence_routes']} low-confidence route decision(s) recorded")
        recommendations.append("Add routing probes or specialized tool schemas for low-confidence request patterns.")
    route_decisions = metrics.get("route_decisions", {})
    inspected_route_review = int(route_decisions.get("ambiguous") or 0) + int(
        route_decisions.get("low_confidence") or 0
    )
    if inspected_route_review:
        score -= min(12, inspected_route_review * 2)
        risks.append(f"{inspected_route_review} inspected route decision(s) need review")
        recommendations.append(
            "Use route inspector history to tune router keywords or tool schemas before those patterns become failed runs."
        )

    usage = metrics.get("usage", {})
    average_answer_chars = int(usage.get("average_answer_chars") or 0)
    average_context_chars = int(usage.get("average_context_chars") or 0)
    if average_answer_chars > 6000:
        score -= 8
        risks.append(f"Average answer size is high ({average_answer_chars} chars)")
        recommendations.append("Tighten response formatting and summarization rules for verbose answer patterns.")
    if average_context_chars > 12000:
        score -= 10
        risks.append(f"Average attached context is high ({average_context_chars} chars)")
        recommendations.append("Reduce retrieval limits or improve context ranking before provider calls.")

    memory = metrics.get("memory", {})
    if int(memory.get("message_count") or 0) > 0 and not memory.get("has_summary"):
        score -= 6
        risks.append("Conversation memory exists without a condensed summary")
        recommendations.append("Run a chat turn or refresh memory summarization so future prompts get compact context.")
    if int(memory.get("summary_chars") or 0) > 1600:
        score -= 6
        risks.append("Condensed memory summary is large")
        recommendations.append("Tighten summary compaction to keep long-running sessions lightweight.")

    context_window = metrics.get("context_window", {})
    if int(context_window.get("item_count") or 0) > 12:
        score -= 6
        risks.append("Context window has many chained tool observations")
        recommendations.append("Clear or prune the context window when tool chaining becomes stale.")
    if int(context_window.get("content_chars") or 0) > 20000:
        score -= 8
        risks.append("Context window content is large")
        recommendations.append("Reduce retained tool-result size or clear stale observations before provider calls.")

    chunk_count = int(index.get("chunk_count") or 0)
    age_seconds = index.get("age_seconds")
    if chunk_count <= 0:
        score -= 25
        risks.append("Search index is empty; repo context retrieval is unavailable")
        recommendations.append("Run `python -m agent_core.indexer --rebuild` before relying on repository answers.")
    elif isinstance(age_seconds, int) and age_seconds > 86400:
        score -= 8
        risks.append("Search index is older than 24 hours")
        recommendations.append("Refresh the search index so repo context reflects current code.")

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
        "index": index,
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
