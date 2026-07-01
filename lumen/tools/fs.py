"""Filesystem tools: read, write, edit, list."""

from __future__ import annotations

from pathlib import Path

from lumen.tools.base import Tool

MAX_READ_CHARS = 400_000


def _read_file(args: dict) -> str:
    raw = args["path"]
    path = Path(raw).expanduser()
    if not path.exists():
        return f"Error: file not found: {raw}"
    if path.is_dir():
        return f"Error: {raw} is a directory (use list_dir)"
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return f"Error reading {raw}: {exc}"

    lines = text.splitlines()
    offset = args.get("offset")
    limit = args.get("limit")
    if offset or limit:
        start = max((offset or 1) - 1, 0)
        end = start + limit if limit else len(lines)
        chosen = lines[start:end]
        if not chosen:
            return "(no lines in the requested range)"
        return "\n".join(f"{start + i + 1:>6}\t{line}" for i, line in enumerate(chosen))

    numbered = "\n".join(f"{i + 1:>6}\t{line}" for i, line in enumerate(lines))
    if len(numbered) > MAX_READ_CHARS:
        return (
            numbered[:MAX_READ_CHARS]
            + f"\n... (truncated; {len(lines)} lines total — read a range with offset/limit)"
        )
    return numbered or "(empty file)"


def _write_file(args: dict) -> str:
    raw = args["path"]
    path = Path(raw).expanduser()
    content = args.get("content", "")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        existed = path.exists()
        path.write_text(content, encoding="utf-8")
    except OSError as exc:
        return f"Error writing {raw}: {exc}"
    verb = "Overwrote" if existed else "Created"
    return f"{verb} {raw} ({len(content)} bytes, {content.count(chr(10)) + 1} lines)"


def _edit_file(args: dict) -> str:
    raw = args["path"]
    path = Path(raw).expanduser()
    old = args.get("old_string", "")
    new = args.get("new_string", "")
    replace_all = bool(args.get("replace_all", False))
    if not path.exists():
        return f"Error: file not found: {raw}"
    if old == new:
        return "Error: old_string and new_string are identical"
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return f"Error reading {raw}: {exc}"

    count = text.count(old)
    if count == 0:
        return f"Error: old_string not found in {raw}"
    if count > 1 and not replace_all:
        return (
            f"Error: old_string matches {count} places in {raw}. "
            "Add surrounding context to make it unique, or pass replace_all=true."
        )
    updated = text.replace(old, new) if replace_all else text.replace(old, new, 1)
    try:
        path.write_text(updated, encoding="utf-8")
    except OSError as exc:
        return f"Error writing {raw}: {exc}"
    where = f"all {count} occurrences" if replace_all else "1 occurrence"
    return f"Edited {raw} ({where} replaced)"


def _list_dir(args: dict) -> str:
    raw = args.get("path", ".")
    path = Path(raw).expanduser()
    if not path.exists():
        return f"Error: path not found: {raw}"
    if path.is_file():
        return f"{raw} (file, {path.stat().st_size} bytes)"
    try:
        entries = sorted(path.iterdir(), key=lambda e: (e.is_file(), e.name.lower()))
    except OSError as exc:
        return f"Error listing {raw}: {exc}"
    lines = [f"{e.name}/" if e.is_dir() else e.name for e in entries]
    return "\n".join(lines) or "(empty directory)"


TOOLS = [
    Tool(
        name="read_file",
        description=(
            "Read a text file from disk. Returns the content with line numbers. "
            "Use offset/limit to read a slice of a large file."
        ),
        parameters={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to the file."},
                "offset": {
                    "type": "integer",
                    "description": "1-based line to start from (optional).",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max number of lines to read (optional).",
                },
            },
            "required": ["path"],
        },
        run=_read_file,
    ),
    Tool(
        name="write_file",
        description=(
            "Write content to a file, creating parent directories as needed. "
            "Overwrites the file if it exists."
        ),
        parameters={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to write."},
                "content": {"type": "string", "description": "Full file content."},
            },
            "required": ["path", "content"],
        },
        run=_write_file,
        requires_approval=True,
    ),
    Tool(
        name="edit_file",
        description=(
            "Replace an exact string in a file. old_string must match the file "
            "verbatim (including whitespace) and be unique unless replace_all is set."
        ),
        parameters={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to edit."},
                "old_string": {"type": "string", "description": "Exact text to find."},
                "new_string": {"type": "string", "description": "Replacement text."},
                "replace_all": {
                    "type": "boolean",
                    "description": "Replace every occurrence (default false).",
                },
            },
            "required": ["path", "old_string", "new_string"],
        },
        run=_edit_file,
        requires_approval=True,
    ),
    Tool(
        name="list_dir",
        description="List the entries of a directory (directories are suffixed with /).",
        parameters={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Directory path (default: current directory).",
                }
            },
            "required": [],
        },
        run=_list_dir,
    ),
]
