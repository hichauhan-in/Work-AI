"""Text chunking.

Splits section text into overlapping, embed-ready chunks. Word-based chunking keeps the
implementation dependency-free and predictable; ``chunk_size_words`` of ~220 is roughly a
few short paragraphs (~300 tokens).
"""
from __future__ import annotations

import hashlib

from ..schema import Chunk, Section


def chunk_text(text: str, size: int, overlap: int, min_words: int) -> list[str]:
    """Split ``text`` into overlapping word windows."""
    words = text.split()
    if not words:
        return []
    if len(words) <= size:
        return [" ".join(words)]

    step = max(1, size - overlap)
    chunks: list[str] = []
    index = 0
    while index < len(words):
        window = words[index : index + size]
        # Keep the first window always; drop only tiny trailing fragments.
        if index == 0 or len(window) >= min_words:
            chunks.append(" ".join(window))
        index += step
    return chunks


def make_chunk_id(source: str, section_index: int, chunk_index: int) -> str:
    """Deterministic id so re-ingesting the same file overwrites (not duplicates) chunks."""
    digest = hashlib.sha1(
        f"{source}|{section_index}|{chunk_index}".encode("utf-8")
    ).hexdigest()
    return digest[:16]


def sections_to_chunks(
    sections: list[Section], size: int, overlap: int, min_words: int
) -> list[Chunk]:
    """Convert loaded sections into chunks carrying provenance metadata."""
    out: list[Chunk] = []
    for section_index, section in enumerate(sections):
        pieces = chunk_text(section.text, size, overlap, min_words)
        for chunk_index, piece in enumerate(pieces):
            metadata = dict(section.metadata)
            metadata["section_index"] = section_index
            metadata["chunk_index"] = chunk_index
            chunk_id = make_chunk_id(
                str(metadata.get("source", "")), section_index, chunk_index
            )
            out.append(Chunk(id=chunk_id, text=piece, metadata=metadata))
    return out
