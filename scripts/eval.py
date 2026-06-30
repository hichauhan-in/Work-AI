"""Evaluate retrieval + answers against a small question set.

The eval file is JSONL; one JSON object per line:

    {"question": "How do I analyze a bugcheck 0x9F?", "expect_source": "windbg"}
    {"question": "What does netsh winsock reset do?", "expect_source": "networking"}

``expect_source`` is a case-insensitive substring matched against retrieved note
filenames; a "retrieval hit" means at least one retrieved chunk came from a matching file.

Usage
-----
    python scripts/eval.py --file data/sample/eval_set.jsonl
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from src.assistant import build_assistant  # noqa: E402


def load_eval(path: pathlib.Path) -> list[dict]:
    items: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            items.append(json.loads(line))
    return items


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate PersonalAI retrieval/answers.")
    parser.add_argument(
        "--file", default="data/sample/eval_set.jsonl", help="Path to a JSONL eval set."
    )
    parser.add_argument("--no-web", action="store_true", help="Disable web during eval.")
    parser.add_argument("--show-answers", action="store_true", help="Print full answers.")
    parser.add_argument("--config", default=None, help="Path to a config file.")
    args = parser.parse_args()

    eval_path = pathlib.Path(args.file)
    if not eval_path.is_absolute():
        eval_path = pathlib.Path(__file__).resolve().parent.parent / eval_path
    if not eval_path.exists():
        print(f"ERROR: eval file not found: {eval_path}")
        return 1

    assistant = build_assistant(args.config)
    engine = assistant.engine
    items = load_eval(eval_path)

    hits = 0
    print(f"Running {len(items)} eval question(s) from {eval_path.name}\n")
    for i, item in enumerate(items, start=1):
        question = item["question"]
        expect = (item.get("expect_source") or "").lower()
        result = engine.answer(question, use_web=False if args.no_web else None)

        note_files = [
            str(n.metadata.get("filename", "")).lower() for n in result.get("notes", [])
        ]
        hit = bool(expect) and any(expect in f for f in note_files)
        hits += 1 if hit else 0

        status = "HIT " if hit else ("MISS" if expect else "n/a ")
        print(f"[{i:>2}] {status} score={result.get('best_score', 0):.3f}  {question}")
        if expect:
            print(f"      expected '{expect}' in: {note_files}")
        if args.show_answers:
            print("      " + result["answer"].strip().replace("\n", "\n      "))

    scored = sum(1 for it in items if it.get("expect_source"))
    if scored:
        print(f"\nRetrieval hit rate: {hits}/{scored} = {hits / scored:.0%}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
