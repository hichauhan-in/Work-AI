"""Vector store backed by a persistent ChromaDB collection.

We compute embeddings ourselves (via Ollama) and pass them in, so Chroma is used purely
as a similarity index. Cosine space is used; the returned ``score`` is ``1 - distance``
(higher is more similar).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from ..logging_setup import get_logger
from ..schema import Chunk, RetrievedChunk

log = get_logger("vectorstore")

_PRIMITIVES = (str, int, float, bool)


def _sanitize(metadata: dict[str, Any]) -> dict[str, Any]:
    """Chroma only accepts str/int/float/bool metadata values (no None, no lists)."""
    clean: dict[str, Any] = {}
    for key, value in metadata.items():
        if value is None:
            continue
        clean[key] = value if isinstance(value, _PRIMITIVES) else str(value)
    return clean


class VectorStore:
    def __init__(self, index_dir: str | Path, collection_name: str = "personal_ai"):
        import chromadb  # lazy

        Path(index_dir).mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(path=str(index_dir))
        self.collection_name = collection_name
        self._collection = self._client.get_or_create_collection(
            name=collection_name, metadata={"hnsw:space": "cosine"}
        )

    @classmethod
    def from_config(cls, cfg) -> "VectorStore":
        index_dir = cfg.path("paths.index_dir", "storage/index")
        return cls(index_dir)

    def add(self, chunks: list[Chunk], embeddings: list[list[float]]) -> None:
        if not chunks:
            return
        self._collection.upsert(
            ids=[c.id for c in chunks],
            embeddings=embeddings,
            documents=[c.text for c in chunks],
            metadatas=[_sanitize(c.metadata) for c in chunks],
        )

    def delete_by_source(self, source: str) -> None:
        try:
            self._collection.delete(where={"source": source})
        except Exception as exc:  # pragma: no cover
            log.warning("Failed to delete old chunks for %s: %s", source, exc)

    def query(self, embedding: list[float], top_k: int) -> list[RetrievedChunk]:
        result = self._collection.query(
            query_embeddings=[embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )
        documents = (result.get("documents") or [[]])[0]
        metadatas = (result.get("metadatas") or [[]])[0]
        distances = (result.get("distances") or [[]])[0]

        retrieved: list[RetrievedChunk] = []
        for text, metadata, distance in zip(documents, metadatas, distances):
            retrieved.append(
                RetrievedChunk(text=text, metadata=metadata or {}, score=1.0 - float(distance))
            )
        return retrieved

    def count(self) -> int:
        try:
            return self._collection.count()
        except Exception:  # pragma: no cover
            return 0

    def reset(self) -> None:
        try:
            self._client.delete_collection(self.collection_name)
        except Exception:  # pragma: no cover
            pass
        self._collection = self._client.get_or_create_collection(
            name=self.collection_name, metadata={"hnsw:space": "cosine"}
        )
