"""The query engine: notes-first retrieval, optional web fallback, then the LLM.

Flow:
  1. (optional) describe an attached image with the vision model and append to the query.
  2. resolve follow-ups against the conversation into a standalone query (condensing).
  3. plan retrieval: fan the request out into several focused sub-queries (multi-query) so
     associated commands / procedures / related scenarios in the notes are surfaced, then
     embed each, retrieve top-k, and merge keeping the best score per unique chunk.
  4. consult the web when forced, when notes look weak, or when an in-depth answer is asked
     for (and web is enabled).
  5. assemble context + citations, include recent conversation, and ask the chat model
     (which is instructed to reason step by step on troubleshooting scenarios).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from ..logging_setup import get_logger
from ..schema import RetrievedChunk
from .prompts import (
    build_condense_messages,
    build_context,
    build_expand_messages,
    build_messages,
)

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
        history_messages: int = 8,
        condense_followups: bool = True,
        multi_query: bool = True,
        max_subqueries: int = 4,
    ):
        self.store = store
        self.llm = llm  # OllamaClient: used for both embeddings and chat/vision
        self.web = web
        self.top_k = top_k
        self.score_threshold = score_threshold
        self.web_enabled = web_enabled
        self.history_messages = history_messages
        self.condense_followups = condense_followups
        self.multi_query = multi_query
        self.max_subqueries = max_subqueries

    @classmethod
    def from_config(cls, cfg, store, llm, web=None) -> "RagEngine":
        return cls(
            store=store,
            llm=llm,
            web=web,
            top_k=int(cfg.get("retrieval.top_k", 6)),
            score_threshold=float(cfg.get("retrieval.score_threshold", 0.35)),
            web_enabled=bool(cfg.get("web.enabled", True)),
            history_messages=int(cfg.get("conversation.history_messages", 8)),
            condense_followups=bool(cfg.get("conversation.condense_followups", True)),
            multi_query=bool(cfg.get("retrieval.multi_query", True)),
            max_subqueries=int(cfg.get("retrieval.max_subqueries", 4)),
        )

    def answer(
        self,
        question: str,
        use_web: bool | None = None,
        image: str | Path | None = None,
        force_web: bool = False,
        history: list[dict] | None = None,
    ) -> dict[str, Any]:
        # Resolve follow-ups into a standalone query so retrieval/web see the real topic
        # (e.g. "explain that in more detail" -> "explain <previous topic> in more detail").
        standalone = question
        if history and self.condense_followups:
            standalone = self._condense_query(question, history)

        query_text = standalone
        if image:
            try:
                description = self.llm.describe_image(image)
                query_text = f"{standalone}\n\n[Attached image content]\n{description}"
                log.info("Vision model described the attached image.")
            except Exception as exc:
                log.warning("Could not analyse image %s: %s", image, exc)

        # Plan the lookups: a scenario fans out into several focused note queries so we
        # surface associated commands/procedures, not just a single literal match.
        queries = self._plan_queries(standalone, history)
        if image and query_text != standalone:
            queries = [query_text, *queries]
        notes = self._retrieve(queries)
        best_score = notes[0].score if notes else 0.0
        log.info(
            "Retrieved %d note chunk(s) from %d query/-ies; best score=%.3f",
            len(notes), len(queries), best_score,
        )

        want_web = self.web_enabled if use_web is None else use_web
        notes_weak = (not notes) or (best_score < self.score_threshold)
        wants_depth = self._wants_depth(question)
        # Web fires when forced, or (auto mode) when the notes are too weak OR the user is
        # explicitly asking for an in-depth answer that the notes may only cover generically.
        should_search = bool(force_web) or (want_web and (notes_weak or wants_depth))
        web_results: list[dict] = []
        if should_search and self.web is not None:
            if force_web:
                reason = "user requested"
            elif notes_weak:
                reason = "notes look weak"
            else:
                reason = "in-depth request"
            log.info("Querying the web (%s) for: %s", reason, standalone)
            web_results = self.web.search(standalone)

        context, sources = build_context(notes, web_results)
        messages = build_messages(query_text, context, history, self.history_messages)
        answer_text = self.llm.chat(messages)

        return {
            "answer": answer_text,
            "sources": sources,
            "notes": notes,
            "web": web_results,
            "used_web": bool(web_results),
            "best_score": best_score,
            "standalone_query": standalone if standalone != question else None,
        }

    # --- intent / follow-up helpers ------------------------------------------
    _DEPTH_KEYWORDS = (
        "in-depth", "in depth", "deep dive", "deep-dive", "comprehensive",
        "thorough", "thoroughly", "elaborate", "in detail", "detailed explanation",
        "full explanation", "fully explain", "exhaustive", "deep understanding",
    )

    @classmethod
    def _wants_depth(cls, question: str) -> bool:
        q = question.lower()
        return any(keyword in q for keyword in cls._DEPTH_KEYWORDS)

    def _condense_query(self, question: str, history: list[dict]) -> str:
        """Rewrite a follow-up into a standalone query; fall back to the original on failure."""
        try:
            condensed = self.llm.chat(build_condense_messages(question, history)).strip()
            if condensed and len(condensed) <= 400:
                log.info("Condensed follow-up to standalone query: %s", condensed)
                return condensed
        except Exception as exc:
            log.warning("Query condensation failed: %s", exc)
        return question

    def _plan_queries(self, standalone: str, history: list[dict] | None) -> list[str]:
        """Return the main query plus, when enabled, LLM-generated sub-queries that cover
        related concepts, commands and next steps in the user's notes."""
        queries = [standalone]
        # Skip expansion for very short, direct questions - they don't need fanning out.
        if not self.multi_query or len(standalone.split()) < 4:
            return queries
        try:
            raw = self.llm.chat(
                build_expand_messages(standalone, history, self.max_subqueries)
            )
            for line in raw.splitlines():
                sub = line.strip().lstrip("-*0123456789.) ").strip()
                if sub and sub.lower() != standalone.lower() and sub not in queries:
                    queries.append(sub)
                if len(queries) >= self.max_subqueries + 1:
                    break
        except Exception as exc:
            log.warning("Query expansion failed: %s", exc)
        if len(queries) > 1:
            log.info("Expanded into sub-queries: %s", queries[1:])
        return queries

    def _retrieve(self, queries: list[str]) -> list[RetrievedChunk]:
        """Retrieve for each query and merge, keeping the best score per unique chunk."""
        best: dict[tuple, RetrievedChunk] = {}
        for query in queries:
            try:
                embedding = self.llm.embed(query)
            except Exception as exc:
                log.warning("Embedding failed for '%s': %s", query, exc)
                continue
            for chunk in self.store.query(embedding, self.top_k):
                key = (chunk.metadata.get("source", ""), chunk.text[:120])
                existing = best.get(key)
                if existing is None or chunk.score > existing.score:
                    best[key] = chunk
        merged = sorted(best.values(), key=lambda c: c.score, reverse=True)
        return merged[: self.top_k]
