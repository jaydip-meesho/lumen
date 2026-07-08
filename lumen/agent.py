"""The agent loop: stream a turn, guard/preview/run tools, repeat.

Adds, on top of the basic loop:
  • Secret Guard  — scan outgoing messages before any cloud request
  • Diff preview  — show what a write/edit will do before it happens
  • Undo          — snapshot files before mutation so /undo can revert
  • Fallback      — fail over to another provider when one is down
  • Turn stats    — time / tokens / cost per turn
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from pathlib import Path

from lumen import airgap, security, ui
from lumen.config import Config
from lumen.diffing import preview_change
from lumen.providers.base import Completion, Delta, ProviderError
from lumen.providers.openai_compat import OpenAICompatProvider
from lumen.session import Session
from lumen.tools.registry import ToolRegistry

MUTATING = ("write_file", "edit_file")


class AbortTurn(Exception):
    """Raised to stop the current turn cleanly (e.g. user cancels a send)."""


class Agent:
    def __init__(
        self,
        provider: OpenAICompatProvider,
        registry: ToolRegistry,
        session: Session,
        config: Config,
        make_provider: Callable[[str], OpenAICompatProvider] | None = None,
    ):
        self.provider = provider
        self.registry = registry
        self.session = session
        self.config = config
        self.make_provider = make_provider
        self.undo_stack: list[tuple[str, str | None, bool]] = []
        self._ack_secrets: set[tuple[str, str]] = set()
        self._redact_mode = False

    # -- public ------------------------------------------------------------
    def run_turn(self, user_input: str) -> None:
        self.session.add_user(user_input)
        t0 = time.monotonic()
        p0, c0, cost0 = self.session.prompt_tokens, self.session.completion_tokens, self.session.cost
        try:
            for _ in range(self.config.max_iterations):
                try:
                    completion = self._stream_assistant()
                except AbortTurn:
                    return
                except ProviderError as exc:
                    ui.error(str(exc))
                    return
                except KeyboardInterrupt:
                    ui.warn("Interrupted.")
                    return

                self.session.messages.append(self._assistant_message(completion))
                self.session.add_usage(completion.usage)

                if not completion.tool_calls:
                    break
                for call in completion.tool_calls:
                    result = self._execute(call)
                    self.session.messages.append(
                        {"role": "tool", "tool_call_id": call.id, "content": result}
                    )
            else:
                ui.warn(f"Stopped after {self.config.max_iterations} tool iterations.")
        finally:
            ui.turn_stats(
                time.monotonic() - t0,
                self.session.prompt_tokens - p0,
                self.session.completion_tokens - c0,
                self.session.cost - cost0,
                self.provider.name,
                self.provider.model,
            )

    def undo(self) -> str | None:
        if not self.undo_stack:
            return None
        path, old, existed = self.undo_stack.pop()
        p = Path(path).expanduser()
        try:
            if not existed:
                if p.exists():
                    p.unlink()
                return f"Reverted: deleted {path} (it was newly created)"
            p.write_text(old or "", encoding="utf-8")
            return f"Reverted {path} to its previous contents"
        except OSError as exc:
            return f"Undo failed for {path}: {exc}"

    # -- streaming + fallback ---------------------------------------------
    def _stream_assistant(self) -> Completion:
        tried: list[str] = []
        while True:
            provider = self.provider
            outgoing = self._guard_outgoing(provider)  # may raise AbortTurn
            try:
                return self._do_stream(provider, outgoing)
            except ProviderError as exc:
                fb = self._fallback(provider, tried)
                if fb is None:
                    raise
                ui.fallback_notice(
                    provider.name, fb.name,
                    leaving_machine=(provider.offline and not fb.offline),
                )
                tried.append(provider.name)
                self.provider = fb  # stick with the working provider
                continue

    def _do_stream(self, provider: OpenAICompatProvider, messages: list[dict]) -> Completion:
        stream = provider.stream(
            messages, tools=self.registry.schemas(), temperature=self.config.temperature
        )
        ui.assistant_start()
        completion: Completion | None = None
        had_text = False
        for event in stream:
            if isinstance(event, Delta):
                ui.assistant_delta(event.text)
                had_text = True
            elif isinstance(event, Completion):
                completion = event
        ui.assistant_end(had_text)
        return completion if completion is not None else Completion(text="")

    def _fallback(self, provider: OpenAICompatProvider, tried: list[str]) -> OpenAICompatProvider | None:
        if not self.config.fallback_enabled or self.make_provider is None:
            return None
        name = self.config.providers.get(provider.name, {}).get("fallback")
        if not name or name == provider.name or name in tried or name not in self.config.providers:
            return None
        # Under airgap, never fall back to a provider that would leave the machine.
        if airgap.is_enabled() and not self.config.providers[name].get("offline"):
            return None
        try:
            return self.make_provider(name)
        except (KeyError, ValueError, ProviderError) as exc:
            ui.warn(f"Fallback provider '{name}' could not be built: {exc}")
            return None

    # -- secret guard ------------------------------------------------------
    def _guard_outgoing(self, provider: OpenAICompatProvider) -> list[dict]:
        msgs = self.session.to_api_messages()
        # Airgap: refuse any non-local provider outright (the socket layer would
        # block it anyway — this is the clean, explained refusal).
        if airgap.is_enabled() and not provider.offline:
            ui.error(
                f"Airgap mode is ON — refusing to contact cloud provider '{provider.name}'. "
                "Nothing left the machine. Switch to a local provider or run /airgap to disable."
            )
            raise AbortTurn()
        if provider.offline or not self.config.secret_guard:
            return msgs  # nothing leaves the machine (or guard disabled)
        hits = security.scan_messages(msgs)
        new = [(w, f) for (w, f) in hits if (f.kind, f.masked) not in self._ack_secrets]
        if not new:
            return security.redact_messages(msgs) if self._redact_mode else msgs
        decision = ui.secret_alert(new, provider.name)
        if decision == "cancel":
            ui.warn("Cancelled — nothing was sent.")
            raise AbortTurn()
        for _, f in new:
            self._ack_secrets.add((f.kind, f.masked))
        if decision == "redact":
            self._redact_mode = True
            return security.redact_messages(msgs)
        return msgs  # send anyway

    # -- tool execution ----------------------------------------------------
    @staticmethod
    def _assistant_message(completion: Completion) -> dict:
        msg: dict = {"role": "assistant", "content": completion.text or None}
        if completion.tool_calls:
            msg["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.name, "arguments": tc.arguments},
                }
                for tc in completion.tool_calls
            ]
        return msg

    def _execute(self, call) -> str:
        try:
            args = json.loads(call.arguments) if call.arguments.strip() else {}
            if not isinstance(args, dict):
                raise ValueError("arguments must be a JSON object")
        except (json.JSONDecodeError, ValueError) as exc:
            return f"Error: could not parse arguments for {call.name}: {exc}"

        ui.tool_call(call.name, args)
        tool = self.registry.get(call.name)
        mutating = call.name in MUTATING

        diff = note = None
        if mutating and self.config.show_diffs:
            diff, note = preview_change(call.name, args)

        if tool is not None and tool.requires_approval and not self.config.auto_approve:
            decision = ui.ask_permission(call.name, args, diff=diff, note=note or "")
            if decision == "always":
                self.config.auto_approve = True
            elif decision == "no":
                return "Denied by user. Do not retry this action; ask how to proceed."
        elif diff:
            ui.render_diff(diff, note or "")  # show the change even when auto-approved

        snap = None
        if mutating and "path" in args:
            p = Path(args["path"]).expanduser()
            existed = p.exists() and p.is_file()
            old = p.read_text(encoding="utf-8", errors="replace") if existed else None
            snap = (str(args["path"]), old, existed)

        result = self.registry.dispatch(call.name, args)
        ui.tool_result(result)

        if snap and not result.startswith("Error"):
            self.undo_stack.append(snap)
        return result
