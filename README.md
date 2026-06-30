# PersonalAI

A private, local, **notes-first** AI assistant. It answers from your own documents and
images (RAG), falls back to the web only when your notes are insufficient, can read
screenshots (vision/OCR), and grows as you add more notes — all running on your own
hardware.

- **Plan & design:** [PersonalAI-Plan.md](PersonalAI-Plan.md)
- **How to run it on the runtime machine:** [INSTRUCTIONS.md](INSTRUCTIONS.md) ← start here

## What it does

- Ingests **many formats**: `.pdf` (incl. OneNote-exported PDF), `.docx`, `.pptx`,
  `.xlsx`, `.html`, `.rtf`, `.md`/`.txt`/`.csv`, and images (`.png/.jpg/...`) via OCR.
  Video is a planned bonus.
- Retrieves the most relevant chunks of **your** notes and answers with **citations**.
- Uses a local LLM via **Ollama**; embeddings + a vector store (**ChromaDB**) stay local.
- **Web fallback** via a self-hosted **SearXNG** (only the search query leaves the machine).
- **Vision**: attach a screenshot and ask about it.

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

## Project layout

```
src/        core library (config, ingestion, RAG, web, vision wiring)
scripts/    CLIs: check_env, ingest, query, eval
tests/      unit + smoke tests (no GPU needed)
data/sample tiny committed demo notes
```

## Run the tests (dev machine, no GPU needed)

```bash
pip install -r requirements-dev.txt
pytest -q
```
