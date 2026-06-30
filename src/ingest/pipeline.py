"""The ingestion pipeline: discover -> load -> chunk -> embed -> store.

Incremental by design: a manifest tracks each file's content hash so unchanged files are
skipped on re-runs, and changed files have their old chunks removed before re-adding.
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

from ..logging_setup import get_logger
from .chunking import sections_to_chunks
from .loaders import is_supported, load_file

log = get_logger("pipeline")


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(65536), b""):
            digest.update(block)
    return digest.hexdigest()


class Manifest:
    """JSON record of ingested files -> {hash, chunks, timestamp}."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self.data: dict[str, dict] = {}
        if self.path.exists():
            try:
                self.data = json.loads(self.path.read_text(encoding="utf-8"))
            except Exception as exc:  # pragma: no cover
                log.warning("Could not read manifest %s: %s", self.path, exc)
                self.data = {}

    def is_unchanged(self, source: str, content_hash: str) -> bool:
        entry = self.data.get(source)
        return bool(entry) and entry.get("hash") == content_hash

    def update(self, source: str, content_hash: str, chunk_count: int) -> None:
        self.data[source] = {
            "hash": content_hash,
            "chunks": chunk_count,
            "ingested_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }

    def remove(self, source: str) -> None:
        self.data.pop(source, None)

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, indent=2), encoding="utf-8")


class IngestionPipeline:
    def __init__(self, store, embedder, ocr, cfg):
        self.store = store
        self.embedder = embedder
        self.ocr = ocr
        self.size = int(cfg.get("chunking.chunk_size_words", 220))
        self.overlap = int(cfg.get("chunking.chunk_overlap_words", 40))
        self.min_words = int(cfg.get("chunking.min_chunk_words", 20))
        index_dir = cfg.path("paths.index_dir", "storage/index")
        self.manifest = Manifest(Path(index_dir) / "manifest.json")

    def discover(self, root: str | Path) -> list[Path]:
        root = Path(root)
        if root.is_file():
            return [root] if is_supported(root) else []
        if not root.exists():
            log.warning("Path does not exist: %s", root)
            return []
        return sorted(p for p in root.rglob("*") if p.is_file() and is_supported(p))

    def ingest_path(self, root: str | Path, reset: bool = False, force: bool = False) -> dict:
        if reset:
            log.info("Reset requested: clearing the vector store and manifest.")
            self.store.reset()
            self.manifest.data = {}
            self.manifest.save()

        files = self.discover(root)
        log.info("Discovered %d supported file(s) under %s", len(files), root)

        stats = {"files": len(files), "ingested": 0, "skipped": 0,
                 "failed": 0, "chunks": 0}

        for path in files:
            try:
                content_hash = file_hash(path)
                if not force and self.manifest.is_unchanged(str(path), content_hash):
                    stats["skipped"] += 1
                    log.info("Unchanged, skipping: %s", path.name)
                    continue

                # Remove any previous chunks for this file before re-adding.
                self.store.delete_by_source(str(path))

                sections = load_file(path, ocr=self.ocr)
                chunks = sections_to_chunks(sections, self.size, self.overlap, self.min_words)

                if not chunks:
                    log.info("No extractable text: %s", path.name)
                    self.manifest.update(str(path), content_hash, 0)
                    self.manifest.save()
                    stats["ingested"] += 1
                    continue

                embeddings = self.embedder.embed_batch([c.text for c in chunks])
                self.store.add(chunks, embeddings)
                self.manifest.update(str(path), content_hash, len(chunks))
                self.manifest.save()

                stats["ingested"] += 1
                stats["chunks"] += len(chunks)
                log.info("Ingested %s (%d chunks)", path.name, len(chunks))
            except Exception as exc:
                stats["failed"] += 1
                log.error("Failed to ingest %s: %s", path, exc, exc_info=True)

        log.info(
            "Done. ingested=%d skipped=%d failed=%d chunks=%d (store now holds %d chunks)",
            stats["ingested"], stats["skipped"], stats["failed"], stats["chunks"],
            self.store.count(),
        )
        return stats
