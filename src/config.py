"""Configuration loading.

Config lives in ``config.yaml`` (copied from ``config.example.yaml``). Values can be
read with dotted keys, e.g. ``cfg.get("ollama.chat_model")``. Relative paths are
resolved against the repository root so the same config works from any working dir.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

DEFAULT_CONFIG_FILENAME = "config.yaml"


def repo_root() -> Path:
    """Return the repository root (the parent of the ``src`` package)."""
    return Path(__file__).resolve().parent.parent


class Config:
    """Thin wrapper around the parsed YAML config with dotted-key access."""

    def __init__(self, data: dict[str, Any], root: Path):
        self.data = data or {}
        self.root = Path(root)

    def get(self, dotted_key: str, default: Any = None) -> Any:
        current: Any = self.data
        for part in dotted_key.split("."):
            if not isinstance(current, dict) or part not in current:
                return default
            current = current[part]
        return current

    def path(self, dotted_key: str, default: str | None = None) -> Path | None:
        """Resolve a config value as a filesystem path relative to the repo root."""
        value = self.get(dotted_key, default)
        if value is None:
            return None
        p = Path(value)
        if not p.is_absolute():
            p = self.root / p
        return p


def load_config(path: str | os.PathLike[str] | None = None) -> Config:
    """Load configuration from ``config.yaml`` (or an explicit path).

    Resolution order for the config file:
      1. The ``path`` argument, if given.
      2. The ``PERSONALAI_CONFIG`` environment variable.
      3. ``config.yaml`` in the repo root.
    """
    import yaml  # lazy import

    # Load .env (if present) so OLLAMA_HOST / PERSONALAI_CONFIG can come from there.
    try:
        from dotenv import load_dotenv

        load_dotenv(repo_root() / ".env")
    except Exception:
        pass

    root = repo_root()
    raw_path = path or os.environ.get("PERSONALAI_CONFIG") or DEFAULT_CONFIG_FILENAME
    cfg_path = Path(raw_path)
    if not cfg_path.is_absolute():
        cfg_path = root / cfg_path

    if not cfg_path.exists():
        raise FileNotFoundError(
            f"Config file not found: {cfg_path}\n"
            "Create it on this machine by copying the template:\n"
            "  Windows : Copy-Item config.example.yaml config.yaml\n"
            "  Linux   : cp config.example.yaml config.yaml"
        )

    with open(cfg_path, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}

    # Environment override for the Ollama host.
    host = os.environ.get("OLLAMA_HOST")
    if host:
        data.setdefault("ollama", {})["host"] = host

    return Config(data, root)
