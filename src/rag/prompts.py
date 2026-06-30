"""Prompt construction and source formatting for the RAG engine."""
from __future__ import annotations

from ..schema import RetrievedChunk

SYSTEM_PROMPT = (
    "You are PersonalAI, a private technical assistant for the user's own notes "
    "(focus areas: Windows networking and Windows debugging, but general-purpose).\n"
    "\n"
    "Rules:\n"
    "1. Answer PRIMARILY from the user's notes shown under CONTEXT. Cite note sources "
    "inline as [1], [2] matching their numbers.\n"
    "2. If the notes are insufficient and WEB RESULTS are provided, you may use them, but "
    "label that information as (web) and cite it as [W1], [W2].\n"
    "3. If the answer is not in the provided context at all, say clearly that it is not in "
    "the notes, then you may answer from general knowledge and label it as (general "
    "knowledge).\n"
    "4. Never invent citations or facts. If unsure, say so.\n"
    "5. Be concise, technical, and practical. Prefer concrete steps, commands, and checks."
)


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


def build_messages(question: str, context: str) -> list[dict]:
    user = f"CONTEXT:\n{context}\n\nQUESTION: {question}"
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user},
    ]
