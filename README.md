# Indexer

A private, local, **notes-first** AI assistant. It answers from your own documents and
images (RAG), falls back to the web only when your notes are insufficient, can read
screenshots (vision/OCR), and grows as you add more notes — all running on your own
hardware.

- **Plan & design:** [PersonalAI-Plan.md](PersonalAI-Plan.md)
- **First-time setup (runtime machine):** [INSTRUCTIONS.md](INSTRUCTIONS.md) ← start here
- **Everyday use:** [RUN-DAILY.md](RUN-DAILY.md)

## What it does

- Ingests **many formats**: `.pdf` (incl. OneNote-exported PDF), `.docx`, `.pptx`,
  `.xlsx`, `.html`, `.rtf`, `.md`/`.txt`/`.csv`, and images (`.png/.jpg/...`) via OCR.
  Video is a planned bonus.
- Retrieves the most relevant chunks of **your** notes and answers with **citations**.
- Uses a local LLM via **Ollama**; embeddings + a vector store (**ChromaDB**) stay local.
- **Web fallback** via a self-hosted **SearXNG** (only the search query leaves the machine).
- **Vision**: attach a screenshot and ask about it.
- **Chat UI** (Streamlit) plus CLIs — use whichever you prefer.

## Two-machine workflow

This repo is written on a **code-only machine** and executed on a separate **GPU runtime
machine** (Ryzen 7 7800X3D + RX 7900 XT). Code is synced via Git; your data, models, and
the index stay on the runtime machine and are git-ignored.

```
dev machine  --git push-->  GitHub  --git pull-->  runtime machine (runs everything)
```

## Quick start (on the runtime machine)

```bash
python -m venv .venv
# Windows: .venv\Scripts\Activate.ps1   |   Linux: source .venv/bin/activate
pip install -r requirements.txt
cp config.example.yaml config.yaml          # then edit it
python scripts/check_env.py                 # verify prerequisites
python scripts/ingest.py --path data/sample # try the bundled demo notes
python scripts/query.py "What does netsh winsock reset do?"
```

Full, detailed setup (Ollama, models, Tesseract, SearXNG, troubleshooting) is in
[INSTRUCTIONS.md](INSTRUCTIONS.md).

## Everyday use

After setup, one command starts Docker/SearXNG, checks Ollama, and opens the chat UI:

```powershell
.\start.ps1                 # web search + chat UI at http://localhost:8501
.\start.ps1 -NoWeb          # notes-only session
.\start.ps1 -Cli            # interactive terminal chat
.\start.ps1 -Check          # environment health check
```

Or launch the UI directly: `streamlit run app/streamlit_app.py`. See [RUN-DAILY.md](RUN-DAILY.md).

## Project layout

```
src/        core library (config, ingestion, RAG, web, vision wiring)
scripts/    CLIs: check_env, ingest, query, eval
app/        Streamlit chat UI
searxng/    Docker compose + settings for local web search
tests/      unit + smoke tests (no GPU needed)
data/sample tiny committed demo notes
start.ps1   daily launcher (Docker + Ollama check + UI)
```

## Run the tests (dev machine, no GPU needed)

```bash
pip install -r requirements-dev.txt
pytest -q
```
