"""Shell tool: run a command in the working directory."""

from __future__ import annotations

import subprocess

from lumen.tools.base import Tool

MAX_OUTPUT_CHARS = 30_000


def _run_bash(args: dict) -> str:
    command = args["command"]
    timeout = int(args.get("timeout", 120))
    try:
        proc = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return f"Error: command timed out after {timeout}s"
    except Exception as exc:  # pragma: no cover - defensive
        return f"Error running command: {exc}"

    parts: list[str] = []
    if proc.stdout:
        parts.append(proc.stdout.rstrip("\n"))
    if proc.stderr:
        parts.append(("[stderr]\n" if proc.stdout else "") + proc.stderr.rstrip("\n"))
    parts.append(f"[exit code: {proc.returncode}]")
    result = "\n".join(p for p in parts if p)
    if len(result) > MAX_OUTPUT_CHARS:
        result = result[:MAX_OUTPUT_CHARS] + "\n... (output truncated)"
    return result


TOOLS = [
    Tool(
        name="run_bash",
        description=(
            "Run a shell command in the current working directory and return its "
            "stdout, stderr, and exit code. Use for builds, tests, git, and inspection."
        ),
        parameters={
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "The command to run."},
                "timeout": {
                    "type": "integer",
                    "description": "Timeout in seconds (default 120).",
                },
            },
            "required": ["command"],
        },
        run=_run_bash,
        requires_approval=True,
    ),
]
