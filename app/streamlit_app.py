"""PersonalAI — local chat UI (Streamlit).

A thin front-end over the existing RAG engine. Nothing leaves your machine except
an optional web-search query when the web fallback is enabled.

Run it from the repo root:

    pip install -r requirements-ui.txt
    streamlit run app/streamlit_app.py

Notes-first behaviour, citations, image (vision) questions and a one-click
"re-scan notes folder" are all wired to the same components the CLI uses.
"""
from __future__ import annotations

import json
import pathlib
import sys
import tempfile
from datetime import datetime
from uuid import uuid4

import streamlit as st

# Make `src` importable when Streamlit runs this file directly.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from src.assistant import build_assistant  # noqa: E402


@st.cache_resource(show_spinner="Loading models and index…")
def get_assistant(config_path: str | None = None):
    """Build the assistant once and reuse it across reruns (it is expensive)."""
    return build_assistant(config_path)


def _save_upload(uploaded) -> str:
    """Persist an uploaded image to a temp file and return its path."""
    suffix = pathlib.Path(uploaded.name).suffix or ".png"
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp.write(uploaded.getbuffer())
    tmp.close()
    return tmp.name


def _conversations_dir(cfg) -> pathlib.Path:
    base = pathlib.Path(cfg.path("paths.index_dir", "storage/index")).parent
    directory = base / "conversations"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _list_conversations(cfg) -> list[dict]:
    items: list[dict] = []
    for path in _conversations_dir(cfg).glob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        items.append(
            {
                "id": path.stem,
                "title": data.get("title") or "Untitled",
                "updated_at": data.get("updated_at", ""),
            }
        )
    return sorted(items, key=lambda x: x["updated_at"], reverse=True)


def _load_conversation(cfg, conv_id: str) -> list[dict]:
    path = _conversations_dir(cfg) / f"{conv_id}.json"
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8")).get("messages", [])
    except Exception:
        return []


def _save_conversation(cfg, conv_id: str, messages: list[dict]) -> None:
    clean = [
        {"role": m["role"], "content": m["content"]}
        for m in messages
        if m.get("content")
    ]
    if not clean:
        return
    title = next((m["content"] for m in clean if m["role"] == "user"), "New chat")
    title = (title[:48] + "\u2026") if len(title) > 48 else title
    payload = {
        "title": title,
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "messages": clean,
    }
    (_conversations_dir(cfg) / f"{conv_id}.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8"
    )


def _delete_conversation(cfg, conv_id: str) -> None:
    (_conversations_dir(cfg) / f"{conv_id}.json").unlink(missing_ok=True)


def _render_sources(result: dict) -> None:
    sources = result.get("sources", [])
    used_web = result.get("used_web")
    best = result.get("best_score", 0.0) or 0.0
    caption = ("web used" if used_web else "notes only") + f" · best note score {best:.3f}"

    if not sources:
        st.caption(caption)
        return

    with st.expander(f"Sources ({len(sources)}) — {caption}"):
        for src in sources:
            if src.get("kind") == "note":
                loc = f" · {src['location']}" if src.get("location") else ""
                st.markdown(
                    f"**{src['ref']}** 📝 {src['name']}{loc} "
                    f"<span style='color:gray'>(score {src.get('score')})</span>",
                    unsafe_allow_html=True,
                )
            else:
                url = src.get("url", "")
                name = src.get("name", url)
                st.markdown(f"**{src['ref']}** 🌐 [{name}]({url})")


