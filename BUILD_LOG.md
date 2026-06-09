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
2026-06-09: [FIX] Fixed streaming fast paths to build planner metadata before greeting/visual responses, with regression tests for streaming plan metadata.
2026-06-09: [UPGRADE] Aligned internal coordinator prompt, package docstring, and CLI description with the Midday Workbench name, with prompt-harness tests for identity/context.
2026-06-09: [UPGRADE] Added a Prompt Harness sidebar panel backed by `/api/prompts`, showing coordinator and sub-agent prompt previews for local control-plane inspection.
2026-06-09: [UPGRADE] Added `/api/control-plane`, an aggregate local endpoint for provider route, tool records, health, metrics, sessions, execution policy, quality gates, and prompt harness names.
2026-06-09: [UPGRADE] Added deterministic delegation planning with manager/executor/verifier/reviewer assignments, plan metadata integration, `/api/delegation`, control-plane manifest exposure, health checks, tests, and route-inspector UI preview.
2026-06-09: [UPGRADE] Added single-run detail lookup with `get_run(run_id)` and `/api/runs/{run_id}` so plan/delegation/verifier metadata can be inspected directly by UI and external agents.
2026-06-09: [UPGRADE] Added Recent Runs UI detail inspection: run rows are clickable/keyboard accessible and fetch `/api/runs/{run_id}` to show intent, tool, provider, delegation, and verifier summary.
2026-06-09: [UPGRADE] Added ReAct context-window observability with snapshot/clear helpers, `/api/context-window`, `/api/context-window/clear`, control-plane inclusion, tests, and a sidebar panel for inspecting chained tool observations.
2026-06-09: [UPGRADE] Added operational review scoring with risks/recommendations, `/api/operational-review`, control-plane inclusion, tests, and an Execution sidebar scorecard.
2026-06-09: [HARDENING] Optimized `/api/control-plane` to reuse precomputed health and metrics when building the operational review, avoiding duplicate tool-health probes as the control plane grows.
2026-06-09: [UPGRADE] Added batch quality-gate execution with `run_quality_gates`, `/api/quality/run`, dry-run preview mode, verifier-backed per-gate results, API/unit tests, and a Command Runner button for required gates.
2026-06-09: [UPGRADE] Quality gate runs now support `gate_names` filtering and persist non-dry-run command audit rows with `quality:<gate>` verifier summaries when a session id is provided.
2026-06-09: [UPGRADE] Added unified activity timeline aggregation for runs, commands, and decisions with `/api/timeline`, control-plane inclusion, tests, and an Activity sidebar panel.
2026-06-09: [UPGRADE] Added route alternative metadata across routing, planning, and route diagnostics so Midday Workbench can audit why a tool was selected over other matching candidates.
2026-06-09: [UI] Exposed route alternatives in chat run metadata, run-detail inspection, and the Route Inspector so operators can see ranked routing candidates without leaving the workbench.
2026-06-09: [UPGRADE] Added routing contract audits with `/api/routing-audit`, health/control-plane inclusion, sidebar status, and tests for greeting, visual, graph, code, system-design, and ambiguous route probes.
2026-06-09: [HARDENING] Normalized the ReAct loop and aligned formatted traces to the final verifier report after automatic recovery retries, so recovered tool runs display PASS while preserving all verifier reports.
2026-06-09: [HARDENING] Added structured sandbox command decisions with allow/block reasons, matched prefixes, blocked patterns, timeout metadata, API exposure, command-run responses, UI display, and regression tests.
2026-06-09: [UPGRADE] Persisted sandbox policy decisions with command-run history and quality-gate audits, including SQLite migration, API history exposure, UI command-history display, and regression tests.
2026-06-09: [HARDENING] Added provider streaming metadata so streamed runs retain provider attempts, fallback state, selected provider, and errors across provider failover.
2026-06-09: [UPGRADE] Injected live operational guardrails into provider system prompts, including routing audit status, sandbox allowlist/blocklist summaries, and explicit verification expectations.
2026-06-09: [UPGRADE] Added search-index observability with index stats, `/api/index`, control-plane inclusion, health coverage, sidebar display, and tests for repo-context readiness.
2026-06-09: [UPGRADE] Added search-index readiness scoring to operational review, including empty/stale index risks, rebuild recommendations, precomputed index reuse, and API tests.
2026-06-09: [HARDENING] Made JSON responses tolerate aborted/reset clients so long-running control-plane probes do not leave noisy server exceptions or flaky API tests.
2026-06-09: [UPGRADE] Added structured file-write audit metadata with bytes, lines, sha256, created/overwritten status, API exposure, UI display, and regression tests.
2026-06-09: [HARDENING] Added lightweight health mode for `/api/control-plane` so the control plane remains responsive while `/api/health` keeps full per-tool probes.
2026-06-09: [UPGRADE] Added persistent file mutation events with SQLite audit storage, `/api/files/events`, timeline and metrics integration, session-aware UI writes, and regression tests.
2026-06-09: [UPGRADE] Added planner confidence and ambiguity metadata to persisted run plans, run-detail UI, streaming metadata, and regression tests.
2026-06-09: [UPGRADE] Added route-uncertainty operational scoring with ambiguous/low-confidence route metrics, control-plane risks, UI counters, and regression tests.
2026-06-09: [UPGRADE] Added route-confidence policy to provider operational guardrails so ambiguous or low-confidence plans stay one-tool, assumption-aware, and verifier-driven.
2026-06-09: [UPGRADE] Added automatic agent file-write audit metadata with persisted run `file_writes`, chat API propagation, file-event mirroring, run-detail UI display, and regression tests.
2026-06-09: [HARDENING] Added sandbox policy verification and persisted blocked-command audit rows so denied command attempts keep verifier summaries, policy details, and command history.
2026-06-09: [HARDENING] Added built-in secret scanning with Groq/OpenRouter key pattern detection, a required quality gate, sandbox allowlisting, health coverage, and regression tests.
2026-06-09: [UPGRADE] Added run usage telemetry with prompt, answer, context, tool-result, and history character counts persisted in run logs, exposed through APIs, summarized in metrics, and displayed in the UI.
2026-06-09: [UPGRADE] Added usage-bloat operational scoring for oversized answers and attached context, plus expanded sidebar review display and regression coverage.
2026-06-09: [UPGRADE] Added audit-log retention maintenance with row-count telemetry, prune APIs, metrics/UI visibility, SQLite vacuuming, and regression tests for newest-row retention.
2026-06-09: [UPGRADE] Added safe provider diagnostics with provider route readiness, redacted provider metadata, status/control-plane API exposure, UI display, health coverage, and regression tests.
2026-06-09: [UPGRADE] Added delegation concurrency planning with serial ordering, safe parallel-candidate grouping, blocked parallel rationale, API exposure, route-inspector UI display, and tests.
2026-06-09: [UPGRADE] Added provider readiness and parallel-candidate policy to the live prompt guardrails so model calls receive current routing, sandbox, concurrency, and verification constraints.
2026-06-09: [UPGRADE] Added provider-route verification reports for model failover metadata so streamed and non-streamed runs explicitly record provider success, fallback failures, or missing attempt data.
2026-06-09: [UPGRADE] Added a provider diagnostics panel to the sidebar showing selected provider, provider kind, configured state, model names, and fallback route readiness without exposing secrets.
2026-06-09: [UPGRADE] Added provider-route degradation telemetry to operational metrics and scorecard risks so fallback chains are tracked separately from generic verifier failures.
2026-06-09: [UPGRADE] Surfaced provider-route degradation counts in the sidebar metrics panel so operator telemetry matches the new backend scorecard.
2026-06-09: [UPGRADE] Added memory telemetry with message counts, session counts, summary readiness, scorecard risks for missing/large summaries, metrics API exposure, sidebar display, and tests.
2026-06-09: [UPGRADE] Added raw memory pruning with summary preservation, `/api/memory/prune`, and regression tests so long-running sessions can compact transcript rows without losing durable memory.
2026-06-09: [HARDENING] Cached deterministic routing audits behind mutation-safe copies to reduce repeated control-plane, health, and prompt-guardrail work while preserving API behavior.
2026-06-09: [UPGRADE] Added quality gate history summaries with persisted quality-command extraction, `/api/quality/history`, pass/fail counts, latest gate metadata, and regression tests.
2026-06-09: [UPGRADE] Surfaced quality gate history in the command runner panel with pass/fail counts, latest gate summaries, refresh after gate runs, and UI regression coverage.
2026-06-09: [UPGRADE] Added quality gate history metrics and operational scorecard penalties so failed verification gates are visible as first-class shipping risks in APIs and the sidebar.
2026-06-09: [UPGRADE] Added persisted run concurrency-plan display in run details so serial order and safe parallel candidate groups remain auditable after execution.
2026-06-09: [UPGRADE] Added redacted provider diagnostics to health reports and API tests so provider route readiness is observable from `/api/health` without exposing secrets.
2026-06-09: [UPGRADE] Added context-window telemetry with item counts, retained content size, tool distribution, metrics/sidebar exposure, scorecard bloat risks, and regression tests.
2026-06-09: [UPGRADE] Added context-window pruning with newest-item retention, `/api/context-window/prune`, sidebar prune control, metrics refresh, and regression tests.
2026-06-09: [UPGRADE] Added route-decision telemetry with intent/tool breakdowns, ambiguous and low-confidence inspected-route counts, metrics API exposure, sidebar counter, and regression tests.
2026-06-09: [HARDENING] Added `light=1` control-plane mode that keeps core health, metrics, scorecard, policy, routing, and provider state while skipping heavier history payloads for faster probes.
2026-06-09: [UPGRADE] Added operational scorecard penalties for inspected route-decision ambiguity and low confidence so route-inspector telemetry influences system quality before full agent runs.
2026-06-09: [UPGRADE] Expanded the recent decision UI with route confidence, selected tool, review flags, and alternative summaries so inspected routes are visible from the workbench sidebar.
2026-06-09: [UPGRADE] Added a canonical route-decision summary API with top intents/tools and review-worthy examples, then surfaced the summary in the decision sidebar.
2026-06-09: [UPGRADE] Marked ambiguous or low-confidence route decisions as review events in the activity timeline so routing drift is visible in operator history.
2026-06-09: [UPGRADE] Injected compact route-decision drift telemetry into provider prompt guardrails so live model calls receive current routing health context.
2026-06-09: [UPGRADE] Expanded the safe command sandbox with common project health commands and clearer blocked-pattern diagnostics for install/network/destructive command attempts.
2026-06-09: [UPGRADE] Added route-decision summary telemetry to the control-plane API, including light mode, so operators can fetch route drift with the rest of system state.
2026-06-09: [UPGRADE] Added live sandbox policy preview in the command runner so typed commands show allow/block status before execution.
2026-06-09: [DOCS] Updated README API and safety sections with control-plane, route-decision summary, quality history, timeline, and command sandbox preview features.
2026-06-09: [HARDENING] Increased API smoke-test timeouts through a named constant so heavy control-plane tests remain stable during parallel verification.
2026-06-09: [UPGRADE] Added a required frontend syntax quality gate using `node --check web/app.js` with sandbox allowlist coverage for JavaScript verification.
2026-06-09: [UPGRADE] Added a named frontend syntax health check so `/api/health` exposes JavaScript quality-gate readiness separately from generic gate allowlisting.
2026-06-09: [UPGRADE] Added health badge hover details for failed platform checks, frontend syntax readiness, and failed tool probes in the sidebar.
2026-06-09: [UPGRADE] Added `latest_failed` quality-history telemetry and surfaced the newest failed gate in the command-runner history panel.
2026-06-09: [UPGRADE] Updated operational review recommendations to name the latest failed quality gate when quality-history telemetry includes it.
2026-06-09: [UPGRADE] Added `next_action` to operational review payloads and updated the sidebar scorecard to display the top recommended action directly.
2026-06-09: [UPGRADE] Added structured operational-review action items with priority, severity, risk, and recommendation fields for planner/UI consumers.
2026-06-09: [UPGRADE] Added latest failed quality-gate telemetry to operational metrics and injected compact quality-action status into provider prompt guardrails.
2026-06-09: [HARDENING] Added structured sandbox policy decisions to quality-gate dry runs so planned verification commands explain allow/block status before execution.
2026-06-09: [UPGRADE] Added sandbox policy decisions to quality gate manifests and surfaced them as command-runner gate tooltips.
2026-06-09: [UPGRADE] Added sandbox policy decisions to quality-history rows and displayed policy summaries for persisted quality gate runs in the UI.
2026-06-09: [UPGRADE] Added sandbox policy details to operational metrics latest-failed quality gate telemetry for consistent quality audit payloads.
2026-06-09: [UPGRADE] Promoted persisted quality-gate command runs to first-class `quality` activity timeline events with gate names and sandbox policy details.
2026-06-09: [UPGRADE] Added latest failed command telemetry to operational metrics and named the failed command in operational-review recommendations.
2026-06-09: [UPGRADE] Surfaced command failure counts in the sidebar metrics panel with a latest-failed-command tooltip for faster operator triage.
2026-06-09: [UPGRADE] Injected command-failure telemetry into provider prompt guardrails so model calls receive current failed-command context alongside quality status.
