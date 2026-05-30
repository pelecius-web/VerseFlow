"""Tests for v1.3.0 Phase 4 Preset Library — JSON integrity, color consistency, ThemeCardWidget API."""

import json
import os
import tempfile
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QPixmap

from theme import BUILTIN_THEME_IDS, Theme


# ── Helpers ──────────────────────────────────────────────────────────────────

THEMES_DIR = Path(__file__).resolve().parent.parent / "src" / "utils" / "themes"

CHROME_TOKENS = ("bg_sidebar", "bg_sidebar_end", "bg_panel_start",
                 "bg_panel_end", "bg_input", "bg_preview_center",
                 "bg_preview_edge", "bg_statusbar")

DARK_THEMES = ("warm_amber", "forest_green", "royal_purple",
               "crimson_red", "slate_gray")

EXPECTED_COLOR_TOKENS = 47   # Was 46; +1 for red_text (Phase 1)

REQUIRED_SECTIONS = ("fonts", "animation", "spacing", "typography", "fullscreen", "lower_third")


def _load_colors(theme_id: str) -> dict:
    with open(THEMES_DIR / f"{theme_id}.json", encoding="utf-8") as f:
        return json.load(f)["colors"]


@pytest.fixture(scope="module")
def app():
    existing = QApplication.instance()
    if existing is not None:
        return existing
    return QApplication([])


# ── JSON Integrity Tests (no QApp needed) ───────────────────────────────────

class TestPresetJsonIntegrity:

    def test_all_builtin_theme_ids_have_files(self):
        for tid in BUILTIN_THEME_IDS:
            path = THEMES_DIR / f"{tid}.json"
            assert path.exists(), f"Missing theme file: {path}"

    def test_all_json_parse_valid(self):
        for tid in BUILTIN_THEME_IDS:
            path = THEMES_DIR / f"{tid}.json"
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            assert "colors" in data, f"{tid}.json missing 'colors'"
            assert isinstance(data["colors"], dict)

    def test_all_have_46_color_tokens(self):
        for tid in BUILTIN_THEME_IDS:
            colors = _load_colors(tid)
            assert len(colors) == EXPECTED_COLOR_TOKENS, (
                f"{tid}.json has {len(colors)} color tokens, expected {EXPECTED_COLOR_TOKENS}")

    def test_all_have_required_sections(self):
        for tid in BUILTIN_THEME_IDS:
            path = THEMES_DIR / f"{tid}.json"
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            for section in REQUIRED_SECTIONS:
                assert section in data, f"{tid}.json missing section '{section}'"
                assert isinstance(data[section], dict), f"{tid}.json.{section} must be a dict"

    def test_no_midnight_blue_chrome_leak(self):
        midnight = _load_colors("midnight_blue")
        for tid in DARK_THEMES:
            colors = _load_colors(tid)
            for token in CHROME_TOKENS:
                assert colors.get(token) != midnight.get(token), (
                    f"{tid}.json {token} = {midnight[token]} (same as midnight_blue)")

    def test_nav_active_text_equals_text_primary(self):
        for tid in (*DARK_THEMES, "midnight_blue", "pastel_calm", "dark_gold", "high_contrast"):
            colors = _load_colors(tid)
            assert colors.get("nav_active_text") == colors.get("text_primary"), (
                f"{tid}.json nav_active_text ({colors.get('nav_active_text')}) "
                f"!= text_primary ({colors.get('text_primary')})")

    def test_builtin_ids_count_matches_file_count(self):
        files = [p for p in THEMES_DIR.glob("*.json") if p.stem in BUILTIN_THEME_IDS]
        assert len(BUILTIN_THEME_IDS) == len(files), (
            f"BUILTIN_THEME_IDS has {len(BUILTIN_THEME_IDS)} IDs but {len(files)} JSON files exist")

    def test_all_chrome_tokens_present_in_dark_themes(self):
        for tid in DARK_THEMES:
            colors = _load_colors(tid)
            for token in CHROME_TOKENS:
                assert token in colors, f"{tid}.json missing chrome token '{token}'"


# ── ThemeCardWidget Tests (need QApp) ───────────────────────────────────────

