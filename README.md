# Lumen

[![PyPI](https://img.shields.io/pypi/v/lumen-code?color=F4B740&label=pypi)](https://pypi.org/project/lumen-code/)
[![Python](https://img.shields.io/badge/python-3.10%2B-4FD1C5)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-A99C82)](LICENSE)
[![models](https://img.shields.io/badge/models-local%20%2B%20OpenRouter-F4B740)](https://openrouter.ai/models)

**A privacy-first coding agent for your terminal.** Run local LLMs offline, or bring your own OpenRouter key for the full catalogue — no daily limits, no vendor lock-in, and your code never leaves your machine when you don't want it to.

```bash
pipx install lumen-code     # then just run:  lumen
```

<p align="center">
  <img src="docs/demo.svg" alt="Lumen in the terminal — offline build, diff + undo, airgap mode, Secret Guard, model catalogue" width="880">
</p>

Lumen is your own agentic **terminal** coding assistant: point it at a local model (Ollama, LM Studio, llama.cpp — fully offline) or at OpenRouter's entire catalogue with a key you control. It reads, edits, runs and searches your code straight from the shell — with an approval gate on anything destructive.

> **Prefer not to install anything?** Try the same agent in your browser, zero setup → **https://jaydip-meesho.github.io/lumen/app/**

## Why

- **Privacy first.** In `local` mode every byte stays on your machine — no network calls at all. Great for proprietary code.
- **No daily limits.** Bring your own OpenRouter key and pay per token, or run entirely free on local hardware.
- **The whole catalogue.** OpenRouter exposes hundreds of models (Claude, GPT, Gemini, Llama, Qwen, DeepSeek…). Switch between any of them — and your local models — without leaving the REPL.
- **A real agent.** Not a chat box. Lumen reads and edits files, runs shell commands, and searches your code with an approval gate on anything destructive.

## How it compares

| | Hosted tools (Claude Code / Codex) | **Lumen** |
|---|---|---|
| Daily usage limits | Yes — locked out mid-task on a cap | **None** (local) · none beyond your balance |
| Your code leaves your machine | **100%** — uploaded to a vendor cloud | **0 bytes** in local mode (shown live by the egress meter); provable via Airgap |
| Cost | **$20–$200/mo** subscription (or metered API) | **$0** local · pay-per-token cloud with your key |
| Model choice | **1** vendor's family | **300+** models via OpenRouter **+ any local model**, switchable mid-session |
| Works offline | ❌ No | ✅ **Yes** (local) |
| Setup to try | Account + subscription / API key | **Zero** — open the web app, no key, no login |
| Context overhead / turn | Large, hidden | **~1,100 tokens**, measured (run `scripts/measure_context.py`) |
| Open source | ❌ No | ✅ **MIT**, self-hosted, yours |

<sub>Subscription figures are the published Pro ($20) / Max ($100–$200) tiers; "300+" is OpenRouter's current catalogue; 1,100 tokens is measured on Lumen's own system prompt + tool schemas. Lumen isn't trying to out-model frontier vendors — it uses the same frontier models via your key when you want, and wins on privacy, limits, cost, choice and openness.</sub>

## What's inside

Lumen is, first and foremost, a **terminal** coding agent — `pip install lumen-code`, then run `lumen`:

- **🔒 Airgap mode** — `--airgap` (or `/airgap`) patches the socket layer to hard-block *all* outbound network. Local model servers keep working; anything that would leave the machine is refused before a byte moves. Privacy you can prove, not just promise.
- **🛡 Secret Guard** — before any *cloud* request, Lumen scans outgoing messages for API keys, private keys and `.env` values, and lets you block or redact them. In `local`/offline mode it's skipped entirely — nothing leaves the machine.
- **📝 Diff before write** — every `write_file`/`edit_file` shows a colored unified diff *before* it's applied; approve with `y`/`n`/`a`.
- **↩ Undo** — `/undo` reverts the last file change (restores edits, deletes newly-created files).
- **💾 Local sessions** — conversations are saved under `~/.lumen/sessions/`; resume with `--continue` or `--resume <id>`, browse with `lumen sessions`.
- **🧠 Project memory** — a `LUMEN.md` (or `AGENTS.md`) in your repo is auto-loaded into the system prompt; `/init` generates one by exploring the codebase.
- **🔁 Auto-fallback** — if a provider errors (local server down, cloud rate-limited), Lumen fails over to the configured `fallback` provider, warning you if code will now leave the machine.
- **Runs any local model** — parses tool calls even from models that emit them as plain text (`<tool_call>…`, `<function=…>`, fenced JSON), not just those returning structured `tool_calls`.
- **@file mentions** — reference a file with `@path/to/file` in your prompt and Lumen inlines its contents.

**Also runnable in your browser** — [Lumen Web](https://jaydip-meesho.github.io/lumen/app/) brings the same agent to a tab (local via Ollama, or your OpenRouter key), with a live egress monitor, diff-approve, Secret Guard and a zero-setup demo — entirely client-side, nothing to install. Handy for trying it in seconds.

## Install

Requires Python 3.10+.

```bash
# recommended — installs the `lumen` command in an isolated environment
pipx install lumen-code          # or:  uv tool install lumen-code

# or run it once without installing
uvx lumen-code
```

Install straight from source (latest):

```bash
pipx install "git+https://github.com/jaydip-meesho/lumen.git"
```

For development:

```bash
git clone https://github.com/jaydip-meesho/lumen.git
cd lumen
uv pip install -e .              # or: pip install -e .
```

All of these give you the `lumen` command.

## Quick start

### Local (offline, private)

Install [Ollama](https://ollama.com) and pull a tool-capable coding model:

```bash
ollama pull qwen3-coder:30b     # or any tool-capable model
lumen                            # local is the default provider
```

Also works with any OpenAI-compatible local server — LM Studio, llama.cpp's
`server`, vLLM — just point the `local` provider's `base_url` at it.

### OpenRouter (your key, full catalogue)

```bash
export OPENROUTER_API_KEY=sk-or-...     # or: lumen config set-key openrouter sk-or-...
lumen -p openrouter -m anthropic/claude-sonnet-4.5
```

### One-shot (scripting)

```bash
lumen "refactor utils.py to remove the duplicated date parsing"
lumen -p openrouter -m openai/gpt-4o "explain what main.go does"
```

## In-REPL commands

| command | what it does |
|---|---|
| `/models [filter]` | list the provider's catalogue (with context & price) |
| `/model <id>` | switch model |
| `/provider <name>` | switch between `local`, `openrouter`, … |
| `/providers` | list configured providers (and their fallback) |
| `/init` | explore the repo and generate a `LUMEN.md` |
| `/undo` | revert the last file change Lumen made |
| `/sessions` | list saved sessions (resume with `lumen --resume <id>`) |
| `/guard` | toggle the Secret Guard on/off |
| `/airgap` | toggle airgap mode (hard-block all network egress) |
| `/auto` | toggle auto-approve (skip permission prompts) |
| `/tools` | list available tools |
| `/cost` | token usage (and $ cost on OpenRouter) |
| `/clear` | reset the conversation |
| `/save` | persist current provider/model to config |
| `/help` | full command list |

`Ctrl-D` to exit, `Ctrl-C` to cancel the current line.

**Flags:** `--continue`/`-c` (resume latest session here) · `--resume <id>` · `--yolo` (auto-approve) · `--no-guard` (disable Secret Guard) · `--airgap` (block all network) · `-p/--provider` · `-m/--model`.

## Tools the agent can use

`read_file` · `write_file` · `edit_file` · `list_dir` · `run_bash` · `search` (regex/ripgrep) · `find_files` (glob).

Writes and shell commands prompt for approval by default: answer `y` (once), `n` (deny), or `a` (allow all for this session). Start with `--yolo` or toggle `/auto` to run unattended.

## Configuration

Config lives at `~/.lumen/config.json` (override with `LUMEN_HOME`). Add or edit providers there — anything OpenAI-compatible works:

```json
{
  "provider": "local",
  "providers": {
    "local":      { "base_url": "http://localhost:11434/v1", "model": "qwen3-coder:30b", "offline": true },
    "lmstudio":   { "base_url": "http://localhost:1234/v1",  "model": "your-local-model", "offline": true },
    "openrouter": { "base_url": "https://openrouter.ai/api/v1", "model": "anthropic/claude-sonnet-4.5",
                    "api_key_env": "OPENROUTER_API_KEY" }
  }
}
```

## Architecture

```
lumen/
  cli.py                 argument parsing + interactive REPL + slash commands
  agent.py               the agent loop: stream → run tools → repeat
  session.py             conversation state + usage/cost totals
  config.py              providers, models, keys, preferences
  prompts.py             system prompt (+ project memory)
  security.py            Secret Guard — scan/redact secrets before any cloud call
  airgap.py              socket-layer hard block of all outbound network
  diffing.py             unified-diff preview for pending file changes
  persistence.py         local session save / load / resume
  toolcall_parse.py      parse tool calls from models that emit them as text
  providers/
    openai_compat.py     one OpenAI-compatible client for local + cloud
    base.py              Delta / Completion / ToolCall types
  tools/
    base.py              Tool definition + JSON-schema export
    fs.py                read / write / edit / list
    shell.py             run_bash (permission-gated)
    search.py            regex search + glob find
    registry.py          schema export + dispatch
  ui/console.py          rich-based streaming, tool display, permissions

scripts/                 dev-only tooling (needs `pip install -e ".[dev]"`)
  measure_context.py     reproduce the ~1,100-token context-overhead figure
  build_deck.py, make_*_svg.py   pitch deck + demo/poster generators
```

Local and cloud share **one** client because Ollama, LM Studio, llama.cpp and
OpenRouter all speak the OpenAI `/chat/completions` dialect — only the base URL
and key differ. Adding a new backend is a config entry, not code.

## License

MIT.
