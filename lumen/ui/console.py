"""Terminal rendering for Lumen, built on rich."""

from __future__ import annotations

import json

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

console = Console()

# streaming state
_stream_open = False


def banner(provider: str, model: str, offline: bool, auto: bool, guard: bool = True,
           airgap_on: bool = False) -> None:
    lock = "offline · code never leaves this machine" if offline else "cloud · via your own key"
    body = Text()
    body.append("LUMEN", style="bold cyan")
    body.append("  privacy-first coding harness\n\n", style="dim")
    body.append("provider  ", style="dim")
    body.append(f"{provider}\n", style="bold")
    body.append("model     ", style="dim")
    body.append(f"{model}\n", style="bold")
    body.append("mode      ", style="dim")
    body.append(f"{lock}\n", style="green" if offline else "yellow")
    body.append("approval  ", style="dim")
    body.append("auto (yolo)\n" if auto else "prompt + diff before writes / shell\n", style="dim")
    body.append("guard     ", style="dim")
    if offline:
        body.append("n/a — nothing leaves the machine\n", style="green")
    else:
        body.append("secret guard ON\n" if guard else "secret guard OFF\n", style="green" if guard else "red")
    body.append("airgap    ", style="dim")
    if airgap_on:
        body.append("🔒 ENGAGED — all network egress blocked", style="bold green")
    else:
        body.append("off  (enable with --airgap or /airgap)", style="dim")
    console.print(Panel(body, border_style="green" if airgap_on else "cyan", expand=False))
    console.print("[dim]Type your request, or /help for commands. Ctrl-D to exit.[/dim]\n")


def rule(label: str = "") -> None:
    console.rule(f"[dim]{label}[/dim]" if label else "")


def info(msg: str) -> None:
    console.print(f"[cyan]{msg}[/cyan]")


def warn(msg: str) -> None:
    console.print(f"[yellow]! {msg}[/yellow]")


def error(msg: str) -> None:
    console.print(f"[bold red]✗ {msg}[/bold red]")


def thinking(msg: str = "thinking") -> None:
    console.print(f"[dim]{msg}…[/dim]")


# --- assistant streaming -------------------------------------------------
def assistant_start() -> None:
    global _stream_open
    _stream_open = False


def assistant_delta(text: str) -> None:
    global _stream_open
    if not _stream_open:
        console.print("[bold green]lumen[/bold green] ", end="")
        _stream_open = True
    # markup/highlight off so code and braces render literally
    console.print(text, end="", markup=False, highlight=False, soft_wrap=True)


def assistant_end(had_text: bool) -> None:
    global _stream_open
    if _stream_open:
        console.print()  # newline after the streamed answer
    _stream_open = False


# --- tool calls ----------------------------------------------------------
def _preview_args(args: dict) -> str:
    try:
        s = json.dumps(args, ensure_ascii=False)
    except (TypeError, ValueError):
        s = str(args)
    return s if len(s) <= 120 else s[:117] + "…"


def tool_call(name: str, args: dict) -> None:
    # dynamic parts rendered via Text.append so brackets in args aren't parsed as markup
    t = Text("  ⚙ ", style="cyan")
    t.append(name, style="bold cyan")
    t.append("  " + _preview_args(args), style="dim")
    console.print(t, highlight=False)


def tool_result(text: str) -> None:
    lines = text.splitlines()
    shown = lines[:12]
    for line in shown:
        console.print("    " + line, style="dim", markup=False, highlight=False)
    if len(lines) > len(shown):
        console.print(f"    … (+{len(lines) - len(shown)} more lines)", style="dim")


def render_diff(diff_text: str, note: str = "") -> None:
    """Print a unified diff with colored +/- lines."""
    console.print(f"  change preview{(' · ' + note) if note else ''}", style="dim")
    for line in diff_text.splitlines():
        if line.startswith(("+++", "---")):
            style = "dim"
        elif line.startswith("@@"):
            style = "cyan"
        elif line.startswith("+"):
            style = "green"
        elif line.startswith("-"):
            style = "red"
        else:
            style = "dim"
        console.print("    " + line, style=style, markup=False, highlight=False)


def ask_permission(name: str, args: dict, diff: str | None = None, note: str = "") -> str:
    """Prompt to run a mutating tool. Returns 'yes' | 'no' | 'always'."""
    if diff:
        render_diff(diff, note)
    t = Text("  permission ", style="yellow")
    t.append("run ")
    t.append(name, style="bold")
    t.append("  " + _preview_args(args), style="dim")
    console.print(t, highlight=False)
    try:
        answer = console.input("  [yellow]allow? (y)es / (n)o / (a)lways: [/yellow]").strip().lower()
    except (EOFError, KeyboardInterrupt):
        return "no"
    if answer in ("a", "always"):
        return "always"
    if answer in ("y", "yes"):
        return "yes"
    return "no"


