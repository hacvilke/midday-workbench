# Tool Policy

The agent starts with conservative tools.

## Enabled

- `workspace_map`: list top-level workspace folders.
- `search_workspace`: search the SQLite FTS index.
- `read_file`: read files inside the workspace root.
- `shell`: run explicitly allowlisted read-only commands.
- `erpnext_business_tool`: focused ERPNext workflow/code search for business answers.
- `julia_language_tool`: focused Julia language/runtime search for technical answers.
- `cugraph_graph_tool`: focused cuGraph graph/dependency search.
- `system_design_tool`: focused architecture and scaling search.
- `aider_git_native_tool`: compact repository map generation.
- `repomix_context_pack_tool`: selected safe file packing with XML-style boundaries.
- `gitingest_remote_context_tool`: public GitHub URL ingestion planning.
- `last30days_research_tool`: research synthesis and comparison-writing patterns from the local skill repo.

## JSON Tool Definitions

Tool schemas live in `agent_core/tool_schemas.py`. Each active OSS tool is exposed as an OpenAI-style function definition with `query` and `limit` parameters.

## ReAct Loop

The deterministic planner in `agent_core/react_loop.py` runs:

1. Thought: choose the matching OSS tool.
2. Action: execute the tool through `agent_core.oss_tools`.
3. Observation: summarize the tool result for the model.

## Prompt Templates

Prompt templates live in `agent_core/prompt_harness.py`:

- Coordinator system prompt
- Generic sub-agent template
- Read-only research sub-agent
- Implementation sub-agent

The live coordinator prompt appends dynamic environment context on each call.

## Shell Allowlist

Current prefixes:

- `rg`
- `python -m`
- `python --version`
- `node --version`
- `git status`

Broaden this only after adding approval, audit logging, and command risk classification.

## Secrets

Never commit provider keys. Load keys from `.env` or the OS environment.
