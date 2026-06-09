"""Quality gate definitions for Midday Workbench."""
from __future__ import annotations

from dataclasses import asdict, dataclass
import time

from .config import PROJECT_ROOT
from .run_log import add_command_run, recent_command_runs
from .sandbox import ExecutionSandbox
from .verifier import ReActVerifier


@dataclass(frozen=True)
class QualityGate:
    """One verification command the workbench knows how to run safely.

    Args:
        name: Stable gate id.
        command: Allowlisted sandbox command.
        purpose: What the gate proves.
        required: Whether the gate is required before shipping a backend change.

    Returns:
        Immutable gate metadata.
    """

    name: str
    command: str
    purpose: str
    required: bool = True


QUALITY_GATES: tuple[QualityGate, ...] = (
    QualityGate("compile", "python -m compileall agent_core", "Python source compiles."),
    QualityGate("frontend_syntax", "node --check web/app.js", "Frontend JavaScript syntax is valid."),
    QualityGate("unit_tests", "python -m unittest discover tests", "Full test suite passes."),
    QualityGate("evals", "python -m agent_core.evals", "Agent routing, tools, health, memory, and run log evals pass."),
    QualityGate("secret_scan", "python -m agent_core.secret_scan", "Configured provider key patterns are absent from the workspace."),
    QualityGate("git_status", "git status --short", "Working tree state is visible."),
    QualityGate("diff_stat", "git diff --stat", "Change size is visible.", required=False),
)


def quality_gate_manifest() -> list[dict[str, object]]:
    """Return JSON-compatible quality gate metadata.

    Args:
        None.

    Returns:
        List of quality gate dictionaries.
    """

    sandbox = ExecutionSandbox(PROJECT_ROOT)
    records = []
    for gate in QUALITY_GATES:
        record = asdict(gate)
        record["policy_decision"] = _policy_decision_payload(sandbox.decide(gate.command, timeout=60))
        records.append(record)
    return records


def required_quality_commands() -> list[str]:
    """Return commands for required quality gates.

    Args:
        None.

    Returns:
        Required allowlisted verification commands.
    """

    return [gate.command for gate in QUALITY_GATES if gate.required]


def run_quality_gates(
    required_only: bool = True,
    dry_run: bool = False,
    session_id: str | None = None,
    gate_names: list[str] | None = None,
) -> dict[str, object]:
    """Run quality gates through the read-only sandbox.

    Args:
        required_only: Whether to run only required gates.
        dry_run: Return allowlist/plan results without executing commands.
        session_id: Optional session id for persisted command audit rows.
        gate_names: Optional gate-name filter.

    Returns:
        JSON-compatible report with per-gate verifier results.
    """

    sandbox = ExecutionSandbox(PROJECT_ROOT)
    verifier = ReActVerifier()
    requested = set(gate_names or [])
    gates = [
        gate
        for gate in QUALITY_GATES
        if (gate.required or not required_only) and (not requested or gate.name in requested)
    ]
    results = []
    started_all = time.perf_counter()
    for gate in gates:
        started = time.perf_counter()
        if dry_run:
            decision = sandbox.decide(gate.command, timeout=60)
            policy_decision = _policy_decision_payload(decision)
            allowed = bool(decision.allowed)
            results.append(
                {
                    "name": gate.name,
                    "command": gate.command,
                    "required": gate.required,
                    "exit_code": None,
                    "output": "",
                    "duration_ms": 0,
                    "policy_decision": policy_decision,
                    "verified": {
                        "passed": allowed,
                        "issues": [] if allowed else ["command is not allowlisted"],
                        "summary": "dry-run allowlisted" if allowed else "dry-run blocked",
                    },
                }
            )
            continue
        try:
            decision = sandbox.decide(gate.command, timeout=60)
            result = sandbox.run_read_only(gate.command, timeout=60)
            report = verifier.verify_command_result(result.command, result.exit_code, result.output)
            verified = {"passed": report.passed, "issues": report.issues, "summary": f"quality:{gate.name} {report.summary}"}
            policy_decision = _policy_decision_payload(decision)
            duration_ms = int((time.perf_counter() - started) * 1000)
            if session_id:
                add_command_run(session_id, result.command, result.exit_code, result.output, verified, duration_ms, policy_decision)
            results.append(
                {
                    "name": gate.name,
                    "command": gate.command,
                    "required": gate.required,
                    "exit_code": result.exit_code,
                    "output": result.output,
                    "duration_ms": duration_ms,
                    "verified": verified,
                    "policy_decision": policy_decision,
                }
            )
        except Exception as exc:
            results.append(
                {
                    "name": gate.name,
                    "command": gate.command,
                    "required": gate.required,
                    "exit_code": None,
                    "output": "",
                    "duration_ms": int((time.perf_counter() - started) * 1000),
                    "verified": {"passed": False, "issues": [str(exc)], "summary": str(exc)},
                }
            )
    passed = all(item["verified"]["passed"] for item in results if item["required"])
    return {
        "passed": passed,
        "required_only": required_only,
        "dry_run": dry_run,
        "gate_names": gate_names or [],
        "duration_ms": int((time.perf_counter() - started_all) * 1000),
        "results": results,
    }


def _policy_decision_payload(decision) -> dict[str, object]:
    return {
        "command": decision.command,
        "allowed": decision.allowed,
        "reason": decision.reason,
        "matched_prefix": decision.matched_prefix,
        "blocked_pattern": decision.blocked_pattern,
        "timeout_seconds": decision.timeout_seconds,
    }


def quality_history(session_id: str | None = None, limit: int = 50) -> dict[str, object]:
    """Summarize persisted quality-gate command runs."""

    rows = []
    passed = 0
    failed = 0
    for command in recent_command_runs(session_id=session_id, limit=limit):
        verified = command.get("verified") or {}
        summary = str(verified.get("summary") or "")
        if not summary.startswith("quality:"):
            continue
        gate = summary.split(" ", 1)[0].removeprefix("quality:")
        ok = bool(verified.get("passed"))
        passed += 1 if ok else 0
        failed += 0 if ok else 1
        rows.append(
            {
                "gate": gate,
                "command": command.get("command"),
                "passed": ok,
                "summary": summary,
                "policy_decision": command.get("policy_decision") or {},
                "duration_ms": command.get("duration_ms"),
                "created_at": command.get("created_at"),
            }
        )
    return {
        "session_id": session_id,
        "count": len(rows),
        "passed": passed,
        "failed": failed,
        "latest_failed": next((row for row in rows if not row["passed"]), None),
        "latest": rows[:10],
    }