def secret_alert(hits: list, provider: str) -> str:
    """Warn about secrets about to leave the machine. Returns 'redact'|'send'|'cancel'."""
    from rich.panel import Panel

    body = Text()
    body.append("🛡  Secret Guard\n", style="bold red")
    body.append(f"About to send {len(hits)} possible secret(s) to ", style="bold")
    body.append(f"{provider}", style="bold yellow")
    body.append(" — a cloud provider.\n\n", style="bold")
    for where, f in hits[:8]:
        body.append("  • ", style="red")
        body.append(f"{f.kind}", style="bold")
        body.append(f"  {f.masked}", style="yellow")
        body.append(f"   [in {where}]\n", style="dim")
    if len(hits) > 8:
        body.append(f"  … and {len(hits) - 8} more\n", style="dim")
    console.print(Panel(body, border_style="red", expand=False))
    try:
        answer = console.input(
            "  [red]redact & send[/red] (r) / [yellow]send anyway[/yellow] (s) / [bold]cancel[/bold] (c): "
        ).strip().lower()
    except (EOFError, KeyboardInterrupt):
        return "cancel"
    if answer in ("s", "send"):
        return "send"
    if answer in ("r", "redact"):
        return "redact"
    return "cancel"


def fallback_notice(from_name: str, to_name: str, leaving_machine: bool) -> None:
    warn(f"{from_name} is unavailable — falling back to {to_name}.")
    if leaving_machine:
        console.print("  [bold red]⚠ your code will now leave this machine (cloud provider).[/bold red]")


def turn_stats(seconds: float, prompt_tok: int, completion_tok: int, cost: float,
               provider: str, model: str) -> None:
    parts = [f"{seconds:.1f}s"]
    total = (prompt_tok or 0) + (completion_tok or 0)
    if total:
        parts.append(f"{total:,} tok")
    if cost:
        parts.append(f"${cost:.4f}")
    parts.append(f"{provider}/{model}")
    console.print(f"  [dim]{'  ·  '.join(parts)}[/dim]")


def session_list(rows: list) -> None:
    from rich.table import Table

    if not rows:
        info("No saved sessions yet.")
        return
    t = Table(show_header=True, header_style="bold cyan", box=None, pad_edge=False)
    t.add_column("id"); t.add_column("when"); t.add_column("provider"); t.add_column("msgs", justify="right"); t.add_column("preview")
    import time as _time
    for d in rows:
        first_user = next((m.get("content") for m in d.get("messages", []) if m.get("role") == "user"), "") or ""
        first_user = " ".join(str(first_user).split())[:44]
        when = _time.strftime("%b %d %H:%M", _time.localtime(d.get("updated", 0)))
        t.add_row(d.get("id", "")[:17], when, d.get("provider", ""),
                  str(len(d.get("messages", []))), Text(first_user))
    console.print(t)


# --- model catalogue -----------------------------------------------------
def print_models(models: list[dict], filter_str: str = "") -> None:
    from rich.table import Table

    rows = []
    for m in models:
        mid = m.get("id", "")
        if filter_str and filter_str.lower() not in mid.lower():
            continue
        ctx = m.get("context_length") or (m.get("top_provider") or {}).get("context_length")
        pricing = m.get("pricing") or {}
        prompt_price = pricing.get("prompt")
        # OpenRouter prices are per-token as strings; show per-million.
        price_str = ""
        if prompt_price not in (None, "", "0"):
            try:
                price_str = f"${float(prompt_price) * 1_000_000:.2f}/M in"
            except (TypeError, ValueError):
                price_str = ""
        rows.append((mid, str(ctx) if ctx else "", price_str))

    if not rows:
        warn(f"No models match '{filter_str}'." if filter_str else "No models returned.")
        return

    table = Table(show_header=True, header_style="bold cyan", box=None, pad_edge=False)
    table.add_column("model id")
    table.add_column("context", justify="right")
    table.add_column("price", justify="right")
    for mid, ctx, price in sorted(rows):
        table.add_row(mid, ctx, price)
    console.print(table)
    console.print(f"[dim]{len(rows)} model(s). Select one with /model <id>.[/dim]")
