from __future__ import annotations

import argparse
import re
import sqlite3
from pathlib import Path

from .config import get_config


TEXT_EXTENSIONS = {
    ".c", ".cc", ".cpp", ".cuh", ".cu", ".h", ".hpp", ".jl", ".js", ".json", ".md",
    ".py", ".toml", ".txt", ".yaml", ".yml",
}
SKIP_DIRS = {".git", ".venv", "node_modules", "__pycache__", "dist", "build", ".mypy_cache", "Midday-Workbench"}


def iter_files(root: Path):
    for path in root.rglob("*"):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.is_file() and path.suffix.lower() in TEXT_EXTENSIONS:
            yield path


def chunks(text: str, max_chars: int = 1800):
    paragraphs = re.split(r"\n\s*\n", text)
    current = ""
    for paragraph in paragraphs:
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        if len(current) + len(paragraph) + 2 > max_chars and current:
            yield current
            current = paragraph
        else:
            current = f"{current}\n\n{paragraph}".strip()
    if current:
        yield current


def connect(index_path: Path) -> sqlite3.Connection:
    index_path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(index_path)
    con.execute(
        "CREATE VIRTUAL TABLE IF NOT EXISTS docs USING fts5(path, repo, content, tokenize='porter unicode61')"
    )
    return con


def rebuild(root: Path, index_path: Path) -> int:
    con = connect(index_path)
    con.execute("DELETE FROM docs")
    count = 0
    for file_path in iter_files(root):
        try:
            text = file_path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        repo = file_path.relative_to(root).parts[0] if file_path != root else root.name
        relative = str(file_path.relative_to(root))
        for chunk in chunks(text):
            con.execute("INSERT INTO docs(path, repo, content) VALUES (?, ?, ?)", (relative, repo, chunk))
            count += 1
    con.commit()
    con.close()
    return count


def make_fts_query(query: str) -> str:
    terms = re.findall(r"[A-Za-z0-9_]{3,}", query.lower())
    stop = {
        "the", "and", "for", "with", "that", "this", "use", "using", "agent", "design",
        "make", "build", "from", "into", "your", "you", "are",
    }
    terms = [term for term in terms if term not in stop]
    if not terms:
        return query
    return " OR ".join(dict.fromkeys(terms[:12]))


def search(index_path: Path, query: str, limit: int = 8, repo: str | None = None) -> list[dict[str, str]]:
    con = connect(index_path)
    where = "docs MATCH ?"
    params: list[object] = [make_fts_query(query)]
    if repo:
        where += " AND repo = ?"
        params.append(repo)
    params.append(limit)
    sql = (
        "SELECT path, repo, snippet(docs, 2, '[', ']', ' ... ', 18) AS snip "
        f"FROM docs WHERE {where} ORDER BY bm25(docs) LIMIT ?"
    )
    try:
        rows = con.execute(sql, params).fetchall()
    except sqlite3.OperationalError:
        fallback_params: list[object] = [f"%{query}%", limit]
        fallback_repo = ""
        if repo:
            fallback_repo = "AND repo = ? "
            fallback_params = [f"%{query}%", repo, limit]
        rows = con.execute(
            "SELECT path, repo, substr(content, 1, 500) FROM docs "
            f"WHERE content LIKE ? {fallback_repo}LIMIT ?",
            fallback_params,
        ).fetchall()
    finally:
        con.close()
    return [{"path": path, "repo": repo, "snippet": snip} for path, repo, snip in rows]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rebuild", action="store_true")
    args = parser.parse_args()
    config = get_config()
    if args.rebuild:
        count = rebuild(config.workspace_root, config.index_path)
        print(f"Indexed {count} chunks from {config.workspace_root}")


if __name__ == "__main__":
    main()
