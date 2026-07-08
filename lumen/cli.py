"""Command-line entry point and interactive REPL."""

from __future__ import annotations

import argparse
import os
import re
import sys
import time
from pathlib import Path

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory

from lumen import __version__, airgap, persistence, ui
from lumen.ui.console import console
from lumen.agent import Agent
from lumen.config import CONFIG_DIR, HISTORY_PATH, Config
from lumen.prompts import system_prompt
from lumen.providers.base import ProviderError
from lumen.providers.openai_compat import OpenAICompatProvider
from lumen.session import Session
from lumen.tools.registry import default_registry

PROJECT_FILES = ("LUMEN.md", ".lumen/LUMEN.md", "AGENTS.md")
MAX_CONTEXT_CHARS = 8000
MAX_MENTION_CHARS = 20_000

INIT_PROMPT = (
    "Explore this repository using your tools (list_dir, read key files, search) and then "
    "write a concise LUMEN.md at the repo root. Capture: what this project is, how to build / "
    "test / run it, the directory layout, and any conventions an AI coding agent should follow. "
    "Keep it under ~50 lines. Create it with write_file."
)

HELP = """[bold]commands[/bold]
  /help                 show this help
  /model <id>           switch model for the current provider
  /models <filter>      list the provider's model catalogue
  /provider <name>      switch provider (local | openrouter | ...)
  /providers            list configured providers
  /init                 explore the repo and generate a LUMEN.md
  /undo                 revert the last file change Lumen made
  /sessions             list saved sessions (resume with: lumen --resume <id>)
  /auto                 toggle auto-approve (skip permission prompts)
  /guard                toggle the Secret Guard on/off
  /airgap               toggle airgap mode (hard-block all network egress)
  /tools                list available tools
  /cost                 show token usage this session
  /clear                clear the conversation history
  /save                 persist current provider/model/settings to config
  /exit, /quit          leave Lumen  (or press Ctrl-D)
"""


# --- provider wiring -----------------------------------------------------
def build_provider(cfg: Config, name: str | None = None) -> OpenAICompatProvider:
    name = name or cfg.provider
    prov = cfg.providers[name]
    key = cfg.resolve_api_key(name)
    if not prov.get("offline") and not key:
        env = prov.get("api_key_env")
        ui.warn(
            f"No API key for provider '{name}'. "
            f"Set {env} in your environment or run `lumen config set-key {name} <key>`."
        )
    return OpenAICompatProvider(
        name=name,
        base_url=prov["base_url"],
        model=prov["model"],
        api_key=key,
        extra_headers=prov.get("extra_headers"),
        extra_body=prov.get("extra_body"),
        offline=bool(prov.get("offline")),
    )


def load_project_context(cwd: str) -> tuple[str, str]:
    for rel in PROJECT_FILES:
        p = Path(cwd) / rel
        if p.exists() and p.is_file():
            try:
                text = p.read_text(encoding="utf-8", errors="replace")[:MAX_CONTEXT_CHARS]
                return text, rel
            except OSError:
                continue
    return "", ""


def make_agent(cfg: Config, resume: dict | None = None) -> Agent:
    provider = build_provider(cfg)
    registry = default_registry()
    ctx, src = load_project_context(os.getcwd())
    system = system_prompt(os.getcwd(), provider.model, cfg.provider, ctx, src)
    session = Session(system=system, id=persistence.new_id(), created=time.time())
    if resume:
        session.restore(resume)
    if not session.id:
        session.id = persistence.new_id()
    if not session.created:
        session.created = time.time()
    agent = Agent(provider, registry, session, cfg, make_provider=lambda n: build_provider(cfg, n))
    if ctx:
        ui.info(f"Loaded project context from {src}.")
    return agent


def expand_mentions(text: str) -> str:
    """Inline the contents of any @path that points to a real file."""
    added = []
    for token in re.findall(r"(?<!\S)@(\S+)", text):
        p = Path(token).expanduser()
        if p.exists() and p.is_file():
            try:
                body = p.read_text(encoding="utf-8", errors="replace")[:MAX_MENTION_CHARS]
                added.append(f"\n\n--- contents of {token} ---\n{body}\n--- end {token} ---")
            except OSError:
                pass
    return text + "".join(added)


