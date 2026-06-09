from __future__ import annotations

import re


MERMAID_STARTERS = ("graph ", "flowchart ", "sequenceDiagram", "mindmap", "classDiagram", "stateDiagram", "xychart-beta")


def extract_mermaid_blocks(markdown: str) -> list[str]:
    """Extract Mermaid code blocks from Markdown.

    Args:
        markdown: Markdown text.

    Returns:
        List of Mermaid source strings.
    """

    return [match.strip() for match in re.findall(r"```mermaid\s*(.*?)```", markdown, re.DOTALL)]


def is_valid_mermaid(source: str) -> bool:
    """Validate basic Mermaid syntax without external rendering.

    Args:
        source: Mermaid source.

    Returns:
        True when source starts with a known Mermaid diagram directive.
    """

    stripped = source.strip()
    return any(stripped.startswith(starter) for starter in MERMAID_STARTERS)


def normalize_mermaid_output(markdown: str) -> str:
    """Ensure Mermaid blocks are clean and renderable by the UI.

    Args:
        markdown: Markdown with optional Mermaid blocks.

    Returns:
        Markdown with valid Mermaid fences preserved and invalid empty fences removed.
    """

    def replace(match: re.Match[str]) -> str:
        source = match.group(1).strip()
        if not is_valid_mermaid(source):
            return source
        return f"```mermaid\n{source}\n```"

    return re.sub(r"```mermaid\s*(.*?)```", replace, markdown, flags=re.DOTALL)


def has_renderable_mermaid(markdown: str) -> bool:
    """Check whether Markdown contains at least one valid Mermaid block.

    Args:
        markdown: Markdown text.

    Returns:
        True when a valid Mermaid block is present.
    """

    return any(is_valid_mermaid(block) for block in extract_mermaid_blocks(markdown))
