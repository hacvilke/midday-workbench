# Architecture

## Goal

Build a local-first AI agent that can use the open-source code already present in the workspace as knowledge, tools, and design inspiration.

## Layers

- Interface: CLI and local browser UI.
- Orchestrator: `agent_core.agent.Agent` assembles the system prompt, retrieved context, workspace map, and provider call.
- Prompt harness: `agent_core.prompt_harness` builds the coordinator prompt, injects dynamic environment context, and stores sub-agent templates.
- Rich output templates: `agent_core.output_templates` provides Markdown and Mermaid report formats for dashboards, maps, diagrams, and project reports.
- Providers: `agent_core.providers` supports Groq, OpenRouter, local OpenAI-compatible endpoints, and offline mode.
- Retrieval: `agent_core.indexer` creates a SQLite FTS5 index from local OSS repos.
- Execution sandbox: `agent_core.sandbox.ExecutionSandbox` runs only allowlisted read-only commands today and can later be swapped for Docker or a remote isolated worker.
- Tool definitions: `agent_core.tool_schemas` exposes JSON function schemas for every active OSS tool.
- ReAct loop: `agent_core.react_loop.ReactPlanner` creates Thought -> Action -> Observation traces before the model writes the final answer.
- Base tools: `agent_core.tools` exposes workspace map, search, file read, and a conservative shell policy.
- Active OSS tools: `agent_core.oss_tools` selects repo-specific tools and produces tool results before the model answers.
- Git-native coding: use Aider as the design reference for repository maps, controlled file edits, review diffs, and optional commits.
- Remote/context ingestion: use Gitingest and Repomix patterns for URL-to-context ingestion, prompt-ready repo packs, explicit file boundaries, and secret filtering.

## OSS Roles

- ERPNext: business process schemas and enterprise workflow examples.
- Julia: language/runtime/compiler corpus and technical-computing patterns.
- cuGraph: graph reasoning concepts for dependency maps, relationship ranking, and future GPU acceleration.
- System Design Primer: architecture reasoning and reliability patterns.
- Aider: autonomous coding loop, repo-map compression, Git-aware edits, and commit hygiene.
- Gitingest: remote public repo ingestion into a single prompt-ready Markdown artifact.
- Repomix: structured repo packing with clear file tags and security checks.
- Last30days Skill: research synthesis and comparison-writing patterns already present in the workspace.

## Tool-Using Agent Process

1. Execution sandbox: OSS tools run behind a narrow boundary. The current local sandbox allows read-only commands only; Docker isolation is the next production step.
2. Tool definition: every OSS capability is represented as a JSON function schema so the model can know the tool name, purpose, and expected arguments.
3. ReAct loop: the orchestrator selects tools, records Thought -> Action -> Observation, and gives those observations to the model for the final answer.

## Prompt Harness

The coordinator prompt follows the Claude Code/Replit-style anatomy:

- Role and identity
- Core workflow principles
- Tool usage constraints
- Active JSON tool schemas
- Dynamic current environment context

The API exposes prompt templates at `/api/prompts`:

- `coordinator`
- `sub_agent_template`
- `read_only_research`
- `implementation`

Sub-agents are scoped by mandate, allowed tools, forbidden tools, context isolation, no nesting, and structured return format.

## Framework Targets

- LangGraph: production-grade stateful/cyclic agent graphs.
- CrewAI: multi-agent task assignment with tool ownership.
- LlamaIndex Workflows: retrieval-heavy event-driven routing.

The local implementation stays dependency-light for now, but its modules are shaped so any of those frameworks can replace the simple planner later.

## Enterprise Roadmap

1. Add streaming chat responses.
2. Add durable conversation memory in SQLite.
3. Add structured tool calling JSON protocol.
4. Add repo graph builder using import/reference edges.
5. Add permissioned write tools with review diffs.
6. Add model router with cost, latency, and capability preferences.
7. Add evaluation harness for retrieval quality and tool safety.
8. Add background workers for indexing, long tasks, and scheduled audits.
9. Add Aider-style repository map generation.
10. Add Repomix-style packed context export with secret filters.
11. Add Gitingest-style GitHub URL ingestion for public repos.
