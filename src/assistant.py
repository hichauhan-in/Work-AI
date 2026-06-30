"""Application wiring: build all components from config in one place.

The CLI scripts call :func:`build_assistant` so they don't each repeat the setup.
"""
from __future__ import annotations

from .config import Config, load_config
from .ingest.ocr import OCREngine
from .ingest.pipeline import IngestionPipeline
from .logging_setup import setup_logging
from .ollama_client import OllamaClient
from .rag.engine import RagEngine
from .rag.vectorstore import VectorStore
from .web.search import WebSearch


class Assistant:
    """Container that holds the wired-up components."""

    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.llm = OllamaClient.from_config(cfg)
        self.store = VectorStore.from_config(cfg)
        self.web = WebSearch.from_config(cfg) if cfg.get("web.enabled", True) else None
        self.ocr = OCREngine.from_config(cfg, vision_client=self.llm)
        self.engine = RagEngine.from_config(cfg, self.store, self.llm, self.web)
        self.pipeline = IngestionPipeline(self.store, self.llm, self.ocr, cfg)


def build_assistant(config_path: str | None = None) -> Assistant:
    cfg = load_config(config_path)
    setup_logging(cfg.get("logging.level", "INFO"), cfg.path("paths.log_dir"))
    return Assistant(cfg)
