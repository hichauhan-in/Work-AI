"""Thin wrapper around the Ollama client for chat, embeddings, and vision.

All Ollama calls in the project go through this class so models, host, and options are
configured in one place. The ``ollama`` package is imported lazily so this module can be
imported on the dev machine without it installed.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .logging_setup import get_logger

log = get_logger("ollama")


def _content(response: Any) -> str:
    """Extract assistant text from a chat response (dict or typed object)."""
    try:
        return response["message"]["content"]
    except Exception:
        return response.message.content


def _embedding(response: Any) -> list[float]:
    """Extract the embedding vector from an embeddings response."""
    try:
        return list(response["embedding"])
    except Exception:
        return list(response.embedding)


class OllamaClient:
    """Chat, embedding, and vision calls against a local Ollama server."""

    def __init__(
        self,
        host: str = "http://localhost:11434",
        chat_model: str = "qwen2.5:14b",
        embed_model: str = "nomic-embed-text",
        vision_model: str | None = None,
        timeout: int = 180,
        options: dict[str, Any] | None = None,
    ):
        import ollama  # lazy import

        self._client = ollama.Client(host=host, timeout=timeout)
        self.host = host
        self.chat_model = chat_model
        self.embed_model = embed_model
        self.vision_model = vision_model
        self.options = options or {}

    @classmethod
    def from_config(cls, cfg) -> "OllamaClient":
        options: dict[str, Any] = {}
        if cfg.get("ollama.temperature") is not None:
            options["temperature"] = cfg.get("ollama.temperature")
        if cfg.get("ollama.num_ctx") is not None:
            options["num_ctx"] = cfg.get("ollama.num_ctx")
        return cls(
            host=cfg.get("ollama.host", "http://localhost:11434"),
            chat_model=cfg.get("ollama.chat_model", "qwen2.5:14b"),
            embed_model=cfg.get("ollama.embed_model", "nomic-embed-text"),
            vision_model=cfg.get("ollama.vision_model"),
            timeout=int(cfg.get("ollama.request_timeout", 180)),
            options=options,
        )

    # --- Embeddings ---------------------------------------------------------
    def embed(self, text: str) -> list[float]:
        response = self._client.embeddings(model=self.embed_model, prompt=text)
        return _embedding(response)

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self.embed(t) for t in texts]

    # --- Chat ---------------------------------------------------------------
    def chat(self, messages: list[dict[str, Any]], model: str | None = None,
             options: dict[str, Any] | None = None) -> str:
        merged = {**self.options, **(options or {})}
        response = self._client.chat(
            model=model or self.chat_model, messages=messages, options=merged or None
        )
        return _content(response)

    # --- Vision -------------------------------------------------------------
    def describe_image(self, image_path: str | Path, prompt: str | None = None) -> str:
        if not self.vision_model:
            raise RuntimeError("No vision_model configured in config.yaml (ollama.vision_model).")
        message = {
            "role": "user",
            "content": prompt
            or (
                "Transcribe all visible text exactly, then briefly describe any diagrams, "
                "tables, code, or UI shown. Be concise and technical."
            ),
            "images": [str(image_path)],
        }
        response = self._client.chat(
            model=self.vision_model, messages=[message], options=self.options or None
        )
        return _content(response)

    # --- Health -------------------------------------------------------------
    def list_models(self) -> list[str]:
        """Return the names of models available on the server."""
        data = self._client.list()
        raw = data.get("models", []) if isinstance(data, dict) else getattr(data, "models", [])
        names: list[str] = []
        for item in raw:
            if isinstance(item, dict):
                name = item.get("model") or item.get("name")
            else:
                name = getattr(item, "model", None) or getattr(item, "name", None)
            if name:
                names.append(name)
        return names

    def ping(self) -> bool:
        """Return True if the server responds; raises on connection failure."""
        self._client.list()
        return True
