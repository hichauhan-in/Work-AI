"""Unit tests for chunking — pure logic, no third-party dependencies required."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from src.ingest.chunking import chunk_text, make_chunk_id, sections_to_chunks
from src.schema import Section


def test_chunk_text_short_returns_single():
    assert chunk_text("hello world", size=10, overlap=2, min_words=1) == ["hello world"]


def test_chunk_text_empty():
    assert chunk_text("   ", size=10, overlap=2, min_words=1) == []


def test_chunk_text_overlap_and_coverage():
    words = " ".join(str(i) for i in range(100))
    chunks = chunk_text(words, size=30, overlap=10, min_words=5)
    assert len(chunks) > 1
    # First chunk has exactly `size` words.
    assert len(chunks[0].split()) == 30
    # Overlap: last 10 words of chunk 0 equal first 10 words of chunk 1.
    assert chunks[0].split()[-10:] == chunks[1].split()[:10]


def test_make_chunk_id_is_deterministic():
    a = make_chunk_id("file.md", 0, 1)
    b = make_chunk_id("file.md", 0, 1)
    c = make_chunk_id("file.md", 0, 2)
    assert a == b
    assert a != c
    assert len(a) == 16


def test_sections_to_chunks_metadata():
    sections = [Section("alpha beta gamma " * 50, {"source": "x.md", "filename": "x.md"})]
    chunks = sections_to_chunks(sections, size=20, overlap=5, min_words=5)
    assert chunks
    meta = chunks[0].metadata
    assert meta["source"] == "x.md"
    assert meta["section_index"] == 0
    assert meta["chunk_index"] == 0
