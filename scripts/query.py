"""Ask PersonalAI a question (notes-first, web-second).

Examples
--------
    # One-off question:
    python scripts/query.py "How do I analyze a bugcheck 0x9F crash dump?"

    # Attach an image (screenshot) for the vision model to read:
    python scripts/query.py "What does this error mean?" --image shot.png

    # Notes only, no web fallback:
    python scripts/query.py "Summarise my DNS notes" --no-web

    # Always search the web too, even if the notes are strong:
    python scripts/query.py "Any newer guidance than my notes on CVE-2024-XXXX?" --force-web

    # Interactive chat loop:
    python scripts/query.py --interactive
"""
from __future__ import annotations

import argparse
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from src.assistant import build_assistant  # noqa: E402


def _print_result(result: dict) -> None:
    print("\n" + "=" * 70)
    print(result["answer"].strip())
    print("=" * 70)

    sources = result.get("sources", [])
    if sources:
        print("Sources:")
        for src in sources:
            if src["kind"] == "note":
                loc = f" {src['location']}" if src.get("location") else ""
                print(f"  {src['ref']} note: {src['name']}{loc} (score {src.get('score')})")
            else:
                print(f"  {src['ref']} web: {src.get('name','')} — {src.get('url','')}")
    flags = []
    flags.append("web used" if result.get("used_web") else "notes only")
    flags.append(f"best note score {result.get('best_score', 0):.3f}")
    print("(" + ", ".join(flags) + ")")


def _run_once(engine, question: str, use_web, image, force_web, history=None) -> dict:
    result = engine.answer(
        question, use_web=use_web, image=image, force_web=force_web, history=history
    )
    _print_result(result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Query PersonalAI.")
    parser.add_argument("question", nargs="*", help="Your question.")
    parser.add_argument("--image", default=None, help="Path to an image to analyse.")
    parser.add_argument("--no-web", action="store_true", help="Disable web fallback.")
    parser.add_argument("--web", action="store_true", help="Enable the auto web fallback.")
    parser.add_argument(
        "--force-web",
        action="store_true",
        help="Always search the web, even if the notes are strong.",
    )
    parser.add_argument("--interactive", action="store_true", help="Start a chat loop.")
    parser.add_argument("--config", default=None, help="Path to a config file.")
    args = parser.parse_args()

    use_web = None
    if args.no_web:
        use_web = False
    elif args.web:
        use_web = True

    assistant = build_assistant(args.config)
    engine = assistant.engine

    if args.interactive:
        print("PersonalAI interactive mode. Type 'exit' or Ctrl-C to quit.")
        history: list[dict] = []
        try:
            while True:
                question = input("\nyou> ").strip()
                if question.lower() in {"exit", "quit", ":q"}:
                    break
                if not question:
                    continue
                result = _run_once(engine, question, use_web, None, args.force_web, history)
                history.append({"role": "user", "content": question})
                history.append({"role": "assistant", "content": result["answer"]})
        except (KeyboardInterrupt, EOFError):
            print("\nbye")
        return 0

    question = " ".join(args.question).strip()
    if not question:
        parser.error("Provide a question, or use --interactive.")
    _run_once(engine, question, use_web, args.image, args.force_web)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
