"""The query engine: notes-first retrieval, optional web fallback, then the LLM.

Flow:
  1. (optional) describe an attached image with the vision model and append to the query.
  2. embed the query and retrieve the top-k note chunks.
  3. if notes are weak (few results or top score below threshold) and web is enabled,
     fetch web results.
  4. assemble context + citations and ask the chat model.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from ..logging_setup import get_logger
from .prompts import build_context, build_messages

log = get_logger("engine")


class RagEngine:
    def __init__(
        self,
        store,
        llm,
        web=None,
        top_k: int = 6,
        score_threshold: float = 0.35,
        web_enabled: bool = True,
    ):
        self.store = store
        self.llm = llm  # OllamaClient: used for both embeddings and chat/vision
        self.web = web
        self.top_k = top_k
        self.score_threshold = score_threshold
        self.web_enabled = web_enabled

    @classmethod
    def from_config(cls, cfg, store, llm, web=None) -> "RagEngine":
        return cls(
            store=store,
            llm=llm,
            web=web,
            top_k=int(cfg.get("retrieval.top_k", 6)),
            score_threshold=float(cfg.get("retrieval.score_threshold", 0.35)),
            web_enabled=bool(cfg.get("web.enabled", True)),
        )

    def answer(
        self,
        question: str,
        use_web: bool | None = None,
        image: str | Path | None = None,
        force_web: bool = False,
    ) -> dict[str, Any]:
        query_text = question

        if image:
            try:
                description = self.llm.describe_image(image)
                query_text = f"{question}\n\n[Attached image content]\n{description}"
                log.info("Vision model described the attached image.")
            except Exception as exc:
                log.warning("Could not analyse image %s: %s", image, exc)

        embedding = self.llm.embed(query_text)
        notes = self.store.query(embedding, self.top_k)
        best_score = notes[0].score if notes else 0.0
        log.info("Retrieved %d note chunk(s); best score=%.3f", len(notes), best_score)

        want_web = self.web_enabled if use_web is None else use_web
        notes_weak = (not notes) or (best_score < self.score_threshold)
        # Web fires when the user explicitly forces it, OR (auto mode) when the notes
        # are too weak to answer confidently.
        should_search = bool(force_web) or (want_web and notes_weak)
        web_results: list[dict] = []
        if should_search and self.web is not None:
            reason = "user requested" if force_web else "notes look weak"
            log.info("Querying the web (%s) for: %s", reason, question)
            web_results = self.web.search(question)

        context, sources = build_context(notes, web_results)
        messages = build_messages(query_text, context)
        answer_text = self.llm.chat(messages)

        return {
            "answer": answer_text,
            "sources": sources,
            "notes": notes,
            "web": web_results,
            "used_web": bool(web_results),
            "best_score": best_score,
        }
