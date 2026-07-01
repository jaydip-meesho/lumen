"""Provider-facing data types.

A provider's `stream()` yields a sequence of `Delta` objects (streamed text)
followed by exactly one terminal `Completion` (full text + assembled tool
calls + usage). The agent consumes this stream directly.
"""

from __future__ import annotations

from dataclasses import dataclass, field


class ProviderError(RuntimeError):
    """Raised when the model backend returns an error or is unreachable."""


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: str  # raw JSON string as emitted by the model


@dataclass
class Delta:
    """A streamed chunk of assistant text."""

    text: str


@dataclass
class Completion:
    """Terminal event: the fully assembled assistant turn."""

    text: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    finish_reason: str | None = None
    usage: dict = field(default_factory=dict)
