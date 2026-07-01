"""Search tools: content search (grep) and filename search (glob).

Uses ripgrep when available for speed; otherwise falls back to pure Python.
"""

from __future__ import annotations

import fnmatch
import os
import re
import shutil
import subprocess
from pathlib import Path

from lumen.tools.base import Tool

MAX_HITS = 200
IGNORE_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build", ".mypy_cache"}


def _search(args: dict) -> str:
    pattern = args["pattern"]
    root = args.get("path", ".")

    if shutil.which("rg"):
        try:
            proc = subprocess.run(
                ["rg", "--line-number", "--no-heading", "--color=never",
                 "--max-count=50", pattern, root],
                capture_output=True,
                text=True,
                timeout=60,
            )
            out = proc.stdout.strip()
            if proc.returncode not in (0, 1):  # 1 == no matches
                err = proc.stderr.strip()
                if err:
                    return f"Error (rg): {err}"
            lines = out.splitlines()
            if len(lines) > MAX_HITS:
                out = "\n".join(lines[:MAX_HITS]) + f"\n... ({len(lines)} matches, truncated)"
            return out or "(no matches)"
        except (subprocess.TimeoutExpired, OSError):
            pass  # fall through to Python

    # Pure-Python fallback
    try:
        regex = re.compile(pattern)
    except re.error as exc:
        return f"Error: invalid regex: {exc}"
    hits: list[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]
        for name in filenames:
            fp = Path(dirpath) / name
            try:
                with fp.open("r", encoding="utf-8", errors="ignore") as fh:
                    for lineno, line in enumerate(fh, 1):
                        if regex.search(line):
                            hits.append(f"{fp}:{lineno}:{line.rstrip()}")
                            if len(hits) >= MAX_HITS:
                                return "\n".join(hits) + "\n... (truncated)"
            except OSError:
                continue
    return "\n".join(hits) or "(no matches)"


def _find_files(args: dict) -> str:
    glob = args["glob"]
    root = Path(args.get("path", ".")).expanduser()
    matches: list[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]
        for name in filenames:
            if fnmatch.fnmatch(name, glob):
                matches.append(str(Path(dirpath) / name))
                if len(matches) >= MAX_HITS:
                    matches.append("... (truncated)")
                    return "\n".join(matches)
    return "\n".join(sorted(matches)) or "(no files matched)"


TOOLS = [
    Tool(
        name="search",
        description=(
            "Search file contents by regular expression across a directory tree "
            "(ripgrep-backed). Returns file:line:match. Prefer this over reading "
            "whole directories."
        ),
        parameters={
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "Regular expression to search for."},
                "path": {"type": "string", "description": "Root directory (default: current)."},
            },
            "required": ["pattern"],
        },
        run=_search,
    ),
    Tool(
        name="find_files",
        description="Find files by name using a glob pattern (e.g. '*.py', 'test_*.go').",
        parameters={
            "type": "object",
            "properties": {
                "glob": {"type": "string", "description": "Filename glob pattern."},
                "path": {"type": "string", "description": "Root directory (default: current)."},
            },
            "required": ["glob"],
        },
        run=_find_files,
    ),
]
