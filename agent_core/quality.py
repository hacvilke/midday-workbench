"""Quality gate definitions for Midday Workbench."""
from __future__ import annotations

from dataclasses import asdict, dataclass


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
    QualityGate("unit_tests", "python -m unittest discover tests", "Full test suite passes."),
    QualityGate("evals", "python -m agent_core.evals", "Agent routing, tools, health, memory, and run log evals pass."),
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

    return [asdict(gate) for gate in QUALITY_GATES]


def required_quality_commands() -> list[str]:
    """Return commands for required quality gates.

    Args:
        None.

    Returns:
        Required allowlisted verification commands.
    """

    return [gate.command for gate in QUALITY_GATES if gate.required]
