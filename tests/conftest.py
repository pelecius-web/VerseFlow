"""conftest.py — Test configuration for VerseFlow.

Adds all source subdirectories to sys.path so test imports resolve correctly
after the v1.3.0 directory restructure (2. Source Code/ → src/).
"""
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"
for subdir in ("", "ui", "core", "display", "db", "ndi", "utils"):
    p = str(SRC / subdir) if subdir else str(SRC)
    if p not in sys.path:
        sys.path.insert(0, p)
