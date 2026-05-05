"""Regression tests for UI-facing label cleanup and navigator load behavior."""

import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QApplication

# Add Source Code to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "2. Source Code"))

from editors import TranslationMenu
from display_window import DisplayWindow
from home_panel import DisplayPreview
from navigator import VerseNavigator


@pytest.fixture(scope="module")
def app():
    """Provide a QApplication for widget tests."""
    existing = QApplication.instance()
    if existing is not None:
        return existing
    return QApplication([])


class FakeDb:
    def get_translations(self):
        return ["English KJV", "NKJV"]

    def get_chapter_verses(self, book, chapter, translation=""):
        active = translation or "English KJV"
        return [
            {"id": 1, "book": book, "chapter": chapter, "verse": 1, "reference": f"{book} {chapter}:1", "text": "One", "translation": active},
            {"id": 2, "book": book, "chapter": chapter, "verse": 2, "reference": f"{book} {chapter}:2", "text": "Two", "translation": active},
        ]


class FakeSignal:
    def __init__(self):
        self._callbacks = []

    def connect(self, callback):
        self._callbacks.append(callback)


class FakeDisplay:
    def __init__(self):
        self.current = None
        self.secondary_translations = []
        self.verse_changed = FakeSignal()
        self.layout_changed = FakeSignal()
        self.translations_changed = FakeSignal()

    def push_verse(self, verse):
        self.current = verse


class FakeThemeManager:
    current = None


def test_translation_menu_abbreviates_english_kjv(app):
    menu = TranslationMenu(FakeDb())
    labels = [label.text() for _, _, label in menu.translation_items]
    assert "KJV" in labels
    assert "English KJV" not in labels


def test_preview_verse_abbreviates_translation(app):
    preview = DisplayPreview(FakeDisplay())
    preview.set_preview_verse({
        "reference": "John 3:16",
        "translation": "English KJV",
        "text": "For God so loved the world",
    })
    assert preview.ref_label.text() == "John 3:16 — KJV"


def test_live_preview_abbreviates_translation(app):
    display = FakeDisplay()
    preview = DisplayPreview(display)
    preview._on_verse_changed({
        "reference": "John 3:16",
        "translation": "English KJV",
        "text": "For God so loved the world",
    })
    assert preview.ref_label.text() == "John 3:16 — KJV"


def test_load_chapter_does_not_schedule_delayed_scroll(monkeypatch, app):
    calls = []

    def capture_single_shot(delay, callback):
        calls.append(delay)
        callback()

    monkeypatch.setattr("navigator.QTimer.singleShot", capture_single_shot)

    navigator_widget = VerseNavigator(FakeDb(), FakeDisplay())
    verses = FakeDb().get_chapter_verses("John", 3, "English KJV")
    navigator_widget.load_chapter("John", 3, verses, target_verse=2)

    assert calls == [0]
    assert navigator_widget.highlighted_idx == 1


def test_load_chapter_matches_actual_verse_number_not_list_index(monkeypatch, app):
    calls = []

    def capture_single_shot(delay, callback):
        calls.append(delay)
        callback()

    monkeypatch.setattr("navigator.QTimer.singleShot", capture_single_shot)

    navigator_widget = VerseNavigator(FakeDb(), FakeDisplay())
    verses = [
        {"id": 10, "book": "John", "chapter": 3, "verse": 3, "reference": "John 3:3", "text": "Three", "translation": "English KJV"},
        {"id": 11, "book": "John", "chapter": 3, "verse": 5, "reference": "John 3:5", "text": "Five", "translation": "English KJV"},
    ]

    navigator_widget.load_chapter("John", 3, verses, target_verse=5)

    assert calls == [0]
    assert navigator_widget.highlighted_idx == 1


def test_display_overlay_fit_uses_translation_font_size(app):
    window = DisplayWindow(FakeDisplay(), FakeThemeManager())
    verse = {
        "reference": "John 3:16",
        "translation": "English KJV",
        "text": "For God so loved the world",
    }
    wide_html = window._build_overlay_html(verse, 28, verse["text"], is_primary=False)
    narrow_html = window._build_overlay_html(verse, 10, verse["text"], is_primary=False)
    font = window.font()
    font.setFamily("Segoe UI")
    font.setPointSize(24)
    wide_height = window._measure_rich_text_height(wide_html, font, 180)
    narrow_height = window._measure_rich_text_height(narrow_html, font, 180)

    assert wide_height > narrow_height


def test_preview_wrap_measurement_handles_long_unbroken_tokens(app):
    preview = DisplayPreview(FakeDisplay())
    font = QFont("Segoe UI", 16)
    short_height = preview._measure_wrapped_text_height("short words", font, 140)
    long_height = preview._measure_wrapped_text_height("Supercalifragilisticexpialidocious", font, 40)

    assert long_height > short_height
