"""Secret Guard — stop credentials from leaking to a cloud provider.

Before Lumen sends anything to a non-offline backend, it scans the outgoing
messages for things that look like secrets (API keys, private keys, .env
values) and lets the user redact or cancel. In local/offline mode nothing
leaves the machine, so the guard is skipped entirely.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Ordered most-specific first; overlapping matches keep the earlier (specific) hit.
_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("Anthropic API key", re.compile(r"\bsk-ant-[A-Za-z0-9_\-]{20,}")),
    ("OpenRouter API key", re.compile(r"\bsk-or-[A-Za-z0-9_\-]{20,}")),
    ("OpenAI API key", re.compile(r"\bsk-[A-Za-z0-9]{20,}")),
    ("AWS access key id", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("GitHub token", re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{36}\b|\bgithub_pat_[A-Za-z0-9_]{22,}")),
    ("Google API key", re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b")),
    ("Slack token", re.compile(r"\bxox[baprs]-[A-Za-z0-9\-]{10,}")),
    ("Stripe key", re.compile(r"\b[rs]k_(?:live|test)_[A-Za-z0-9]{16,}")),
    ("Private key block", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY-----")),
    ("JWT", re.compile(r"\beyJ[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}")),
    # KEY = value, anywhere on a line (so it survives read_file's line-number prefixes)
    ("Secret assignment", re.compile(
        r"""(?im)\b[A-Z][A-Z0-9_]*(?:SECRET|PASSWORD|PASSWD|TOKEN|API[_-]?KEY|PRIVATE[_-]?KEY|ACCESS[_-]?KEY)[A-Z0-9_]*\s*[:=]\s*['"]?([^\s'"]{6,})""")),
]


@dataclass
class Finding:
    kind: str
    masked: str
    start: int
    end: int


def _mask(s: str) -> str:
    s = s.strip().strip("'\"")
    if len(s) <= 8:
        return "•" * len(s)
    return f"{s[:3]}…{s[-2:]} ({len(s)} chars)"


def scan(text: str) -> list[Finding]:
    """Find secret-looking substrings, non-overlapping, specific patterns first."""
    if not text:
        return []
    found: list[Finding] = []
    taken: list[tuple[int, int]] = []
    for kind, pat in _PATTERNS:
        for m in pat.finditer(text):
            s, e = m.start(), m.end()
            if any(s < te and e > ts for ts, te in taken):
                continue  # overlaps a more-specific earlier match
            taken.append((s, e))
            found.append(Finding(kind=kind, masked=_mask(m.group(0)), start=s, end=e))
    return sorted(found, key=lambda f: f.start)


def redact(text: str) -> str:
    findings = scan(text)
    for f in sorted(findings, key=lambda f: f.start, reverse=True):
        text = text[: f.start] + f"‹redacted {f.kind}›" + text[f.end :]
    return text


def _msg_texts(msg: dict) -> str:
    """All human-readable text carried by one message (content + tool-call args)."""
    parts = []
    c = msg.get("content")
    if isinstance(c, str):
        parts.append(c)
    for tc in msg.get("tool_calls") or []:
        args = (tc.get("function") or {}).get("arguments")
        if isinstance(args, str):
            parts.append(args)
    return "\n".join(parts)


def scan_messages(messages: list[dict]) -> list[tuple[str, Finding]]:
    """Scan an outgoing message list; return (where, finding) pairs."""
    where_of = {"user": "your message", "tool": "a file/command result", "assistant": "the model's reply"}
    hits: list[tuple[str, Finding]] = []
    for msg in messages:
        where = where_of.get(msg.get("role", ""), msg.get("role", "message"))
        for f in scan(_msg_texts(msg)):
            hits.append((where, f))
    return hits


def redact_messages(messages: list[dict]) -> list[dict]:
    """Return a copy of messages with secret substrings redacted."""
    out: list[dict] = []
    for msg in messages:
        m = dict(msg)
        if isinstance(m.get("content"), str):
            m["content"] = redact(m["content"])
        if m.get("tool_calls"):
            new_calls = []
            for tc in m["tool_calls"]:
                tc = dict(tc)
                fn = dict(tc.get("function") or {})
                if isinstance(fn.get("arguments"), str):
                    fn["arguments"] = redact(fn["arguments"])
                tc["function"] = fn
                new_calls.append(tc)
            m["tool_calls"] = new_calls
        out.append(m)
    return out
