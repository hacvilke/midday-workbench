from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def load_dotenv(path: Path | None = None) -> None:
    env_path = path or PROJECT_ROOT / ".env"
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


@dataclass(frozen=True)
class AgentConfig:
    provider: str
    workspace_root: Path
    index_path: Path
    max_tool_rounds: int
    groq_api_key: str
    groq_model: str
    openrouter_api_key: str
    openrouter_model: str
    local_base_url: str
    local_model: str


def get_config() -> AgentConfig:
    load_dotenv()
    workspace_root = Path(os.getenv("AGENT_WORKSPACE_ROOT", ".."))
    if not workspace_root.is_absolute():
        workspace_root = (PROJECT_ROOT / workspace_root).resolve()
    return AgentConfig(
        provider=os.getenv("AGENT_PROVIDER", "offline").lower(),
        workspace_root=workspace_root,
        index_path=PROJECT_ROOT / "data" / "workspace_index.sqlite3",
        max_tool_rounds=int(os.getenv("AGENT_MAX_TOOL_ROUNDS", "4")),
        groq_api_key=os.getenv("GROQ_API_KEY", ""),
        groq_model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
        openrouter_api_key=os.getenv("OPENROUTER_API_KEY", ""),
        openrouter_model=os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct"),
        local_base_url=os.getenv("LOCAL_BASE_URL", "http://127.0.0.1:11434/v1"),
        local_model=os.getenv("LOCAL_MODEL", "llama3.1"),
    )
