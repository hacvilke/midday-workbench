from __future__ import annotations

import re
import time
import json
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path

from .config import PROJECT_ROOT


GRAPH_EXTENSIONS = {".py", ".js", ".jl", ".cpp", ".hpp", ".h", ".c", ".cc", ".cu", ".cuh"}
SKIP_DIRS = {".git", "__pycache__", "node_modules", ".venv", "build", "dist", ".mypy_cache", "Midday-Workbench"}
_GRAPH_CACHE: dict[tuple[str, int, int], tuple[float, RepoGraph]] = {}
_CACHE_TTL_SECONDS = 300
GRAPH_CACHE_PATH = PROJECT_ROOT / "data" / "repo_graph_cache.json"


@dataclass(frozen=True)
class GraphEdge:
    source: str
    target: str
    kind: str
    weight: int


@dataclass(frozen=True)
class RepoGraph:
    nodes: list[str]
    edges: list[GraphEdge]
    centrality: list[tuple[str, int]]
    mermaid: str

    def to_dict(self) -> dict[str, object]:
        return {
            "nodes": self.nodes,
            "edges": [asdict(edge) for edge in self.edges],
            "centrality": self.centrality,
            "mermaid": self.mermaid,
        }


def iter_graph_files(root: Path):
    for path in root.rglob("*"):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.is_file() and path.suffix.lower() in GRAPH_EXTENSIONS:
            yield path


def repo_name(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).parts[0]
    except (ValueError, IndexError):
        return root.name


def extract_dependencies(path: Path) -> list[tuple[str, str]]:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return []
    deps: list[tuple[str, str]] = []
    for match in re.finditer(r"^\s*(?:from|import)\s+([A-Za-z_][\w.]*)", text, re.MULTILINE):
        deps.append(("python", match.group(1).split(".")[0]))
    for match in re.finditer(r"^\s*#include\s+[<\"]([^>\"]+)[>\"]", text, re.MULTILINE):
        deps.append(("cpp", match.group(1).split("/")[0]))
    for match in re.finditer(r"^\s*(?:using|import)\s+([A-Za-z_][\w.]*)", text, re.MULTILINE):
        deps.append(("julia", match.group(1).split(".")[0]))
    for match in re.finditer(r"^\s*import\s+.*?\s+from\s+[\"']([^\"']+)[\"']", text, re.MULTILINE):
        deps.append(("javascript", match.group(1).split("/")[0].lstrip(".")))
    return deps


def build_repo_graph(root: Path, limit_files: int = 2500, limit_edges: int = 120) -> RepoGraph:
    cache_key = (str(root.resolve()), limit_files, limit_edges)
    cached = _GRAPH_CACHE.get(cache_key)
    now = time.time()
    if cached and now - cached[0] < _CACHE_TTL_SECONDS:
        return cached[1]
    disk_cached = read_graph_cache(cache_key, now)
    if disk_cached:
        _GRAPH_CACHE[cache_key] = (now, disk_cached)
        return disk_cached
    repo_modules: dict[str, set[str]] = defaultdict(set)
    file_deps: list[tuple[str, str, str]] = []
    for index, path in enumerate(iter_graph_files(root)):
        if index >= limit_files:
            break
        repo = repo_name(root, path)
        stem = path.stem
        repo_modules[repo].add(stem)
        for kind, dep in extract_dependencies(path):
            if dep:
                file_deps.append((repo, dep, kind))

    edge_counts: Counter[tuple[str, str, str]] = Counter()
    repos = set(repo_modules)
    module_to_repo = {}
    for repo, modules in repo_modules.items():
        for module in modules:
            module_to_repo.setdefault(module.lower(), repo)

    for source_repo, dep, kind in file_deps:
        dep_key = dep.lower()
        target_repo = module_to_repo.get(dep_key)
        if not target_repo:
            for repo in repos:
                if dep_key in repo.lower():
                    target_repo = repo
                    break
        if target_repo and target_repo != source_repo:
            edge_counts[(source_repo, target_repo, kind)] += 1

    edges = [
        GraphEdge(source, target, kind, weight)
        for (source, target, kind), weight in edge_counts.most_common(limit_edges)
    ]
    degree = Counter()
    for edge in edges:
        degree[edge.source] += edge.weight
        degree[edge.target] += edge.weight
    nodes = sorted(set(repos) | {edge.source for edge in edges} | {edge.target for edge in edges})
    centrality = degree.most_common(12)
    mermaid = make_mermaid(edges[:30])
    graph = RepoGraph(nodes=nodes, edges=edges, centrality=centrality, mermaid=mermaid)
    _GRAPH_CACHE[cache_key] = (now, graph)
    write_graph_cache(cache_key, now, graph)
    return graph


def read_graph_cache(cache_key: tuple[str, int, int], now: float) -> RepoGraph | None:
    if not GRAPH_CACHE_PATH.exists():
        return None
    try:
        data = json.loads(GRAPH_CACHE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if data.get("cache_key") != list(cache_key):
        return None
    if now - float(data.get("created_at", 0)) > _CACHE_TTL_SECONDS:
        return None
    edges = [GraphEdge(**edge) for edge in data.get("edges", [])]
    centrality = [tuple(item) for item in data.get("centrality", [])]
    return RepoGraph(
        nodes=list(data.get("nodes", [])),
        edges=edges,
        centrality=centrality,
        mermaid=str(data.get("mermaid", "")),
    )


def write_graph_cache(cache_key: tuple[str, int, int], created_at: float, graph: RepoGraph) -> None:
    GRAPH_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "cache_key": list(cache_key),
        "created_at": created_at,
        **graph.to_dict(),
    }
    try:
        GRAPH_CACHE_PATH.write_text(json.dumps(payload), encoding="utf-8")
    except OSError:
        return


def make_mermaid(edges: list[GraphEdge]) -> str:
    if not edges:
        return "flowchart LR\n  Workspace[Workspace]"
    lines = ["flowchart LR"]
    for edge in edges:
        source = safe_node(edge.source)
        target = safe_node(edge.target)
        lines.append(f"  {source}[{edge.source}] -- {edge.kind}:{edge.weight} --> {target}[{edge.target}]")
    return "\n".join(lines)


def safe_node(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_]", "_", value)
    if not cleaned or cleaned[0].isdigit():
        cleaned = f"N_{cleaned}"
    return cleaned
