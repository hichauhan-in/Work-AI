"""Tests for the web-fallback decision logic in RagEngine, using fakes (no Ollama/Chroma)."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from src.rag.engine import RagEngine
from src.schema import RetrievedChunk


class FakeLLM:
    vision_model = None

    def embed(self, text):
        return [0.1, 0.2, 0.3]

    def chat(self, messages):
        return "answer"


class FakeStore:
    def __init__(self, notes):
        self._notes = notes

    def query(self, embedding, top_k):
        return self._notes


class FakeWeb:
    def __init__(self):
        self.calls = 0

    def search(self, query):
        self.calls += 1
        return [{"title": "t", "url": "u", "content": "c"}]


def _engine(notes, web):
    return RagEngine(
        store=FakeStore(notes), llm=FakeLLM(), web=web,
        top_k=5, score_threshold=0.35, web_enabled=True,
    )


def test_strong_notes_do_not_trigger_web():
    web = FakeWeb()
    notes = [RetrievedChunk("t", {"filename": "n.md"}, 0.90)]
    result = _engine(notes, web).answer("q")
    assert web.calls == 0
    assert result["used_web"] is False


def test_weak_notes_trigger_web_automatically():
    web = FakeWeb()
    notes = [RetrievedChunk("t", {"filename": "n.md"}, 0.10)]
    result = _engine(notes, web).answer("q")
    assert web.calls == 1
    assert result["used_web"] is True


def test_force_web_searches_even_with_strong_notes():
    web = FakeWeb()
    notes = [RetrievedChunk("t", {"filename": "n.md"}, 0.95)]
    result = _engine(notes, web).answer("q", force_web=True)
    assert web.calls == 1
    assert result["used_web"] is True


def test_no_web_disables_even_when_notes_weak():
    web = FakeWeb()
    notes = [RetrievedChunk("t", {"filename": "n.md"}, 0.0)]
    result = _engine(notes, web).answer("q", use_web=False)
    assert web.calls == 0
