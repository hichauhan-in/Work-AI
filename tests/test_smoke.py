"""Smoke tests: pure modules import and basic helpers behave. No Ollama/Chroma needed."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))


def test_core_modules_import():
    import src.config  # noqa: F401
    import src.logging_setup  # noqa: F401
    import src.schema  # noqa: F401
    from src.ingest import chunking, loaders  # noqa: F401
    from src.rag import prompts  # noqa: F401


def test_is_supported():
    from src.ingest.loaders import is_supported

    assert is_supported("notes.pdf")
    assert is_supported("a.DOCX")
    assert is_supported("shot.png")
    assert not is_supported("archive.zip")


def test_build_context_numbers_sources():
    from src.rag.prompts import build_context
    from src.schema import RetrievedChunk

    notes = [
        RetrievedChunk("text one", {"filename": "net.md", "page": 2}, 0.91),
        RetrievedChunk("text two", {"filename": "dbg.md"}, 0.80),
    ]
    web = [{"title": "T", "url": "http://e", "content": "c"}]
    context, sources = build_context(notes, web)
    assert "[1]" in context and "[2]" in context and "[W1]" in context
    assert sources[0]["ref"] == "[1]" and sources[0]["kind"] == "note"
    assert sources[-1]["kind"] == "web"


def test_load_text_file(tmp_path):
    from src.ingest.loaders import load_file

    p = tmp_path / "note.txt"
    p.write_text("hello networking notes", encoding="utf-8")
    sections = load_file(p)
    assert len(sections) == 1
    assert "networking" in sections[0].text
    assert sections[0].metadata["filetype"] == "txt"


def test_normalize_host_maps_bind_all_to_loopback():
    from src.ollama_client import _normalize_host

    assert _normalize_host("0.0.0.0") == "127.0.0.1"
    assert _normalize_host("0.0.0.0:11434") == "127.0.0.1:11434"
    assert _normalize_host("http://0.0.0.0:11434") == "http://127.0.0.1:11434"
    assert _normalize_host("http://localhost:11434") == "http://localhost:11434"
    assert _normalize_host("") == "http://127.0.0.1:11434"
    assert _normalize_host(None) == "http://127.0.0.1:11434"


def test_resolve_tesseract_cmd_prefers_configured():
    from src.ingest.ocr import resolve_tesseract_cmd

    assert resolve_tesseract_cmd("D:/Tools/Tesseract-OCR/tesseract.exe") == (
        "D:/Tools/Tesseract-OCR/tesseract.exe"
    )