class TestThemeCardWidget:

    def test_card_stores_attributes(self, app):
        from theme_designer import ThemeCardWidget
        card = ThemeCardWidget("test_id", "Test Name", "", True)
        assert card.theme_id == "test_id"
        assert card.name == "Test Name"
        assert card.is_builtin is True

    def test_selected_property_triggers(self, app):
        from theme_designer import ThemeCardWidget
        card = ThemeCardWidget("test_id", "Test Name", "", True)
        assert card.property("selected") is None or card.property("selected") is False
        card.set_selected(True)
        assert card.property("selected") is True
        card.set_selected(False)
        assert card.property("selected") is False

    def test_clicked_signal_emits_id(self, app):
        from theme_designer import ThemeCardWidget
        card = ThemeCardWidget("test_id", "Test Name", "", True)
        triggered = []
        card.clicked.connect(lambda tid: triggered.append(tid))
        card.clicked.emit("test_id")
        assert triggered == ["test_id"]

    def test_thumbnail_fallback_when_no_file(self, app):
        from theme_designer import ThemeCardWidget
        card = ThemeCardWidget("missing", "No Thumb", "", False)
        assert card.thumb_lbl.text() == "No Preview", (
            "Card without thumbnail file should show 'No Preview' text")

    def test_thumbnail_show_when_file_exists(self, app):
        with tempfile.TemporaryDirectory() as tmp:
            thumb_path = str(Path(tmp) / "test_theme.thumb.png")
            pixmap = QPixmap(140, 48)
            from PyQt6.QtCore import Qt
            pixmap.fill(Qt.GlobalColor.red)
            pixmap.save(thumb_path, "PNG")

            from theme_designer import ThemeCardWidget
            card = ThemeCardWidget("test_id", "Test Name", thumb_path, False)
            assert card.thumb_lbl.pixmap() is not None, (
                "Card with valid thumbnail file should display pixmap")
            assert not card.thumb_lbl.pixmap().isNull()

class TestThumbnailCleanup:

    def test_delete_cleans_thumb_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            json_path = Path(tmp) / "test_theme.json"
            json_path.write_text('{"id": "test", "name": "Test", "schema_version": "2.0"}')
            thumb_path = json_path.with_suffix(".thumb.png")
            thumb_path.write_text("fake png content")
            assert thumb_path.exists()

            theme = Theme({"id": "test", "name": "Test"}, source_path=json_path)
            success = theme.delete()
            assert success is True
            assert not json_path.exists()
            assert not thumb_path.exists()

    def test_delete_skips_missing_thumb(self):
        with tempfile.TemporaryDirectory() as tmp:
            json_path = Path(tmp) / "test_theme_no_thumb.json"
            json_path.write_text('{"id": "test", "name": "Test", "schema_version": "2.0"}')
            thumb_path = json_path.with_suffix(".thumb.png")
            assert not thumb_path.exists()

            theme = Theme({"id": "test", "name": "Test"}, source_path=json_path)
            success = theme.delete()
            assert success is True
            assert not json_path.exists()

    def test_delete_refuses_builtin(self):
        for builtin_id in list(BUILTIN_THEME_IDS)[:3]:
            theme = Theme({"id": builtin_id, "name": builtin_id})
            result = theme.delete()
            assert result is False, f"delete should refuse built-in '{builtin_id}'"


# ── ThemesListPanel Grid Tests ───────────────────────────────────────────────

class TestThemesListPanel:

    def test_panel_has_scroll_area_with_grid(self, app):
        from theme_designer import ThemesListPanel, ThemeManager
        mgr = ThemeManager()
        panel = ThemesListPanel(theme_mgr=mgr)
        assert hasattr(panel, "_scroll"), "ThemesListPanel missing QScrollArea"
        assert hasattr(panel, "_grid"), "ThemesListPanel missing QGridLayout"

    def test_cards_populated_from_available_themes(self, app):
        from theme_designer import ThemesListPanel, ThemeManager
        mgr = ThemeManager()
        panel = ThemesListPanel(theme_mgr=mgr)
        card_count = len(panel._cards)
        available_count = len(mgr.available_themes())
        assert card_count == available_count, (
            f"Grid has {card_count} cards but {available_count} themes available")
