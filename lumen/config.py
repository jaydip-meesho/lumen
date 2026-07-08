"""Configuration: providers, models, keys, and preferences.

Config lives at ~/.lumen/config.json (override the dir with LUMEN_HOME).
API keys can live in the file or, preferably, in an environment variable that
the provider entry names via `api_key_env`.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

CONFIG_DIR = Path(os.environ.get("LUMEN_HOME", str(Path.home() / ".lumen")))
CONFIG_PATH = CONFIG_DIR / "config.json"
HISTORY_PATH = CONFIG_DIR / "history"

# Both providers speak the OpenAI-compatible /chat/completions dialect, so a
# single client drives them — only the base URL, key handling, and a few
# provider-specific extras differ.
DEFAULT_PROVIDERS: dict[str, dict] = {
    # Local, offline. Works with Ollama, LM Studio, llama.cpp server, vLLM —
    # anything that exposes an OpenAI-compatible endpoint. No key, no network.
    "local": {
        "base_url": "http://localhost:11434/v1",
        "model": "qwen3-coder:30b",
        "api_key": "local",
        "api_key_env": None,
        "offline": True,
        "extra_headers": {},
        "extra_body": {},
        # if the local server is down / errors, fail over here (code will leave the machine)
        "fallback": "openrouter",
    },
    # Cloud. Bring your own key and reach the entire OpenRouter catalogue.
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "model": "anthropic/claude-sonnet-4.5",
        "api_key": None,
        "api_key_env": "OPENROUTER_API_KEY",
        "offline": False,
        "extra_headers": {
            "HTTP-Referer": "https://github.com/jaydip-meesho/lumen",
            "X-Title": "Lumen",
        },
        # Ask OpenRouter to report generation cost in the usage payload.
        "extra_body": {"usage": {"include": True}},
        "fallback": "local",
    },
}


def _fresh_defaults() -> dict[str, dict]:
    return json.loads(json.dumps(DEFAULT_PROVIDERS))


@dataclass
class Config:
    provider: str = "local"
    providers: dict[str, dict] = field(default_factory=_fresh_defaults)
    auto_approve: bool = False
    max_iterations: int = 50
    temperature: float = 0.0
    secret_guard: bool = True   # scan for secrets before any cloud request
    show_diffs: bool = True     # preview a diff before applying file changes
    fallback_enabled: bool = True
    airgap: bool = False        # hard-block all outbound network (local only)

    @classmethod
    def load(cls) -> "Config":
        if not CONFIG_PATH.exists():
            return cls()
        try:
            data = json.loads(CONFIG_PATH.read_text())
        except (json.JSONDecodeError, OSError):
            return cls()
        # Start from defaults so new provider fields appear even for old files,
        # then overlay whatever the user has saved.
        merged = _fresh_defaults()
        for name, prov in (data.get("providers") or {}).items():
            merged.setdefault(name, {})
            merged[name].update(prov)
        return cls(
            provider=data.get("provider", "local"),
            providers=merged,
            auto_approve=bool(data.get("auto_approve", False)),
            max_iterations=int(data.get("max_iterations", 50)),
            temperature=float(data.get("temperature", 0.0)),
            secret_guard=bool(data.get("secret_guard", True)),
            show_diffs=bool(data.get("show_diffs", True)),
            fallback_enabled=bool(data.get("fallback_enabled", True)),
            airgap=bool(data.get("airgap", False)),
        )

    def save(self) -> bool:
        """Persist config. Returns False (never raises) if the write fails,
        so an interactive `/save` or `lumen config set-*` can't crash the session."""
        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            CONFIG_PATH.write_text(json.dumps(self.to_dict(), indent=2))
            try:
                os.chmod(CONFIG_PATH, 0o600)  # keys may live here
            except OSError:
                pass
            return True
        except OSError as exc:
            from lumen import ui
            ui.error(f"Could not save config to {CONFIG_PATH}: {exc}")
            return False

    def to_dict(self) -> dict:
        return {
            "provider": self.provider,
            "providers": self.providers,
            "auto_approve": self.auto_approve,
            "max_iterations": self.max_iterations,
            "temperature": self.temperature,
            "secret_guard": self.secret_guard,
            "show_diffs": self.show_diffs,
            "fallback_enabled": self.fallback_enabled,
            "airgap": self.airgap,
        }

    # --- accessors -------------------------------------------------------
    def current(self) -> dict:
        return self.providers[self.provider]

    def model(self) -> str:
        return self.current().get("model", "")

    def resolve_api_key(self, provider: str | None = None) -> str | None:
        provider = provider or self.provider
        prov = self.providers.get(provider, {})
        env = prov.get("api_key_env")
        if env and os.environ.get(env):
            return os.environ[env]
        return prov.get("api_key")