# --- slash commands ------------------------------------------------------
def handle_slash(line: str, agent: Agent, cfg: Config) -> bool:
    parts = line.strip().split(maxsplit=1)
    cmd = parts[0].lower()
    arg = parts[1].strip() if len(parts) > 1 else ""

    if cmd in ("/exit", "/quit"):
        return False

    if cmd == "/help":
        console.print(HELP)

    elif cmd == "/model":
        if not arg:
            ui.info(f"Current model: {cfg.current()['model']}")
        else:
            cfg.current()["model"] = arg
            agent.provider.model = arg
            ui.info(f"Model → {arg}")

    elif cmd == "/models":
        try:
            ui.print_models(agent.provider.list_models(), arg)
        except ProviderError as exc:
            ui.error(str(exc))

    elif cmd == "/provider":
        if not arg:
            ui.info(f"Current provider: {cfg.provider}")
        elif arg not in cfg.providers:
            ui.error(f"Unknown provider '{arg}'. Known: {', '.join(cfg.providers)}")
        else:
            cfg.provider = arg
            agent.provider = build_provider(cfg)
            ctx, src = load_project_context(os.getcwd())
            agent.session.system = system_prompt(os.getcwd(), agent.provider.model, cfg.provider, ctx, src)
            ui.info(f"Provider → {arg} ({agent.provider.model})")

    elif cmd == "/providers":
        for name, prov in cfg.providers.items():
            mark = "→" if name == cfg.provider else " "
            tag = "offline" if prov.get("offline") else "cloud"
            fb = f" · fallback: {prov.get('fallback')}" if prov.get("fallback") else ""
            console.print(f" {mark} [bold]{name}[/bold] [dim]{tag} · {prov['model']}{fb}[/dim]")

    elif cmd == "/init":
        agent.run_turn(INIT_PROMPT)

    elif cmd == "/undo":
        msg = agent.undo()
        ui.info(msg) if msg else ui.warn("Nothing to undo.")

    elif cmd == "/sessions":
        ui.session_list(persistence.list_recent(cwd=os.getcwd()))

    elif cmd == "/auto":
        cfg.auto_approve = not cfg.auto_approve
        ui.info(f"Auto-approve {'ON — tools run without asking' if cfg.auto_approve else 'OFF'}")

    elif cmd == "/guard":
        cfg.secret_guard = not cfg.secret_guard
        ui.info(f"Secret Guard {'ON' if cfg.secret_guard else 'OFF'}")

    elif cmd == "/airgap":
        if airgap.is_enabled():
            airgap.disable()
            cfg.airgap = False
            ui.info("Airgap mode OFF — network allowed again.")
        else:
            airgap.enable()
            cfg.airgap = True
            ui.info("🔒 Airgap mode ENGAGED — all outbound network is now blocked. Local models still work.")
            if not cfg.current().get("offline"):
                ui.warn(f"Current provider '{cfg.provider}' is cloud — switch to a local one to keep working.")

    elif cmd == "/tools":
        for name in agent.registry.names():
            tool = agent.registry.get(name)
            guard = " [yellow](asks approval)[/yellow]" if tool.requires_approval else ""
            desc = tool.description.replace("\n", " ")
            if len(desc) > 72:
                desc = desc[:71] + "…"
            console.print(f"  [cyan]{name}[/cyan]{guard} [dim]— {desc}[/dim]")

    elif cmd == "/cost":
        s = agent.session
        console.print(
            f"[dim]tokens[/dim] in={s.prompt_tokens} out={s.completion_tokens} "
            f"total={s.total_tokens}" + (f"  [dim]cost[/dim] ${s.cost:.4f}" if s.cost else "")
        )

    elif cmd == "/clear":
        agent.session.clear()
        ui.info("Conversation cleared.")

    elif cmd == "/save":
        if cfg.save():
            ui.info("Config saved.")

    else:
        ui.warn(f"Unknown command: {cmd}. Try /help")

    return True


def _persist(agent: Agent) -> None:
    try:
        persistence.save(agent.session, agent.provider.name, agent.provider.model, os.getcwd())
    except OSError:
        pass


# --- REPL ----------------------------------------------------------------
def repl(agent: Agent, cfg: Config) -> None:
    prov = cfg.current()
    ui.banner(cfg.provider, agent.provider.model, bool(prov.get("offline")),
              cfg.auto_approve, cfg.secret_guard, airgap.is_enabled())
    if agent.session.messages:
        ui.info(f"Resumed session {agent.session.id} ({len(agent.session.messages)} messages).")

    # A real terminal gets prompt_toolkit (history, editing). When stdin is
    # piped, use plain readline so the REPL and the in-turn permission prompts
    # share one stdin cleanly (scripted demos work, no TTY warning).
    if sys.stdin.isatty():
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        ptk = PromptSession(history=FileHistory(str(HISTORY_PATH)))

        def read_line() -> str:
            return ptk.prompt("› ")
    else:
        def read_line() -> str:
            line = sys.stdin.readline()
            if not line:
                raise EOFError
            console.print(f"[dim]›[/dim] {line.rstrip()}")
            return line.rstrip("\n")

    while True:
        try:
            line = read_line()
        except KeyboardInterrupt:
            continue
        except EOFError:
            break

        line = line.strip()
        if not line:
            continue
        if line.startswith("/"):
            if not handle_slash(line, agent, cfg):
                break
            _persist(agent)
            continue

        try:
            agent.run_turn(expand_mentions(line))
        except KeyboardInterrupt:
            ui.warn("Turn interrupted.")
        _persist(agent)

    console.print("[dim]bye.[/dim]")


