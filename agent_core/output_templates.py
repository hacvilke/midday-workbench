from __future__ import annotations


REPOSITORY_MAP_TEMPLATE = """# Repository Map

## Core Repositories

| Repository | Purpose |
|------------|---------|
| ai-agent-oss | Agent framework |
| cugraph-main | GPU graph analytics |
| erpnext-develop | Business workflows |
| julia-master | Julia language runtime |
| last30days-skill-main | Research synthesis |
| system-design-primer-master | Architecture knowledge |

### Directory Tree

```text
workspace/
├── ai-agent-oss/
├── cugraph-main/
├── erpnext-develop/
├── julia-master/
├── last30days-skill-main/
└── system-design-primer-master/
```
"""


MERMAID_ARCHITECTURE_TEMPLATE = """```mermaid
graph TD
User[User] --> Agent[AI Agent]
Agent --> ERP[ERPNext Tool]
Agent --> Julia[Julia Tool]
Agent --> Graph[cuGraph Tool]
Agent --> Research[Research Tool]
Agent --> Git[Aider Tool]
Graph --> Analytics[Graph Analytics]
Julia --> Compiler[Compiler Tasks]
Research --> Reports[Research Reports]
```
"""


DEPENDENCY_GRAPH_TEMPLATE = """```mermaid
flowchart LR
Agent[AI Agent]
Agent --> ERPNext
Agent --> Julia
Agent --> CuGraph
Agent --> Aider
Agent --> Research
Julia --> LibGit2
Julia --> Runtime
Julia --> Compiler
CuGraph --> Traversal
CuGraph --> Centrality
CuGraph --> Ranking
```
"""


ENERGY_GRAPH_TEMPLATE = """```mermaid
xychart-beta
    title "Potential Energy vs Kinetic Energy"
    x-axis "System progress" [0, 1, 2, 3, 4, 5]
    y-axis "Energy" 0 --> 100
    line "Potential Energy" [100, 80, 60, 40, 20, 0]
    line "Kinetic Energy" [0, 20, 40, 60, 80, 100]
```
"""


MIND_MAP_TEMPLATE = """```mermaid
mindmap
  root((AI Agent))
    Business
      ERPNext
      Accounting
      Inventory
      Manufacturing
    Programming
      Julia
      Runtime
      Compiler
    Graphs
      CuGraph
      Centrality
      Traversal
    Git
      Aider
      Repo Editing
    Research
      Last30Days
      Summaries
      Comparisons
```
"""


SYSTEM_ARCHITECTURE_TEMPLATE = """```text
┌─────────────────┐
│      User       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│    AI Agent     │
└───┬─────┬─────┬─┘
    │     │     │
    ▼     ▼     ▼
┌───────┐ ┌───────┐ ┌─────────┐
│ Julia │ │ ERP   │ │ CuGraph │
└───┬───┘ └───┬───┘ └────┬────┘
    │         │          │
    ▼         ▼          ▼
Compiler  Accounting  Analytics
Runtime   Inventory   Traversal
```
"""


DASHBOARD_TEMPLATE = """# AI Agent Dashboard

## Summary

| Metric | Value |
|--------|-------|
| Active Tools | 9 |
| Repositories | 6 |
| Languages | Python, Julia, C++, JavaScript |
| Agent Provider | OpenRouter |
| Framework | ReAct |

## Tool Status

| Tool | Status |
|------|--------|
| ERPNext | Active |
| Julia | Active |
| cuGraph | Active |
| Aider-style Repo Map | Active |
| Repomix-style Context Pack | Active |
| GitIngest-style Ingestion | Active |
| Research | Active |
| System Design | Active |
| Rich Output Templates | Active |
"""


COLLAPSIBLE_TEMPLATE = """<details>
<summary>Repository Details</summary>

### julia-master

- Runtime
- Compiler
- LibGit2

### cugraph-main

- Traversal
- Centrality
- Ranking

</details>
"""


KANBAN_TEMPLATE = """| Todo | In Progress | Done |
|------|-------------|------|
| Add Memory | Repo Analysis | Tool Discovery |
| Add Charts | Graph Engine | Repo Map |
| Add UI Cards | Dashboard | Documentation |
"""


SEQUENCE_TEMPLATE = """```mermaid
sequenceDiagram
User->>Agent: Request repo map
Agent->>Git Tool: Scan repository
Git Tool-->>Agent: File structure
Agent->>Graph Tool: Build dependency graph
Graph Tool-->>Agent: Relationships
Agent-->>User: Rich markdown report
```
"""


REPORT_TEMPLATE = """# Project Analysis Report

## Overview

This workspace contains multiple repositories focused on:

- AI agents
- Graph analytics
- Business automation
- System design

## Repository Relationships

```mermaid
graph LR
AIAgent --> ERPNext
AIAgent --> Julia
AIAgent --> CuGraph
AIAgent --> Research
Julia --> Compiler
Julia --> Runtime
CuGraph --> Analytics
Research --> Reports
```

## Findings

> The workspace is centered around an AI orchestration layer integrating business automation, graph analytics, and software engineering tools.

## Recommendations

- Add repository dependency tracking
- Generate automated architecture diagrams
- Add semantic code indexing
- Create searchable knowledge graph

## Health Score

```text
Architecture   ██████████ 100%
Documentation ████████░░ 80%
Testing       ███████░░░ 70%
Automation    █████████░ 90%
```
"""


TEMPLATES = {
    "repository_map": REPOSITORY_MAP_TEMPLATE,
    "mermaid_architecture": MERMAID_ARCHITECTURE_TEMPLATE,
    "dependency_graph": DEPENDENCY_GRAPH_TEMPLATE,
    "energy_graph": ENERGY_GRAPH_TEMPLATE,
    "mind_map": MIND_MAP_TEMPLATE,
    "system_architecture": SYSTEM_ARCHITECTURE_TEMPLATE,
    "dashboard": DASHBOARD_TEMPLATE,
    "collapsible": COLLAPSIBLE_TEMPLATE,
    "kanban": KANBAN_TEMPLATE,
    "sequence": SEQUENCE_TEMPLATE,
    "analysis_report": REPORT_TEMPLATE,
}


def template_manifest() -> str:
    return "\n".join(f"- {name}" for name in TEMPLATES)


def template_registry() -> dict[str, str]:
    return TEMPLATES
