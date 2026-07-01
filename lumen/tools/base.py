"""Tool definition shared by every tool the agent can call."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict  # JSON Schema for the arguments object
    run: Callable[[dict], str]
    # Tools that mutate the filesystem or run commands ask for approval
    # unless the session is in auto-approve mode.
    requires_approval: bool = False

    def schema(self) -> dict:
        """OpenAI function-tool schema sent to the model."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }
