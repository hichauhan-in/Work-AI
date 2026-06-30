"""Ingest a folder or single file into the vector store.

Examples
--------
    # Ingest everything under the configured data_dir (incremental):
    python scripts/ingest.py

    # Ingest a specific folder or file:
    python scripts/ingest.py --path "data/corpus/networking"
    python scripts/ingest.py --path "C:/Notes/export.pdf"

    # Force re-ingest everything from scratch:
    python scripts/ingest.py --reset
"""
from __future__ import annotations

import argparse
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from src.assistant import build_assistant  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest documents/images into PersonalAI.")
    parser.add_argument(
        "--path",
        default=None,
        help="File or folder to ingest (default: paths.data_dir from config).",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Clear the vector store and manifest before ingesting.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-ingest files even if unchanged (ignore the manifest).",
    )
    parser.add_argument("--config", default=None, help="Path to a config file.")
    args = parser.parse_args()

    assistant = build_assistant(args.config)
    target = args.path or assistant.cfg.path("paths.data_dir", "data/corpus")

    target_path = pathlib.Path(target)
    if not target_path.exists():
        print(f"ERROR: path does not exist: {target_path}")
        print("Put your notes under the configured data_dir, or pass --path.")
        return 1

    stats = assistant.pipeline.ingest_path(target_path, reset=args.reset, force=args.force)
    print(
        "\nIngestion complete: "
        f"{stats['ingested']} ingested, {stats['skipped']} skipped, "
        f"{stats['failed']} failed, {stats['chunks']} new chunks."
    )
    return 0 if stats["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
