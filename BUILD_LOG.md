2026-06-09: [PHASE 2] Streaming SSE responses, file write/create/edit tools, DuckDuckGo web search, UI polish (streaming cursor, file editor panel, Ctrl+Enter, bold/italic markdown). max_tokens 900→4096. Tools 9→11.
2026-06-08: Added intent routing, ReAct context chaining, session_state persistence, Mermaid normalization/render targets, and structured per-tool health.
2026-06-08: Verified visual graph routing uses rich templates, cuGraph is reserved for graph analytics, and health now reports per-tool structured JSON.
2026-06-09: Added persistent run log storage, run-log API endpoints, and a Recent Runs UI panel for auditability.
2026-06-09: Fixed visual graph fast paths so graph requests skip provider/repo retrieval, added a potential-vs-kinetic energy Mermaid chart, and added UI SVG fallback rendering for Mermaid xy charts.
2026-06-09: [UPGRADE] Added manager/planner/verifier orchestration — ReactPlanner now plays Planner, IntentRouter plays Manager, new ReActVerifier plays Verifier. Each ReAct step gets THOUGHT/ACTION/OBSERVATION/VERIFY output in traces.
2026-06-09: [UPGRADE] Expanded sandbox allowlist: added python -m pytest, git log, git diff, git branch, ls, cat, find, wc, echo, head, tail, python -m py_compile. Added BLOCKED_PATTERNS guard (pipe, redirect, sudo, rm, curl, etc.) so prefix matches cannot be abused.
2026-06-09: [UPGRADE] Added verifier_reports field to AgentRun; persisted in run_log.sqlite3 (with ALTER TABLE migration for existing DBs); returned in /api/chat response and stored per run.
2026-06-09: [UPGRADE] Added GET /api/sessions endpoint — returns unique session IDs with run counts and last-active timestamps from the run log.
2026-06-09: [UPGRADE] /api/sandbox/run now runs ReActVerifier on every command result and returns a verified block with passed/issues/summary.
2026-06-09: [UPGRADE] Renamed UI branding from "OSS Agent Workbench" to "Midday Workbench" in index.html, agent.py direct_answer, and server.py startup message.
2026-06-09: [UPGRADE] Added self-verifier indicator to the sidebar Execution panel (always On).
2026-06-09: [UPGRADE] Added Mermaid CDN error listener fallback in index.html for offline/CSP environments.
2026-06-09: [UPGRADE] Added tests/test_tools.py (OssToolRegistry, Sandbox, Verifier integration tests) and tests/test_api.py (HTTP smoke tests for all API endpoints).
2026-06-09: [UPGRADE] Migrated Replit's Midday Workbench source into the main repo, fixed Windows sandbox portability, added structured manager/planner artifacts to every run, persisted plans in SQLite, exposed plan/verifier metadata in the API/UI, and excluded the Replit wrapper from graph/index scans.
2026-06-09: [UPGRADE] Added persistent sandbox command history with `/api/commands`, `/api/commands/clear`, command verifier payloads, command duration tracking, UI recent-command display, and run-log tests for command auditability.
2026-06-09: [UPGRADE] Added bounded verifier-driven recovery: failed recoverable tool outputs can receive one corrective retry with stricter instructions, with both reports retained for audit traces.
2026-06-09: [UPGRADE] Added deterministic session memory condensation with SQLite `session_summaries`, `/api/memory` summary payloads, prompt injection of condensed memory, and tests for summary update/clear behavior.
2026-06-09: [UPGRADE] Added quality gate definitions and `/api/quality`, with compile/test/eval/git checks exposed to the UI as clickable safe sandbox commands.
2026-06-09: [UPGRADE] Added `/api/route` routing diagnostics, fixed URL query decoding, and added a UI route inspector for checking tool selection without running a full agent turn.
2026-06-09: [UPGRADE] Added execution policy decisions and `/api/policy`; file write/patch API calls now require explicit confirmation, and agent-side file write post-processing refuses to mutate files unless the prompt includes `confirmed write`.
2026-06-09: [UPGRADE] Expanded platform health to 23 checks by adding execution policy, policy manifest, and quality-gate sandbox allowlist validation.
2026-06-09: [UPGRADE] Added persistent decision audit logging for route and policy decisions with `/api/decisions`, `/api/decisions/clear`, API tests, and a UI recent-decisions panel.
2026-06-09: [UPGRADE] Added operational metrics aggregation with `/api/metrics`, run/command/decision/verifier summaries, API/run-log tests, and a sidebar metrics panel that refreshes after agent, command, and route activity.
2026-06-09: [UPGRADE] Added a Sessions sidebar panel backed by `/api/sessions`, showing current and recent work contexts with run counts and last-active timestamps.
