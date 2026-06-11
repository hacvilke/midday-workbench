"""Specialist skill profiles for Midday Workbench orchestration."""
from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class SkillProfile:
    """A bounded internal specialist profile.

    Args:
        identifier: Stable profile ID.
        role: Human-readable specialist name.
        intent: Router intent this profile primarily supports.
        trigger_hints: Phrases or concepts that suggest this skill.
        permissions: Tool/operation permissions for the profile.
        system_focus: Short instruction focus injected into plans/UI.
        success_criteria: Observable completion condition.

    Returns:
        Immutable JSON-compatible profile through asdict().
    """

    identifier: str
    role: str
    intent: str
    trigger_hints: tuple[str, ...]
    permissions: tuple[str, ...]
    system_focus: str
    success_criteria: str


SKILL_PROFILES: tuple[SkillProfile, ...] = (
    SkillProfile(
        "direct-responder",
        "Direct Responder",
        "plain_chat",
        ("hi", "hello", "thanks", "who are you", "what can you do", "no tools"),
        ("chat",),
        "Answer briefly without tools when the message is conversational or explicitly blocks tools.",
        "No tool/provider call is needed and the response stays concise.",
    ),
    SkillProfile(
        "visual-renderer",
        "Visual Renderer",
        "visualize",
        ("graph", "diagram", "chart", "mermaid", "flowchart", "repo map"),
        ("rich_output_template_tool",),
        "Return a renderable Mermaid-only visual for explicit visual requests.",
        "Exactly one useful visual artifact is produced and passes Mermaid validation.",
    ),
    SkillProfile(
        "code-reviewer",
        "Read-Only Code Reviewer",
        "code_edit",
        ("review", "diff", "risk", "bug", "test", "quality"),
        ("read_file", "list_files", "repo_search", "git_status"),
        "Inspect relevant files and recent changes before mutation or commit decisions.",
        "Findings are grounded in file paths, risk level, and validation gaps.",
    ),
    SkillProfile(
        "implementation-runner",
        "Implementation Runner",
        "code_edit",
        ("edit", "fix", "implement", "refactor", "patch", "write code"),
        ("aider_git_native_tool", "file_write_with_confirmation", "quality_gate"),
        "Make scoped code changes, then run the smallest useful validation command.",
        "Changed files are recorded with verification evidence and no unrelated churn.",
    ),
    SkillProfile(
        "sandbox-operator",
        "Sandbox Operator",
        "command_run",
        ("run tests", "run command", "git status", "pytest", "unittest", "compileall"),
        ("command_runner_tool", "sandbox_readonly", "quality_gate"),
        "Run exactly one allowlisted command and report exit status plus verifier evidence.",
        "The command is policy-allowed, output is captured, and failures are clearly marked.",
    ),
    SkillProfile(
        "research-synthesizer",
        "Research Synthesizer",
        "research",
        ("last 30 days", "latest", "recent trend", "what happened"),
        ("last30days_research_tool", "gitingest_remote_context_tool"),
        "Gather current or external context only when the prompt clearly asks for it.",
        "Summary identifies source type, recency limits, and uncertainty.",
    ),
    SkillProfile(
        "systems-architect",
        "Systems Architect",
        "system_design",
        ("architecture", "scale", "api design", "queues", "caching", "microservice"),
        ("system_design_tool", "repomix_context_pack_tool"),
        "Reason about system boundaries, reliability, data flow, and tradeoffs.",
        "Output includes concrete components, risks, and implementation next steps.",
    ),
    SkillProfile(
        "provider-diagnostician",
        "Provider Diagnostician",
        "provider_health",
        ("offline", "provider", "openrouter", "groq", "api key", "connection refused"),
        ("provider_diagnostics", "health_check"),
        "Explain model-provider readiness without exposing secrets or making unsafe calls.",
        "Advice names the failing provider class and the next safe configuration step.",
    ),
)


def skill_registry() -> list[dict[str, object]]:
    """Return all skill profiles as JSON-compatible dictionaries."""

    return [asdict(profile) for profile in SKILL_PROFILES]


def skills_for_intent(intent: str) -> list[SkillProfile]:
    """Return profiles matching a router intent."""

    return [profile for profile in SKILL_PROFILES if profile.intent == intent]


def best_skill_for_message(intent: str, message: str) -> SkillProfile:
    """Select the best specialist profile for a routed message.

    The selection is deterministic: exact trigger hits win; otherwise the first
    profile registered for the intent is used. Unknown intents fall back to the
    direct responder to avoid unbounded specialist behavior.
    """

    clean = message.lower()
    candidates = skills_for_intent(intent)
    if not candidates and intent == "code_edit":
        candidates = [p for p in SKILL_PROFILES if p.identifier == "implementation-runner"]
    if not candidates:
        return SKILL_PROFILES[0]
    ranked = sorted(
        candidates,
        key=lambda profile: sum(1 for hint in profile.trigger_hints if hint in clean),
        reverse=True,
    )
    return ranked[0]
