"""Environment / prerequisite checker.

Run this FIRST on the runtime machine after `pip install` and editing config.yaml:

    python scripts/check_env.py

It verifies Python, dependencies, config, the Ollama server + required models, Tesseract,
and (if enabled) the SearXNG endpoint, printing a PASS/WARN/FAIL checklist. Exit code is
non-zero if a critical check fails.
"""
from __future__ import annotations

import importlib
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

OK = "PASS"
WARN = "WARN"
FAIL = "FAIL"

_results: list[tuple[str, str, str]] = []


def record(status: str, name: str, detail: str = "") -> None:
    _results.append((status, name, detail))
    print(f"  [{status}] {name}" + (f" — {detail}" if detail else ""))


def check_python() -> None:
    major, minor = sys.version_info[:2]
    detail = f"{major}.{minor}.{sys.version_info[2]}"
    record(OK if (major, minor) >= (3, 10) else FAIL, "Python >= 3.10", detail)


def check_imports() -> None:
    deps = {
        "yaml": "pyyaml",
        "dotenv": "python-dotenv",
        "requests": "requests",
        "ollama": "ollama",
        "chromadb": "chromadb",
        "fitz": "pymupdf",
        "docx": "python-docx",
        "pptx": "python-pptx",
        "openpyxl": "openpyxl",
        "bs4": "beautifulsoup4",
        "striprtf": "striprtf",
        "PIL": "pillow",
        "pytesseract": "pytesseract",
    }
    for module, package in deps.items():
        try:
            importlib.import_module(module)
            record(OK, f"import {module}", f"({package})")
        except Exception as exc:
            record(FAIL, f"import {module}", f"missing '{package}' — pip install -r requirements.txt ({exc})")


def check_config():
    try:
        from src.config import load_config

        cfg = load_config()
        record(OK, "config.yaml loads", str(cfg.path("paths.data_dir")))
        return cfg
    except Exception as exc:
        record(FAIL, "config.yaml loads", str(exc))
        return None


def check_ollama(cfg) -> None:
    if cfg is None:
        record(WARN, "Ollama server", "skipped (no config)")
        return
    try:
        from src.ollama_client import OllamaClient

        client = OllamaClient.from_config(cfg)
        available = client.list_models()
        record(OK, "Ollama server reachable", client.host)
    except Exception as exc:
        record(FAIL, "Ollama server reachable", f"{exc} — is `ollama serve` running?")
        return

    def model_present(name: str) -> bool:
        # Ollama tags may include ':latest'; match on the base name too.
        base = name.split(":")[0]
        return any(name == m or m.startswith(base) for m in available)

    for role in ("chat_model", "embed_model", "vision_model"):
        name = cfg.get(f"ollama.{role}")
        if not name:
            continue
        if model_present(name):
            record(OK, f"model: {name}", f"({role})")
        else:
            record(WARN, f"model: {name}", f"not pulled — run `ollama pull {name}`")


def check_tesseract(cfg) -> None:
    try:
        import pytesseract

        if cfg is not None:
            cmd = cfg.get("ocr.tesseract_cmd", "") or ""
            if cmd:
                pytesseract.pytesseract.tesseract_cmd = cmd
        version = pytesseract.get_tesseract_version()
        record(OK, "Tesseract OCR binary", f"v{version}")
    except Exception as exc:
        record(WARN, "Tesseract OCR binary", f"not found — image OCR will be skipped ({exc})")


def check_searxng(cfg) -> None:
    if cfg is None or not cfg.get("web.enabled", True):
        record(WARN, "Web search", "disabled in config")
        return
    provider = cfg.get("web.provider", "searxng")
    if provider != "searxng":
        record(WARN, "Web search", f"provider='{provider}' (not checked here)")
        return
    url = cfg.get("web.searxng_url", "http://localhost:8888").rstrip("/")
    try:
        import requests

        resp = requests.get(
            f"{url}/search", params={"q": "test", "format": "json"}, timeout=10
        )
        resp.raise_for_status()
        record(OK, "SearXNG reachable", url)
    except Exception as exc:
        record(WARN, "SearXNG reachable", f"{url} unreachable — web fallback off until fixed ({exc})")


def main() -> int:
    print("PersonalAI environment check\n" + "=" * 32)
    check_python()
    print("\nDependencies:")
    check_imports()
    print("\nConfiguration:")
    cfg = check_config()
    print("\nOllama:")
    check_ollama(cfg)
    print("\nOCR:")
    check_tesseract(cfg)
    print("\nWeb search:")
    check_searxng(cfg)

    fails = sum(1 for s, _, _ in _results if s == FAIL)
    warns = sum(1 for s, _, _ in _results if s == WARN)
    print("\n" + "=" * 32)
    print(f"Summary: {len(_results)} checks, {fails} FAIL, {warns} WARN")
    if fails:
        print("Resolve the FAIL items above before ingesting or querying.")
        return 1
    print("Core checks passed. WARN items are optional features you can enable later.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
