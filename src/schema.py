"""Lightweight data structures shared across the pipeline.

Only the standard library is used here so this module imports without any
third-party packages installed (useful for unit tests on the dev machine).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Section:
    """A logical piece of a source file (e.g. one PDF page or one slide)."""

    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Chunk:
    """An embed-ready slice of text plus its provenance metadata."""

    id: str
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RetrievedChunk:
    """A chunk returned from the vector store with a similarity score (0..1)."""

    text: str
    metadata: dict[str, Any]
    score: float
