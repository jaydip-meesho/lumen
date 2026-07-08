#!/usr/bin/env python3
"""Measure Lumen's per-turn context overhead (system prompt + tool schemas).

Reproduces the "~1,088 tokens" figure in the README. Uses tiktoken (cl100k_base)
if installed for an exact count, otherwise a chars/4 estimate.

    pip install tiktoken        # optional, for the exact number
    python scripts/measure_context.py
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lumen.prompts import system_prompt
from lumen.tools.registry import default_registry

try:
    import tiktoken

    _enc = tiktoken.get_encoding("cl100k_base")

    def count(text: str) -> int:
        return len(_enc.encode(text))

    method = "tiktoken / cl100k_base (exact)"
except Exception:
    def count(text: str) -> int:
        return round(len(text) / 4)

    method = "approx (chars ÷ 4) — `pip install tiktoken` for the exact count"


def main() -> None:
    schemas = default_registry().schemas()
    sp = system_prompt(os.getcwd(), "qwen3-coder:30b", "local")
    sc = json.dumps(schemas)
    sp_t, sc_t = count(sp), count(sc)
    print(f"method:         {method}")
    print(f"system prompt:  {sp_t:>5} tokens")
    print(f"tool schemas:   {sc_t:>5} tokens  ({len(schemas)} tools)")
    print(f"─────────────────────────────")
    print(f"TOTAL / turn:   {sp_t + sc_t:>5} tokens")


if __name__ == "__main__":
    main()
