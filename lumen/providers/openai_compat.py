"""An OpenAI-compatible chat provider.

Drives any endpoint that implements POST /chat/completions with streaming and
tool calling: OpenRouter (cloud, BYO key) and local servers alike — Ollama,
LM Studio, llama.cpp, vLLM. The only differences are the base URL, the key,
and a few provider-specific extras carried in the config.
"""

from __future__ import annotations

import json
from collections.abc import Iterator

import httpx

from lumen import toolcall_parse
from lumen.providers.base import Completion, Delta, ProviderError, ToolCall


class OpenAICompatProvider:
    def __init__(
        self,
        name: str,
        base_url: str,
        model: str,
        api_key: str | None = None,
        extra_headers: dict | None = None,
        extra_body: dict | None = None,
        offline: bool = False,
        timeout: float = 600.0,
    ):
        self.name = name
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.extra_headers = extra_headers or {}
        self.extra_body = extra_body or {}
        self.offline = offline
        self.timeout = timeout

    # -- internals ---------------------------------------------------------
    def _headers(self) -> dict:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        headers.update(self.extra_headers)
        return headers

    # -- chat --------------------------------------------------------------
    def stream(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        temperature: float = 0.0,
    ) -> Iterator[Delta | Completion]:
        payload: dict = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "temperature": temperature,
            "stream_options": {"include_usage": True},
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        payload.update(self.extra_body)

        text_parts: list[str] = []
        # tool calls arrive as deltas keyed by index; assemble them here.
        partial: dict[int, dict] = {}
        finish_reason: str | None = None
        usage: dict = {}
        muted = False  # stop echoing text once it turns into a text-format tool call

        try:
            with httpx.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers=self._headers(),
                json=payload,
                timeout=self.timeout,
            ) as response:
                if response.status_code >= 400:
                    body = response.read().decode("utf-8", "replace")
                    raise ProviderError(
                        f"{self.name} returned HTTP {response.status_code}: {body[:800]}"
                    )
                for line in response.iter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    data = line[len("data:"):].strip()
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                    except json.JSONDecodeError:
                        continue

                    if chunk.get("usage"):
                        usage = chunk["usage"]

                    choices = chunk.get("choices") or []
                    if not choices:
                        continue
                    choice = choices[0]
                    delta = choice.get("delta") or {}

                    content = delta.get("content")
                    if content:
                        text_parts.append(content)
                        if not muted and toolcall_parse.has_marker("".join(text_parts)):
                            muted = True  # a text-format tool call is starting
                        if not muted:
                            yield Delta(content)

                    for tc in delta.get("tool_calls") or []:
                        idx = tc.get("index", 0)
                        slot = partial.setdefault(
                            idx, {"id": None, "name": "", "arguments": ""}
                        )
                        if tc.get("id"):
                            slot["id"] = tc["id"]
                        fn = tc.get("function") or {}
                        if fn.get("name"):
                            slot["name"] += fn["name"]
                        if fn.get("arguments"):
                            slot["arguments"] += fn["arguments"]

                    if choice.get("finish_reason"):
                        finish_reason = choice["finish_reason"]
        except httpx.HTTPError as exc:
            hint = ""
            if self.offline:
                hint = (
                    "  (Is your local server running? "
                    "e.g. `ollama serve` on http://localhost:11434)"
                )
            raise ProviderError(f"Could not reach {self.name}: {exc}{hint}") from exc

        tool_calls = [
            ToolCall(
                id=slot["id"] or f"call_{idx}",
                name=slot["name"],
                arguments=slot["arguments"] or "{}",
            )
            for idx, slot in sorted(partial.items())
            if slot["name"]
        ]

        full_text = "".join(text_parts)
        # Fallback: model emitted the call as text instead of structured tool_calls.
        if not tool_calls:
            parsed = toolcall_parse.parse(full_text)
            if parsed:
                tool_calls = parsed
                full_text = toolcall_parse.strip_markers(full_text)

        yield Completion(
            text=full_text,
            tool_calls=tool_calls,
            finish_reason=finish_reason,
            usage=usage,
        )

    # -- catalogue ---------------------------------------------------------
    def list_models(self) -> list[dict]:
        """Return the backend's model catalogue (OpenAI /models shape)."""
        from lumen import airgap
        if airgap.is_enabled() and not self.offline:
            raise ProviderError(
                f"Airgap is ON — refusing to reach {self.name} for the model list. "
                "Nothing left the machine."
            )
        try:
            response = httpx.get(
                f"{self.base_url}/models",
                headers=self._headers(),
                timeout=30.0,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise ProviderError(f"Could not list models from {self.name}: {exc}") from exc
        return response.json().get("data", [])
