"""Parse tool calls that a model emitted as plain text.

Not every local model returns OpenAI-style structured `tool_calls`. Many
(Qwen, Hermes, functionary-style templates) emit the call inline as text:

    <tool_call>{"name": "run_bash", "arguments": {"command": "ls"}}</tool_call>

or

    <function=write_file>
    <parameter=path>hi.py</parameter>
    <parameter=content>print("hi")</parameter>
    </function>

When the structured field is empty but the text looks like one of these,
Lumen parses it so the tool still runs.
"""

from __future__ import annotations

import json
import re

from lumen.providers.base import ToolCall

MARKERS = ("<tool_call>", "<function=", "<function_call>")

_FUNC_BLOCK = re.compile(r"<function(?:_call)?=([^>\s]+)>(.*?)</function(?:_call)?>", re.DOTALL)
_PARAM = re.compile(r"<parameter=([^>\s]+)>(.*?)</parameter>", re.DOTALL)
_TOOLCALL_BLOCK = re.compile(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", re.DOTALL)
_FENCED_JSON = re.compile(r"```(?:json|tool_call)?\s*(\{.*?\})\s*```", re.DOTALL)


def has_marker(text: str) -> bool:
    return any(mk in text for mk in MARKERS)


def _mk(name: str, arguments: str, i: int) -> ToolCall:
    return ToolCall(id=f"call_text_{i}", name=name.strip(), arguments=arguments)


def _from_obj(raw: str, i: int) -> ToolCall | None:
    try:
        obj = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(obj, dict):
        return None
    name = obj.get("name") or obj.get("tool") or obj.get("function")
    if not name or not isinstance(name, str):
        return None
    args = obj.get("arguments", obj.get("parameters", {}))
    args_str = args if isinstance(args, str) else json.dumps(args)
    return _mk(name, args_str, i)


def parse(text: str) -> list[ToolCall]:
    """Extract tool calls from assistant text. Returns [] if none look valid."""
    if not text:
        return []
    calls: list[ToolCall] = []

    # Format: <function=NAME><parameter=k>v</parameter>...</function>
    for m in _FUNC_BLOCK.finditer(text):
        args = {pm.group(1).strip(): pm.group(2).strip("\n") for pm in _PARAM.finditer(m.group(2))}
        calls.append(_mk(m.group(1), json.dumps(args), len(calls)))
    if calls:
        return calls

    # Format: <tool_call>{json}</tool_call>  (possibly repeated)
    for m in _TOOLCALL_BLOCK.finditer(text):
        c = _from_obj(m.group(1), len(calls))
        if c:
            calls.append(c)
    if calls:
        return calls

    # Format: fenced ```json {json}```
    for m in _FENCED_JSON.finditer(text):
        c = _from_obj(m.group(1), len(calls))
        if c and c.name:
            calls.append(c)
    if calls:
        return calls

    # Bare single JSON object that names a tool
    t = text.strip()
    if t.startswith("{") and t.endswith("}"):
        c = _from_obj(t, 0)
        if c:
            return [c]
    return []


def strip_markers(text: str) -> str:
    """Return any prose that precedes the first tool-call marker."""
    idxs = [text.find(mk) for mk in MARKERS if mk in text]
    if idxs:
        return text[: min(idxs)].strip()
    # if the whole thing was a bare/fenced JSON call, there's no prose to keep
    if parse(text):
        return ""
    return text.strip()
