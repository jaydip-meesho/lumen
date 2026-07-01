"""Tool registry: aggregates tools, exposes schemas, and dispatches calls."""

from __future__ import annotations

from lumen.tools import fs, search, shell
from lumen.tools.base import Tool


class ToolRegistry:
    def __init__(self, tools: list[Tool]):
        self.tools: dict[str, Tool] = {t.name: t for t in tools}

    def schemas(self) -> list[dict]:
        return [t.schema() for t in self.tools.values()]

    def get(self, name: str) -> Tool | None:
        return self.tools.get(name)

    def names(self) -> list[str]:
        return list(self.tools)

    def dispatch(self, name: str, args: dict) -> str:
        tool = self.tools.get(name)
        if tool is None:
            return f"Error: unknown tool '{name}'"
        try:
            return tool.run(args)
        except KeyError as exc:
            return f"Error: missing required argument {exc} for {name}"
        except Exception as exc:  # pragma: no cover - defensive
            return f"Error executing {name}: {exc}"


def default_registry() -> ToolRegistry:
    return ToolRegistry(fs.TOOLS + shell.TOOLS + search.TOOLS)