def main() -> None:
    st.set_page_config(page_title="PersonalAI", layout="centered")
    st.markdown(
        "<p style='text-align:center; font-size:1.45rem; font-weight:600; "
        "margin:0.4rem 0 1.4rem 0;'>Your notes, answered locally — with web as a fallback.</p>",
        unsafe_allow_html=True,
    )

    assistant = get_assistant()
    engine = assistant.engine
    cfg = assistant.cfg

    if "conversation_id" not in st.session_state:
        st.session_state.conversation_id = uuid4().hex
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # ---- Sidebar: controls -------------------------------------------------
    with st.sidebar:
        st.header("Settings")

        web_mode = st.radio(
            "Web search",
            options=["Auto", "Notes only", "Always (force)"],
            index=0,
            help=(
                "Auto: search the web only when your notes look weak.\n"
                "Notes only: never search the web.\n"
                "Always: search the web in addition to your notes."
            ),
        )

        uploaded = st.file_uploader(
            "Attach an image (optional)",
            type=["png", "jpg", "jpeg", "webp", "bmp", "gif", "tiff"],
            help="Ask a question about a screenshot or photo using the vision model.",
        )
        if uploaded is not None:
            st.image(uploaded, caption="Will be sent with your next question", use_container_width=True)

        st.divider()

        try:
            count = assistant.store.count()
        except Exception:
            count = "?"
        data_dir = cfg.path("paths.data_dir", "data/corpus")
        st.metric("Indexed chunks", count)
        st.caption(f"Notes folder:\n`{data_dir}`")

        if st.button("🔄 Re-scan notes folder", use_container_width=True):
            with st.spinner("Scanning for new or changed files…"):
                stats = assistant.pipeline.ingest_path(data_dir)
            st.success(
                f"Ingested {stats['ingested']} · skipped {stats['skipped']} · "
                f"failed {stats['failed']} · +{stats['chunks']} chunks"
            )

        st.divider()
        st.subheader("Conversations")
        if st.button("➕ New conversation", use_container_width=True):
            _save_conversation(cfg, st.session_state.conversation_id, st.session_state.messages)
            st.session_state.conversation_id = uuid4().hex
            st.session_state.messages = []
            st.rerun()

        for conv in _list_conversations(cfg):
            is_current = conv["id"] == st.session_state.conversation_id
            row = st.columns([0.82, 0.18])
            label = ("• " if is_current else "") + conv["title"]
            if row[0].button(label, key=f"load_{conv['id']}", use_container_width=True):
                _save_conversation(cfg, st.session_state.conversation_id, st.session_state.messages)
                st.session_state.conversation_id = conv["id"]
                st.session_state.messages = _load_conversation(cfg, conv["id"])
                st.rerun()
            if row[1].button("🗑", key=f"del_{conv['id']}", help="Delete this conversation"):
                _delete_conversation(cfg, conv["id"])
                if is_current:
                    st.session_state.conversation_id = uuid4().hex
                    st.session_state.messages = []
                st.rerun()

    # ---- Map UI controls to engine flags -----------------------------------
    use_web = None
    force_web = False
    if web_mode == "Notes only":
        use_web = False
    elif web_mode == "Always (force)":
        use_web = True
        force_web = True

    # ---- Chat history ------------------------------------------------------
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("result"):
                _render_sources(msg["result"])

    # ---- Input -------------------------------------------------------------
    prompt = st.chat_input("Ask about your notes…")
    if not prompt:
        return

    image_path = _save_upload(uploaded) if uploaded is not None else None

    # Conversation context = everything said so far (before this new turn).
    history = [
        {"role": m["role"], "content": m["content"]}
        for m in st.session_state.messages
    ]

    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking…"):
            try:
                result = engine.answer(
                    prompt, use_web=use_web, image=image_path,
                    force_web=force_web, history=history,
                )
                answer = result.get("answer", "").strip()
            except Exception as exc:  # surface errors instead of crashing the UI
                result = None
                answer = f"⚠️ Error: {exc}"
        st.markdown(answer)
        if result:
            _render_sources(result)

    st.session_state.messages.append(
        {"role": "assistant", "content": answer, "result": result}
    )
    _save_conversation(cfg, st.session_state.conversation_id, st.session_state.messages)


if __name__ == "__main__":
    main()
