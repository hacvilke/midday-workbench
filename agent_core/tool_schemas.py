from __future__ import annotations

from .oss_tools import TOOLS


def oss_tool_schemas() -> list[dict[str, object]]:
    schemas: list[dict[str, object]] = []
    for tool in TOOLS:
        schemas.append(
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The user goal or focused search query for this OSS tool.",
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of tool results to return.",
                                "default": 6,
                            },
                        },
                        "required": ["query"],
                    },
                },
            }
        )
    return schemas


def schema_markdown() -> str:
    lines = []
    for schema in oss_tool_schemas():
        function = schema["function"]
        lines.append(f"- `{function['name']}`: {function['description']}")
    return "\n".join(lines)
