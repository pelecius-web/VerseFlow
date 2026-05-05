"""crossrefs.py — VerseFlow Cross-Reference Manager

Loads cross-reference data from JSON and provides lookups.
"""

import json
from pathlib import Path
from typing import Optional

DATA_DIR = Path(__file__).parent / "data"
CROSSREF_FILE = DATA_DIR / "cross_references.json"


class CrossRefManager:
    """Manages Bible cross-reference lookups."""

    def __init__(self):
        self._refs: dict[str, list[str]] = {}
        self._load()

    def _load(self):
        if not CROSSREF_FILE.exists():
            return
        try:
            with open(CROSSREF_FILE, encoding="utf-8") as f:
                data = json.load(f)
            self._refs = data.get("cross_references", {})
        except (json.JSONDecodeError, KeyError):
            pass

    def get_cross_refs(self, reference: str) -> list[str]:
        """Get cross-references for a given verse reference."""
        return self._refs.get(reference, [])

    def has_cross_refs(self, reference: str) -> bool:
        return reference in self._refs

    def count(self) -> int:
        return len(self._refs)
