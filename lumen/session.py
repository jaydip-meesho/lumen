"""Conversation state and running usage totals."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Session:
    system: str
    messages: list[dict] = field(default_factory=list)
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost: float = 0.0
    id: str = ""
    created: float = 0.0

    def to_api_messages(self) -> list[dict]:
        return [{"role": "system", "content": self.system}] + self.messages

    def add_user(self, content: str) -> None:
        self.messages.append({"role": "user", "content": content})

    def add_usage(self, usage: dict | None) -> None:
        if not usage:
            return
        self.prompt_tokens += int(usage.get("prompt_tokens") or 0)
        self.completion_tokens += int(usage.get("completion_tokens") or 0)
        cost = usage.get("cost")
        if isinstance(cost, (int, float)):
            self.cost += float(cost)

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    def clear(self) -> None:
        self.messages.clear()
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.cost = 0.0

    def restore(self, data: dict) -> None:
        """Reload messages + usage from a saved session dict."""
        self.messages = data.get("messages", [])
        self.prompt_tokens = int(data.get("prompt_tokens") or 0)
        self.completion_tokens = int(data.get("completion_tokens") or 0)
        self.cost = float(data.get("cost") or 0.0)
        if data.get("id"):
            self.id = data["id"]
        if data.get("created"):
            self.created = data["created"]
