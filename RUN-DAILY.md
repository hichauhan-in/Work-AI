# PersonalAI — Daily Run Guide

The short, everyday version. For first-time setup (installing Ollama, models, Tesseract,
SearXNG, etc.) see [INSTRUCTIONS.md](INSTRUCTIONS.md).

---

## TL;DR — one command

From the repo root on the runtime machine:

```powershell
.\start.ps1
```

That single launcher:
1. Starts **Docker Desktop** if needed and ensures **SearXNG** (web search) is running.
2. Verifies **Ollama** is reachable.
3. Opens the **chat UI** at <http://localhost:8501>.

Press `Ctrl+C` in the terminal to stop the UI. Close the browser tab when done.

> First launch after a reboot is slower while Docker starts and the models load into the
> GPU on your first question. Later questions are faster.

### Launcher options

| Command | What it does |
|---|---|
| `.\start.ps1` | Web search + chat UI (the normal way). |
| `.\start.ps1 -NoWeb` | Skip Docker/SearXNG — notes-only session. |
| `.\start.ps1 -Cli` | Interactive **terminal** chat instead of the web UI. |
| `.\start.ps1 -Check` | Run the environment health check and exit. |

---

## What starts automatically vs. manually

| Component | On machine startup | Notes |
|---|---|---|
| **Ollama** | Auto (Windows service) | Usually already running; shared server. |
| **SearXNG** | Auto *once Docker is up* | Container has `restart: unless-stopped`. The launcher starts Docker for you. |
| **venv + UI** | Manual | `.\start.ps1` handles both. |

So in practice you only run `.\start.ps1`.

---

## Manual equivalent (if you prefer)

```powershell
cd C:\Temp\Work-AI
.venv\Scripts\Activate.ps1                                   # prompt shows (.venv)
docker compose -f searxng\docker-compose.yml up -d           # web search (optional)
streamlit run app\streamlit_app.py                           # chat UI
```

---

## Adding or updating notes

Your index persists on disk — you do **not** re-ingest every day. Only when you add or
change files:

1. Drop files into the corpus folder (subfolders are fine):
   `C:\Temp\Work-AI\data\corpus`
2. Re-index — either:
   - Click **🔄 Re-scan notes folder** in the UI sidebar, or
   - Run `python scripts/ingest.py`

Only new or changed files are processed (an internal manifest tracks content hashes).

---

## Asking questions

In the **UI** (sidebar controls):
- **Web search** — *Auto* (web only if notes are weak), *Notes only*, or *Always (force)*.
- **Attach an image** — ask about a screenshot using the vision model.
- Answers show **source citations**: which notes (with scores) and any web results.

From the **CLI** instead:
```powershell
python scripts/query.py "How do I analyze a bugcheck 0x9F crash dump?"
python scripts/query.py "Summarise my DNS notes" --no-web        # notes only
python scripts/query.py "Any newer guidance on this CVE?" --force-web
python scripts/query.py "What does this error mean?" --image "C:/Captures/shot.png"
python scripts/query.py --interactive
```

---

## Quick troubleshooting

| Symptom | Fix |
|---|---|
| `streamlit` not recognized | venv not active / deps missing: `.venv\Scripts\Activate.ps1` then `pip install -r requirements-ui.txt`. |
| UI loads but answers fail | Ollama not running — check `http://127.0.0.1:11434`. The launcher reports this. |
| No web results | Docker/SearXNG down — `docker ps` should list `searxng`; start with `docker compose -f searxng\docker-compose.yml up -d`. |
| Image text not read | Tesseract missing — auto-detected at the standard path; otherwise set `ocr.tesseract_cmd` in `config.yaml`. |
| Anything else | `.\start.ps1 -Check` (full health check). |