# --- subcommands ---------------------------------------------------------
def cmd_config(args: argparse.Namespace, cfg: Config) -> int:
    if args.config_action == "set-key":
        if args.provider not in cfg.providers:
            ui.error(f"Unknown provider '{args.provider}'")
            return 1
        cfg.providers[args.provider]["api_key"] = args.key
        cfg.save()
        ui.info(f"Saved key for '{args.provider}' to {CONFIG_DIR / 'config.json'} (chmod 600).")
    elif args.config_action == "set-model":
        if args.provider not in cfg.providers:
            ui.error(f"Unknown provider '{args.provider}'")
            return 1
        cfg.providers[args.provider]["model"] = args.model
        cfg.save()
        ui.info(f"Default model for '{args.provider}' → {args.model}")
    elif args.config_action == "set-provider":
        if args.provider not in cfg.providers:
            ui.error(f"Unknown provider '{args.provider}'")
            return 1
        cfg.provider = args.provider
        cfg.save()
        ui.info(f"Default provider → {args.provider}")
    else:
        import json as _json
        console.print_json(_json.dumps(cfg.to_dict()))
    return 0


def cmd_models(args: argparse.Namespace, cfg: Config) -> int:
    if args.provider:
        cfg.provider = args.provider
    provider = build_provider(cfg)
    try:
        ui.print_models(provider.list_models(), args.filter or "")
    except ProviderError as exc:
        ui.error(str(exc))
        return 1
    return 0


def cmd_sessions(cfg: Config) -> int:
    ui.session_list(persistence.list_recent())
    return 0


# --- arg parsing ---------------------------------------------------------
def _chat_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="lumen",
        description="Lumen — a privacy-first coding harness (local LLMs offline, or OpenRouter with your own key).",
        epilog="Subcommands: `lumen config ...`, `lumen models [filter]`, `lumen sessions`.",
    )
    p.add_argument("--version", action="version", version=f"lumen {__version__}")
    p.add_argument("-p", "--provider", help="Provider to use (local | openrouter | ...).")
    p.add_argument("-m", "--model", help="Model id override for this run.")
    p.add_argument("--yolo", action="store_true", help="Auto-approve all tool calls.")
    p.add_argument("--no-guard", action="store_true", help="Disable the Secret Guard.")
    p.add_argument("--airgap", action="store_true", help="Hard-block all outbound network (local models only).")
    p.add_argument("-c", "--continue", dest="cont", action="store_true", help="Resume the most recent session here.")
    p.add_argument("--resume", metavar="ID", help="Resume a saved session by id.")
    p.add_argument("prompt", nargs="*", help="One-shot prompt. Omit for interactive mode.")
    return p


def _config_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="lumen config", description="View or edit configuration.")
    csub = p.add_subparsers(dest="config_action", required=False)
    ck = csub.add_parser("set-key"); ck.add_argument("provider"); ck.add_argument("key")
    cm = csub.add_parser("set-model"); cm.add_argument("provider"); cm.add_argument("model")
    cp = csub.add_parser("set-provider"); cp.add_argument("provider")
    csub.add_parser("show")
    return p


def _models_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="lumen models", description="List a provider's model catalogue.")
    p.add_argument("-p", "--provider")
    p.add_argument("filter", nargs="?")
    return p


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    cfg = Config.load()

    if argv and argv[0] == "config":
        return cmd_config(_config_parser().parse_args(argv[1:]), cfg)
    if argv and argv[0] == "models":
        return cmd_models(_models_parser().parse_args(argv[1:]), cfg)
    if argv and argv[0] == "sessions":
        return cmd_sessions(cfg)

    args = _chat_parser().parse_args(argv)
    if args.provider:
        if args.provider not in cfg.providers:
            ui.error(f"Unknown provider '{args.provider}'. Known: {', '.join(cfg.providers)}")
            return 1
        cfg.provider = args.provider
    if args.model:
        cfg.current()["model"] = args.model
    if args.yolo:
        cfg.auto_approve = True
    if args.no_guard:
        cfg.secret_guard = False
    if args.airgap:
        cfg.airgap = True
    if cfg.airgap:
        airgap.enable()

    resume = None
    if args.resume:
        resume = persistence.load(args.resume)
        if resume is None:
            ui.error(f"No session found for id '{args.resume}'.")
            return 1
    elif args.cont:
        resume = persistence.latest(cwd=os.getcwd())
        if resume is None:
            ui.warn("No previous session in this directory — starting fresh.")

    agent = make_agent(cfg, resume=resume)

    if args.prompt:
        agent.run_turn(expand_mentions(" ".join(args.prompt)))
        _persist(agent)
        return 0

    try:
        repl(agent, cfg)
    except Exception as exc:
        ui.error(f"Fatal: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
