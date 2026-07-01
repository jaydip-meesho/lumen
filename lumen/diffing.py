"""Compute a unified diff for a pending file change, without writing it.

Used to show the user exactly what a write_file / edit_file call will do
*before* they approve it.
"""

from __future__ import annotations

import difflib
from pathlib import Path


def unified(old: str, new: str, path: str) -> str:
    lines = difflib.unified_diff(
        old.splitlines(),
        new.splitlines(),
        fromfile=f"a/{path}",
        tofile=f"b/{path}",
        lineterm="",
    )
    return "\n".join(lines)


def preview_change(name: str, args: dict) -> tuple[str | None, str]:
    """Return (diff_text, note) for a mutating tool call, computing the
    would-be result without touching disk. diff_text is None when there's
    nothing meaningful to show."""
    raw = args.get("path")
    if not raw:
        return None, ""
    p = Path(raw).expanduser()
    old = ""
    if p.exists() and p.is_file():
        try:
            old = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return None, ""

    if name == "write_file":
        new = args.get("content", "")
        label = "new file" if not p.exists() else "overwrite"
    elif name == "edit_file":
        if not p.exists():
            return None, "file not found — edit will fail"
        old_s = args.get("old_string", "")
        new_s = args.get("new_string", "")
        count = old.count(old_s)
        if count == 0:
            return None, "old_string not found — edit will fail"
        if count > 1 and not args.get("replace_all"):
            return None, f"old_string matches {count} places — edit will fail (needs replace_all)"
        new = old.replace(old_s, new_s) if args.get("replace_all") else old.replace(old_s, new_s, 1)
        label = "edit"
    else:
        return None, ""

    diff = unified(old, new, raw)
    if not diff:
        return None, "no textual change"
    return diff, label
