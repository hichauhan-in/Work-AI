"""PersonalAI — a local, notes-first RAG assistant.

This package is designed to be developed on one machine and executed on a separate
GPU runtime machine (synced via Git). All heavy/optional dependencies are imported
lazily inside functions so that pure-logic modules import cleanly for tests.
"""

__version__ = "0.1.0"
