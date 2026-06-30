"""Tests for the web-fallback decision logic in RagEngine, using fakes (no Ollama/Chroma)."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from src.rag.engine import RagEngine
from src.schema import RetrievedChunk


class FakeLLM:
    vision_model = None

    def __init__(self):
        self.chat_calls = 0
        self.last_messages = None

    def embed(self, text):
        return [0.1, 0.2, 0.3]

    def chat(self, messages):
        self.chat_calls += 1
        self.last_messages = messages
        return "answer"


class FakeStore:
    def __init__(self, notes):
        self._notes = notes
        self.query_calls = 0

    def query(self, embedding, top_k):
        self.query_calls += 1
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


def test_depth_request_triggers_web_even_with_strong_notes():
    web = FakeWeb()
    notes = [RetrievedChunk("t", {"filename": "n.md"}, 0.95)]
    result = _engine(notes, web).answer("Give me an in-depth explanation of ABC")
    assert web.calls == 1
    assert result["used_web"] is True


def test_followup_is_condensed_using_history():
    web = FakeWeb()
    notes = [RetrievedChunk("t", {"filename": "n.md"}, 0.95)]
    engine = _engine(notes, web)
    history = [
        {"role": "user", "content": "Tell me about Linux networking"},
        {"role": "assistant", "content": "Linux uses ip/ss tools..."},
    ]
    engine.answer("explain that further", history=history)
    # One chat call to condense the follow-up + one to produce the final answer.
    assert engine.llm.chat_calls == 2


def test_history_messages_are_included_in_prompt():
    web = FakeWeb()
    notes = [RetrievedChunk("t", {"filename": "n.md"}, 0.95)]
    engine = RagEngine(
        store=FakeStore(notes), llm=FakeLLM(), web=web,
        top_k=5, score_threshold=0.35, web_enabled=True,
        condense_followups=False,
    )
    history = [{"role": "user", "content": "earlier question about DNS"}]
    engine.answer("and what about caching?", history=history)
    roles = [m["role"] for m in engine.llm.last_messages]
    # system + the prior user turn + the current user turn
    assert roles == ["system", "user", "user"]


def test_multi_query_expands_into_several_lookups():
    web = FakeWeb()
    notes = [RetrievedChunk("t", {"filename": "n.md", "source": "s"}, 0.95)]
    store = FakeStore(notes)
    engine = RagEngine(
        store=store, llm=FakeLLM(), web=web,
        top_k=5, score_threshold=0.35, web_enabled=False,
        multi_query=True, max_subqueries=4, condense_followups=False,
    )
    engine.answer("how do I start analyzing a crash dump file")
    # The planner query + at least one expanded sub-query => more than one store lookup.
    assert store.query_calls >= 2


def test_multi_query_skipped_for_short_questions():
    web = FakeWeb()
    notes = [RetrievedChunk("t", {"filename": "n.md", "source": "s"}, 0.95)]
    store = FakeStore(notes)
    engine = RagEngine(
        store=store, llm=FakeLLM(), web=web,
        top_k=5, score_threshold=0.35, web_enabled=False,
        multi_query=True, condense_followups=False,
    )
    engine.answer("ping basics")
    assert store.query_calls == 1
