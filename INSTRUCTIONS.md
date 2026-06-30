# PersonalAI — Setup & Run Instructions (Runtime Machine)

This is the complete, step-by-step runbook for getting PersonalAI working on your
**runtime machine** (the one with the Ryzen 7 7800X3D + Radeon RX 7900 XT). Follow the
sections in order. Commands are given for **Windows (PowerShell)** and **Linux (bash)** —
use whichever OS that machine runs.

> Reminder on the workflow: code is written on the *dev* machine and pushed to GitHub.
> On the *runtime* machine you `git pull`, then run everything here. Your notes, models,
> and the search index never leave the runtime machine (they are git-ignored).

---

## Table of contents

1. [Prerequisites overview](#1-prerequisites-overview)
2. [Install Git](#2-install-git)
3. [Install Python 3.11+](#3-install-python-311)
4. [Install Ollama + pull models (the AI engine)](#4-install-ollama--pull-models)
5. [Install Tesseract OCR (for images)](#5-install-tesseract-ocr)
6. [(Optional) Install ffmpeg (video bonus)](#6-optional-install-ffmpeg)
7. [(Optional) Run SearXNG for local web search](#7-optional-run-searxng-for-local-web-search)
8. [Get the code & create a virtual environment](#8-get-the-code--create-a-virtual-environment)
9. [Install Python dependencies](#9-install-python-dependencies)
10. [Create and edit your config](#10-create-and-edit-your-config)
11. [Verify everything with the environment check](#11-verify-everything)
12. [Add your notes and ingest them](#12-add-your-notes-and-ingest-them)
13. [Ask questions](#13-ask-questions)
14. [Keep it evolving (adding new notes later)](#14-keep-it-evolving)
15. [Evaluate quality](#15-evaluate-quality)
16. [Troubleshooting](#16-troubleshooting)
17. [Dev → runtime sync loop](#17-dev--runtime-sync-loop)

---

## 1. Prerequisites overview

| Prerequisite | Required? | Purpose |
|---|---|---|
| Git | Yes | Pull the code from GitHub |
| Python 3.11+ | Yes | Runs the application |
| Ollama + models | Yes | Local LLM, embeddings, vision |
| Tesseract OCR | Recommended | Read text from screenshots/images |
| Docker + SearXNG | Optional | Private local web search fallback |
| ffmpeg + faster-whisper | Optional | Video ingestion (bonus) |

You can get a fully working text+notes assistant with just the first three. OCR, web, and
video are additive — enable them when you want.

---

## 2. Install Git

- **Windows:** download from <https://git-scm.com/download/win> and install (accept
  defaults). Verify:
  ```powershell
  git --version
  ```
- **Linux (Debian/Ubuntu):**
  ```bash
  sudo apt update && sudo apt install -y git
  git --version
  ```

---

## 3. Install Python 3.11+

- **Windows:** install from <https://www.python.org/downloads/> (3.11 or 3.12). **Check
  "Add python.exe to PATH"** during setup. Verify:
  ```powershell
  python --version
  ```
- **Linux (Debian/Ubuntu):**
  ```bash
  sudo apt install -y python3 python3-venv python3-pip
  python3 --version
  ```

> If `python` isn't found on Linux, use `python3` everywhere below.

---

## 4. Install Ollama + pull models

Ollama serves the local models and uses your **AMD GPU** automatically when supported. The
RX 7900 XT (gfx1100) is supported.

### Install

- **Windows:** download the installer from <https://ollama.com/download> and run it.
  Ollama runs as a background service at `http://localhost:11434`.
- **Linux:**
  ```bash
  curl -fsSL https://ollama.com/install.sh | sh
  ```

### Verify it's running and using the GPU

```powershell
ollama --version
ollama ps        # shows loaded models; PROCESSOR column should say "GPU" once a model runs
```

### Pull the models

These match the defaults in `config.example.yaml`. Run on the runtime machine (downloads
several GB total):

```powershell
ollama pull qwen2.5:14b          # primary chat model (fits your 20 GB VRAM)
ollama pull nomic-embed-text     # embeddings for retrieval
ollama pull qwen2.5vl:7b         # vision (image understanding / OCR fallback)
```

Notes / alternatives:
- Tighter on VRAM or want speed? Use `qwen2.5:7b` or `llama3.1:8b` and set it as
  `ollama.chat_model` in `config.yaml`.
- Want maximum quality and OK with slower replies? Try `qwen2.5:32b` (Q4-sized).
- If `qwen2.5vl:7b` isn't available in your Ollama version, use `llava:13b` instead and set
  `ollama.vision_model: "llava:13b"`.

Quick manual test:
```powershell
ollama run qwen2.5:14b "Say hello in one short sentence."
```

> **AMD GPU note:** Ollama ships with the runtime it needs. If it falls back to CPU (slow),
> see [Troubleshooting](#16-troubleshooting). On Linux you can confirm GPU use with
> `rocm-smi` while a model is loaded.

---

## 5. Install Tesseract OCR

Needed to extract text from images and screenshot-heavy PDFs/Word docs. The Python
`pytesseract` package (installed later) needs this **system binary**.

- **Windows:** install the build from
  <https://github.com/UB-Mannheim/tesseract/wiki>. Default install path:
  `C:\Program Files\Tesseract-OCR\tesseract.exe`. You will put this path into
  `config.yaml` (step 10). Verify:
  ```powershell
  & "C:\Program Files\Tesseract-OCR\tesseract.exe" --version
  ```
- **Linux (Debian/Ubuntu):**
  ```bash
  sudo apt install -y tesseract-ocr
  tesseract --version
  ```
  On Linux the binary is on PATH, so you can leave `ocr.tesseract_cmd` empty in config.

> If you skip Tesseract, set `ocr.enabled: false` in config. Images will be ignored, but
> everything else still works.

---

## 6. (Optional) Install ffmpeg

Only needed for the **video bonus**. Provides audio extraction for transcription.

- **Windows:** `winget install Gyan.FFmpeg` (or download from <https://ffmpeg.org>), then
  reopen the terminal and check `ffmpeg -version`.
- **Linux:** `sudo apt install -y ffmpeg`

Then install the optional Python deps: `pip install -r requirements-video.txt`.

---

## 7. (Optional) Run SearXNG for local web search

This keeps web-search queries on your machine. Easiest via Docker.

1. Install Docker Desktop (Windows) or Docker Engine (Linux).
2. Run SearXNG with the JSON API enabled (PersonalAI needs JSON output):

   ```bash
   docker run -d --name searxng -p 8888:8080 \
     -e "SEARXNG_SETTINGS_PATH=/etc/searxng/settings.yml" \
     -v "$PWD/searxng:/etc/searxng" \
     searxng/searxng:latest
   ```

3. Enable the JSON format. Edit `searxng/settings.yml` (created on first run) and ensure:

   ```yaml
   search:
     formats:
       - html
       - json
   ```

   Then restart: `docker restart searxng`.

4. Test the JSON endpoint:
   ```bash
   curl "http://localhost:8888/search?q=test&format=json"
   ```

In `config.yaml`, keep `web.provider: "searxng"` and `web.searxng_url: "http://localhost:8888"`.

> Prefer no setup? Set `web.provider: "duckduckgo"` and
> `pip install duckduckgo_search`. Or set `web.enabled: false` to stay 100% offline.

---

## 8. Get the code & create a virtual environment

```powershell
# Clone (first time only) — replace with your repo URL:
git clone https://github.com/<you>/PersonalAi.git
cd PersonalAi

# Create + activate a virtual environment
python -m venv .venv
```

Activate it:
- **Windows (PowerShell):**
  ```powershell
  .venv\Scripts\Activate.ps1
  ```
  If you get an execution-policy error:
  ```powershell
  Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
  .venv\Scripts\Activate.ps1
  ```
- **Linux:**
  ```bash
  source .venv/bin/activate
  ```

Your prompt should now show `(.venv)`.

---

## 9. Install Python dependencies

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Optional extras:
```powershell
pip install -r requirements-dev.txt     # to run the tests
pip install -r requirements-video.txt    # only if doing the video bonus
```

---

## 10. Create and edit your config

Copy the template (the real `config.yaml` is git-ignored):

```powershell
# Windows
Copy-Item config.example.yaml config.yaml
# Linux
cp config.example.yaml config.yaml
```

Open `config.yaml` and review:

- **`ollama.chat_model` / `vision_model` / `embed_model`** — must match what you pulled in
  step 4.
- **`ocr.tesseract_cmd`** — on **Windows**, set the full path, e.g.
  `"C:/Program Files/Tesseract-OCR/tesseract.exe"`. On **Linux**, leave it empty.
- **`web.enabled` / `web.searxng_url`** — turn web off if you didn't set up SearXNG.
- **`paths.data_dir`** — where your notes live (default `data/corpus`).

---

## 11. Verify everything

Run the environment checker. It prints a PASS/WARN/FAIL checklist:

```powershell
python scripts/check_env.py
```

- **FAIL** = must fix before continuing (e.g., a missing dependency, config error, Ollama
  not running).
- **WARN** = optional feature not ready (e.g., Tesseract or SearXNG) — fine to proceed.

Fix any FAIL items, then re-run until the summary says core checks passed.

---

## 12. Add your notes and ingest them

1. Put your exported notes into the data folder (default `data/corpus/`). Supported now:
   `.pdf` (including OneNote-exported PDF), `.docx`, `.pptx`, `.xlsx`, `.html`, `.rtf`,
   `.md`, `.txt`, `.csv`, and images `.png/.jpg/.jpeg/.bmp/.tif/.tiff/.gif/.webp`.
   Subfolders are fine — they're scanned recursively.

2. (Optional) First try the bundled demo notes to confirm the pipeline works:
   ```powershell
   python scripts/ingest.py --path data/sample
   ```

3. Ingest your real notes:
   ```powershell
   python scripts/ingest.py                       # ingests everything under data_dir
   python scripts/ingest.py --path "data/corpus/networking"   # or a specific folder/file
   ```

What happens: each file is parsed → screenshots/images OCR'd → text chunked → embedded →
stored in the local vector DB. A `manifest.json` records file hashes so re-running only
processes new/changed files.

Useful flags:
- `--reset` — wipe the index and start fresh.
- `--force` — re-ingest even unchanged files (e.g., after changing chunking settings).

> First ingest of a large, image-heavy corpus can take a while (OCR + embeddings). Watch
> the log output; progress is printed per file.

---

## 13. Ask questions

One-off question (notes-first, web only if notes are weak):
```powershell
python scripts/query.py "How do I analyze a bugcheck 0x9F crash dump?"
```

Attach a screenshot for the vision model to read:
```powershell
python scripts/query.py "What does this error indicate and what should I check?" --image "C:/Captures/windbg.png"
```

Notes only (no web), or force web on:
```powershell
python scripts/query.py "Summarise my DNS notes" --no-web
python scripts/query.py "Latest mitigations for this CVE" --web
```

Interactive chat loop:
```powershell
python scripts/query.py --interactive
```

Each answer prints **sources**: which of your notes (with page/slide and a relevance score)
and any web results were used, plus whether the web was consulted.

---

## 14. Keep it evolving

This is the whole point — adding knowledge is a *data* operation, never retraining.

- Drop new/updated files into `data/corpus/` and re-run:
  ```powershell
  python scripts/ingest.py
  ```
  Only new or changed files are processed (thanks to the manifest).
- Changed a file? Its old chunks are removed and replaced automatically.
- Want a scheduled refresh? Use **Task Scheduler** (Windows) or **cron** (Linux) to run
  `python scripts/ingest.py` nightly.

---

## 15. Evaluate quality

A small eval set lets you measure retrieval quality as you tune chunking, `top_k`, or
models. Edit `data/sample/eval_set.jsonl` (or make your own) with questions and the
expected source filename substring, then:

```powershell
python scripts/eval.py --file data/sample/eval_set.jsonl --show-answers
```

It reports a **retrieval hit rate** (did the right note get retrieved?) and can print the
answers for a manual quality read.

---

## 16. Troubleshooting

| Symptom | Fix |
|---|---|
| `check_env.py` shows `import X FAIL` | Activate the venv, then `pip install -r requirements.txt`. |
| "Config file not found" | You skipped step 10 — copy `config.example.yaml` to `config.yaml`. |
| "Ollama server reachable FAIL" | Ensure Ollama is installed/running. Windows: it runs as a service; Linux: `ollama serve`. Test `http://localhost:11434`. |
| Model WARN: "not pulled" | Run the `ollama pull <name>` for that model (step 4). |
| Answers are slow / GPU not used | Run `ollama ps` while querying; PROCESSOR should be GPU. Update AMD Adrenalin drivers. Try a smaller model (`qwen2.5:7b`). On Linux, confirm with `rocm-smi`. |
| Tesseract WARN / images ignored | Install Tesseract (step 5) and set `ocr.tesseract_cmd` on Windows; or set `ocr.enabled: false`. |
| OCR produces garbage on a PDF | The page may be low-res; re-export at higher DPI, or rely on the vision fallback (`ocr.vision_fallback: true`). |
| Web search returns nothing | Confirm SearXNG JSON is enabled (step 7) and `web.searxng_url` is correct; or switch `web.provider` to `duckduckgo`; or `web.enabled: false`. |
| "No relevant notes found" for known topics | You may not have ingested yet, or `retrieval.score_threshold` is too high. Run `ingest.py`, lower the threshold, or raise `retrieval.top_k`. |
| PowerShell won't activate venv | `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` then activate again. |
| Chroma/index acting strange after changing embed model | Embeddings from different models aren't comparable — run `python scripts/ingest.py --reset`. |

To get more detail, set `logging.level: "DEBUG"` in `config.yaml`. Logs are also written to
`storage/logs/personalai.log` — that file is handy to copy/paste back to the dev side when
reporting a failure.

---

## 17. Dev → runtime sync loop

Typical cycle once set up:

```bash
# On the runtime machine, whenever new code is pushed:
git pull
# (re-install only if requirements changed)
pip install -r requirements.txt
# run whatever you're testing
python scripts/check_env.py
python scripts/query.py "..."
```

When something fails, copy back to the dev side:
- the exact command you ran,
- the console output / traceback,
- the relevant tail of `storage/logs/personalai.log`.

That's enough to diagnose and push a fix. Your notes/index never need to leave the runtime
machine.
