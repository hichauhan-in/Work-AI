"""Prompt construction and source formatting for the RAG engine."""
from __future__ import annotations

from ..schema import RetrievedChunk

SYSTEM_PROMPT = (
    "You are PersonalAI, a private technical assistant working primarily from the user's "
    "own notes (strong areas: Windows networking and Windows debugging, but general-purpose).\n"
    "\n"
    "How to answer:\n"
    "1. Understand the user's INTENT, not just keywords. Synthesize across the provided note "
    "chunks into one coherent, well-structured explanation instead of quoting isolated lines.\n"
    "2. Answer PRIMARILY from the notes under CONTEXT and cite them inline as [1], [2] by their "
    "numbers. Combine related chunks, and use the prior conversation to resolve follow-up "
    "references (it, that, the previous one).\n"
    "3. Match the requested depth. If the user asks for an in-depth or detailed explanation, "
    "give a thorough answer: background, how/why it works, concrete steps or commands, and "
    "common pitfalls.\n"
    "4. If the notes only partially cover the topic, say what the notes contain, then enrich "
    "the answer: use WEB RESULTS when provided (label as (web), cite [W1], [W2]) and/or "
    "clearly-labelled (general knowledge). Make explicit which parts come from the notes "
    "versus elsewhere.\n"
    "5. If the answer is not in the notes at all, say so plainly, then you may answer from "
    "general knowledge labelled as (general knowledge).\n"
    "6. Never invent citations or facts. If something is uncertain, say so.\n"
    "7. Be technical, accurate and practical; prefer concrete commands, steps and checks.\n"
    "8. SCENARIO / TROUBLESHOOTING tasks (e.g. analysing a crash dump): work step by step. "
    "Briefly outline the approach, then ask for the specific next input you need (such as the "
    "output of a command). When the user shares a command or its output, explain what that "
    "command does and what the output indicates based on the notes, then recommend the next "
    "step or command. Connect related procedures from the notes even when they are not an "
    "exact match, and don't dump everything at once - guide the user through it."
)

# Used to fan a request out into several focused note lookups (associated/related notes).
EXPAND_SYSTEM = (
    "You plan retrieval for a personal notes search engine. Given the user's latest request "
    "and the prior conversation, list the distinct things to look up in the notes to handle "
    "it well: the core concept, any specific commands / error codes / tools mentioned, and "
    "closely related procedures or likely next steps.\n"
    "Output between 2 and {max_queries} short search queries, ONE per line. No numbering, no "
    "quotes, no extra commentary."
)

# Used to rewrite a follow-up into a standalone search query using the prior turns.
CONDENSE_SYSTEM = (
    "You rewrite a user's latest message into a standalone search query.\n"
    "Use the conversation so pronouns and references (it, that, this, the previous one) "
    "become explicit and self-contained.\n"
    "Output ONLY the rewritten query text - no quotes, no preamble, no explanation. "
    "If the message is already self-contained, return it unchanged."
)

_MAX_HISTORY_MESSAGES = 8


def _location(metadata: dict) -> str:
    for key, label in (("page", "p."), ("slide", "slide "), ("sheet", "sheet ")):
        if metadata.get(key) is not None:
            return f", {label}{metadata[key]}"
    if metadata.get("content"):
        return f", {metadata['content']}"
    return ""


def build_context(
    note_chunks: list[RetrievedChunk], web_results: list[dict]
) -> tuple[str, list[dict]]:
    """Return (context_text, source_list) for prompting and display."""
    blocks: list[str] = []
    sources: list[dict] = []

    for i, chunk in enumerate(note_chunks, start=1):
        name = chunk.metadata.get("filename", "note")
        loc = _location(chunk.metadata)
        blocks.append(f"[{i}] (note: {name}{loc})\n{chunk.text}")
        sources.append(
            {
                "ref": f"[{i}]",
                "kind": "note",
                "name": name,
                "location": loc.lstrip(", "),
                "score": round(chunk.score, 3),
                "source": chunk.metadata.get("source", ""),
            }
        )

    for j, result in enumerate(web_results, start=1):
        title = result.get("title", "")
        url = result.get("url", "")
        content = result.get("content", "")
        blocks.append(f"[W{j}] (web: {url})\n{title}\n{content}")
        sources.append({"ref": f"[W{j}]", "kind": "web", "name": title, "url": url})

    if not blocks:
        return "(no relevant notes found)", sources
    return "\n\n".join(blocks), sources


def _history_to_text(history: list[dict] | None, limit: int = _MAX_HISTORY_MESSAGES) -> str:
    if not history:
        return ""
    lines: list[str] = []
    for turn in history[-limit:]:
        role = "User" if turn.get("role") == "user" else "Assistant"
        content = (turn.get("content") or "").strip()
        if content:
            lines.append(f"{role}: {content}")
    return "\n".join(lines)


def build_condense_messages(question: str, history: list[dict] | None) -> list[dict]:
    """Messages that ask the LLM to turn a follow-up into a standalone search query."""
    convo = _history_to_text(history)
    user = (
        f"Conversation so far:\n{convo}\n\n"
        f"Latest message: {question}\n\nStandalone search query:"
    )
    return [
        {"role": "system", "content": CONDENSE_SYSTEM},
        {"role": "user", "content": user},
    ]


def build_expand_messages(
    question: str, history: list[dict] | None, max_queries: int
) -> list[dict]:
    """Messages that ask the LLM to fan a request into several focused search queries."""
    convo = _history_to_text(history)
    convo_block = f"Conversation so far:\n{convo}\n\n" if convo else ""
    user = f"{convo_block}Latest request: {question}\n\nSearch queries (one per line):"
    return [
        {"role": "system", "content": EXPAND_SYSTEM.format(max_queries=max_queries)},
        {"role": "user", "content": user},
    ]


def build_messages(
    question: str,
    context: str,
    history: list[dict] | None = None,
    history_limit: int = _MAX_HISTORY_MESSAGES,
) -> list[dict]:
    messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]
    if history:
        for turn in history[-history_limit:]:
            role = turn.get("role")
            content = (turn.get("content") or "").strip()
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})
    user = f"CONTEXT:\n{context}\n\nQUESTION: {question}"
    messages.append({"role": "user", "content": user})
    return messages
