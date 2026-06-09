"""Execution policy for autonomous Midday Workbench actions."""
from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class PolicyDecision:
    """Decision for an attempted autonomous action.

    Args:
        action_type: Category of action.
        allowed: Whether the action may run immediately.
        requires_confirmation: Whether user confirmation is needed first.
        reason: Human-readable policy rationale.

    Returns:
        Immutable policy decision for API/UI use.
    """

    action_type: str
    allowed: bool
    requires_confirmation: bool
    reason: str


SAFE_ACTIONS = {
    "chat",
    "route",
    "read_file",
    "list_files",
    "tool_run",
    "quality_gate",
    "sandbox_readonly",
}

CONFIRMATION_ACTIONS = {
    "write_file",
    "patch_file",
    "git_commit",
    "install_dependency",
}

BLOCKED_ACTIONS = {
    "delete_file",
    "destructive_shell",
    "network_upload",
    "expose_secret",
}


def decide(action_type: str) -> PolicyDecision:
    """Decide whether an autonomous action is allowed.

    Args:
        action_type: Action category.

    Returns:
        PolicyDecision describing allowed/confirmation status.
    """

    normalized = action_type.strip().lower()
    if normalized in SAFE_ACTIONS:
        return PolicyDecision(normalized, True, False, "safe local/read-only action")
    if normalized in CONFIRMATION_ACTIONS:
        return PolicyDecision(normalized, False, True, "workspace mutation requires explicit confirmation")
    if normalized in BLOCKED_ACTIONS:
        return PolicyDecision(normalized, False, False, "blocked by safety policy")
    return PolicyDecision(normalized or "unknown", False, True, "unknown action requires confirmation")


def policy_manifest() -> dict[str, object]:
    """Return the execution policy as JSON-compatible metadata.

    Args:
        None.

    Returns:
        Policy categories and example decisions.
    """

    return {
        "safe_actions": sorted(SAFE_ACTIONS),
        "confirmation_actions": sorted(CONFIRMATION_ACTIONS),
        "blocked_actions": sorted(BLOCKED_ACTIONS),
        "examples": [asdict(decide(name)) for name in ("chat", "write_file", "delete_file", "unknown")],
    }
