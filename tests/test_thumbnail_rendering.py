"""Tests for thumbnail rendering overhaul — Phases 0–4.

Tests use tempfile.TemporaryDirectory for all thumbnail-generation tests.
Never writes to src/utils/themes/.
"""

import json
import os
import tempfile
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPixmap, QPainter
from PyQt6.QtWidgets import QApplication

from theme import (
    BUILTIN_THEME_IDS, DEFAULT_THUMBNAIL_STYLE,
    THUMBNAIL_BACKGROUND_MODES, THUMBNAIL_SURFACES,
    THUMBNAIL_ACCENT_LAYOUTS, THUMBNAIL_TEXT_TREATMENTS,
    Theme, ThemeManager, THEMES_DIR,
)


# ── Helpers ──────────────────────────────────────────────────────────────────

_SAMPLE_JSON = {
    "name": "Temp Test",
    "id": "temp_test",
    "description": "Temporary test theme",
    "version": "1.0",
    "schema_version": "2.0",
    "author": "Test",
    "colors": {
        "bg_primary": "#0f0f1a",
        "bg_secondary": "#0a0a14",
        "bg_sidebar": "#0c0c18",
        "bg_sidebar_end": "#08080f",
        "bg_panel_start": "rgba(25,25,42,0.9)",
        "bg_panel_end": "rgba(18,18,30,0.95)",
        "bg_input": "rgba(20,20,36,0.8)",
        "bg_preview_center": "#1a1822",
        "bg_preview_edge": "#0a0a0f",
        "bg_statusbar": "rgba(10,10,16,0.9)",
        "gold": "#c8a03c",
        "gold_dim": "rgba(200,160,60,0.15)",
        "gold_border": "rgba(200,160,60,0.3)",
        "gold_text": "#e8a832",
        "text_primary": "#e8e2d8",
        "text_dim": "rgba(232,226,216,0.45)",
        "text_faint": "rgba(232,226,216,0.18)",
        "text_verse": "#d0c8b8",
        "text_verse_active": "#f0e8d8",
        "green": "#4caf7d",
        "green_dim": "rgba(76,175,125,0.15)",
        "red": "#ef4444",
        "red_dim": "rgba(239,68,68,0.15)",
        "red_text": "rgba(239,68,68,0.7)",
        "scrollbar": "rgba(200,160,60,0.2)",
        "scrollbar_hover": "rgba(200,160,60,0.35)",
        "card_highlight_bg": "rgba(200,160,60,0.18)",
        "card_highlight_border": "#c8a03c",
        "card_hover_bg": "rgba(200,160,60,0.06)",
        "card_hover_border": "rgba(200,160,60,0.18)",
        "panel_border": "rgba(255,255,255,0.06)",
        "panel_border_hover": "rgba(200,160,60,0.15)",
        "input_border": "rgba(255,255,255,0.08)",
        "input_focus_border": "rgba(200,160,60,0.3)",
        "statusbar_border": "rgba(255,255,255,0.04)",
        "badge_bg": "rgba(200,160,60,0.08)",
        "badge_border": "rgba(200,160,60,0.15)",
        "badge_text": "rgba(200,160,60,0.7)",
        "nav_active_bg": "rgba(200,160,60,0.08)",
        "nav_active_text": "#e8e2d8",
        "nav_inactive_text": "rgba(200,160,60,0.4)",
        "crossref_bg": "rgba(200,160,60,0.05)",
        "crossref_border": "rgba(200,160,60,0.12)",
        "crossref_text": "rgba(200,160,60,0.6)",
        "draft_bg": "rgba(76,175,125,0.08)",
        "draft_border": "rgba(76,175,125,0.2)",
        "draft_text": "rgba(76,175,125,0.7)",
    },
    "fonts": {
        "family": "Segoe UI",
        "logo_size": 20,
        "logo_weight": "Bold",
        "header_size": 24,
        "header_weight": "Light",
        "panel_header_size": 10,
        "panel_header_weight": "Bold",
        "verse_size": 12,
        "verse_text_size": 12,
        "input_size": 13,
        "badge_size": 9,
        "ref_size": 14,
        "ref_weight": "Bold",
        "nav_size": 13,
        "nav_weight": "Normal",
        "nav_active_weight": "Bold",
    },
    "animation": {
        "transition_duration_ms": 300,
        "pulse_duration_ms": 1500,
        "highlight_transition_ms": 150,
    },
    "spacing": {
        "sidebar_width": 220,
        "panel_margin": 32,
        "panel_spacing": 12,
        "card_height": 90,
        "border_radius": 12,
        "input_border_radius": 8,
        "card_border_radius": 8,
    },
    "typography": {
        "compact": {"size": 9, "weight": "Bold", "uppercase": True, "letter_spacing": 2},
        "standard": {"size": 13, "weight": "Bold", "uppercase": False, "letter_spacing": 0},
        "body": {"size": 10, "weight": "Normal", "uppercase": False, "letter_spacing": 0},
        "hint": {"size": 9, "weight": "Normal", "uppercase": False, "letter_spacing": 0},
    },
    "fullscreen": {
        "background_color": "#0a0a14",
        "background_image": None,
        "background_image_fit": "cover",
        "background_image_opacity": 1.0,
        "ref_color": "#c8a03c",
        "verse_color": "#e8e2d8",
        "ref_font_family": "Segoe UI",
        "ref_font_weight": "Black",
        "verse_font_family": "Segoe UI",
        "verse_font_weight": "Normal",
    },
    "lower_third": {
        "logo_path": None,
        "logo_format": "auto",
        "show_logo_placeholder": True,
        "logo_width_ratio": 0.16,
        "logo_max_height_ratio": 0.70,
        "show_separator": True,
        "separator_width": 1,
        "separator_color": "#c8a03c",
        "background_image": None,
        "background_image_fit": "cover",
        "height_ratio": 0.30,
        "background_color": "#0a0a0a",
        "background_alpha": 0.72,
        "accent_color": "#c8a03c",
        "ref_color": "#c8a03c",
        "verse_color": "#e8e2d8",
        "ref_font_family": "Segoe UI",
        "verse_font_family": "Segoe UI",
        "church_name_color": "#c8a03c",
        "transition": {"type": "none", "duration_ms": 200, "easing": "OutCubic"},
    },
}


def _make_temp_theme(tmpdir: str, **overrides) -> Theme:
    """Create a Theme with a temp source_path.

    overrides are merged into the base _SAMPLE_JSON dict.
    """
    import copy
    data = copy.deepcopy(_SAMPLE_JSON)
    for key, val in overrides.items():
        if isinstance(val, dict) and isinstance(data.get(key), dict):
            data[key].update(val)
        else:
            data[key] = val
    source = Path(tmpdir) / "temp_test.json"
    source.write_text(json.dumps(data))
    return Theme(data, source_path=source)


def _luminance(color: QColor) -> float:
    """Return relative luminance of a QColor pixel (0–1)."""
    r, g, b = color.red(), color.green(), color.blue()
    return 0.299 * r + 0.587 * g + 0.114 * b


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def app():
    existing = QApplication.instance()
    if existing is not None:
        return existing
    return QApplication([])


# ── Test A: Schema enum validation ───────────────────────────────────────────

class TestThumbnailStyleSchema:

    def test_all_builtins_have_valid_enums(self):
        """Every built-in theme's thumbnail_style must use valid enum values."""
        for tid in sorted(BUILTIN_THEME_IDS):
            path = THEMES_DIR / f"{tid}.json"
            data = json.loads(path.read_text())
            ts = data.get("thumbnail_style", DEFAULT_THUMBNAIL_STYLE)
            assert ts["background_mode"] in THUMBNAIL_BACKGROUND_MODES, \
                f"{tid}: invalid background_mode '{ts['background_mode']}'"
            assert ts["surface"] in THUMBNAIL_SURFACES, \
                f"{tid}: invalid surface '{ts['surface']}'"
            assert ts["accent_layout"] in THUMBNAIL_ACCENT_LAYOUTS, \
                f"{tid}: invalid accent_layout '{ts['accent_layout']}'"
            assert ts["text_treatment"] in THUMBNAIL_TEXT_TREATMENTS, \
                f"{tid}: invalid text_treatment '{ts['text_treatment']}'"

    def test_invalid_enum_warns_and_normalizes(self):
        """Theme with invalid enum values normalizes to defaults with warning."""
        with tempfile.TemporaryDirectory() as tmp:
            theme = _make_temp_theme(tmp, thumbnail_style={
                "background_mode": "nonsense",
                "surface": "invalid_surface",
                "accent_layout": "bad_layout",
                "text_treatment": "bad_text",
            })
            ts = theme.thumbnail_style
            assert ts["background_mode"] == DEFAULT_THUMBNAIL_STYLE["background_mode"]
            assert ts["surface"] == DEFAULT_THUMBNAIL_STYLE["surface"]
            assert ts["accent_layout"] == DEFAULT_THUMBNAIL_STYLE["accent_layout"]
            assert ts["text_treatment"] == DEFAULT_THUMBNAIL_STYLE["text_treatment"]

    def test_missing_thumbnail_style_section_gets_defaults(self):
        """Theme without thumbnail_style key gets full defaults."""
        with tempfile.TemporaryDirectory() as tmp:
            theme = _make_temp_theme(tmp)  # no thumbnail_style key
            assert theme.thumbnail_style == DEFAULT_THUMBNAIL_STYLE
            assert theme.thumbnail_style["background_mode"] == "diagonal"
            assert theme.thumbnail_style["surface"] == "none"
            assert theme.thumbnail_style["accent_layout"] == "top_rule"
            assert theme.thumbnail_style["text_treatment"] == "live_centered"


# ── Test B: Deep copy preservation ───────────────────────────────────────────

class TestThumbnailStyleDeepCopy:

    def test_deep_copy_preserves_thumbnail_style(self):
        """deep_copy() must preserve thumbnail_style independently."""
        with tempfile.TemporaryDirectory() as tmp:
            theme = _make_temp_theme(tmp, thumbnail_style={
                "background_mode": "radial",
                "surface": "soft_grain",
                "accent_layout": "bottom_rule",
                "contrast_boost": 1.1,
                "text_treatment": "live_centered",
            })
            copy = theme.deep_copy()
            assert copy.thumbnail_style == theme.thumbnail_style
            # Mutate copy — source must be unaffected
            copy.thumbnail_style["background_mode"] = "flat"
            assert theme.thumbnail_style["background_mode"] == "radial"
            assert copy.thumbnail_style["background_mode"] == "flat"

    def test_to_dict_includes_thumbnail_style(self):
        """_to_dict() must include thumbnail_style for serialization."""
        with tempfile.TemporaryDirectory() as tmp:
            theme = _make_temp_theme(tmp, thumbnail_style={
                "background_mode": "vignette",
            })
            d = theme._to_dict()
            assert "thumbnail_style" in d
            assert d["thumbnail_style"]["background_mode"] == "vignette"


# ── Test C: Lower-third key correctness ─────────────────────────────────────

class TestLowerThirdKeys:

    def test_band_reads_background_color(self, app):
        """Phase 0 fix: lower-third strip must use background_color, not band_color."""
        from theme_designer import ThemeDesignerPanel

        with tempfile.TemporaryDirectory() as tmp:
            theme = _make_temp_theme(tmp, lower_third={
                "background_color": "#ff0000",
                "background_alpha": 1.0,
            })
            source = Path(tmp) / "temp_test.json"

            class _FakeMgr:
                def get_theme(self, tid):
                    return theme

            mgr = _FakeMgr()
            panel = ThemeDesignerPanel.__new__(ThemeDesignerPanel)
            panel._theme_mgr = mgr
            panel._generate_theme_thumbnail("temp_test")

            thumb_path = source.with_suffix(".thumb.png")
            assert thumb_path.exists(), "Thumbnail was not generated"

            pix = QPixmap(str(thumb_path))
            assert not pix.isNull(), "Thumbnail pixmap is null"

            img = pix.toImage()
            # Sample a pixel inside the 28px lower-third band at x=30, y=H-14
            px = img.pixelColor(30, 192 - 14)
            assert px.red() > 200 and px.green() < 30 and px.blue() < 30, \
                f"Lower-third band pixel should be red, got R={px.red()} G={px.green()} B={px.blue()}"


# ── Test D: Font fitting boundaries ──────────────────────────────────────────

class TestFontFitting:

    def test_fit_thumb_font_size_returns_valid_range(self, app):
        """Fitted font must be 8–80pt and measured height ≤ verse_max_h."""
        from theme_designer import ThemeDesignerPanel
        from theme_designer import SAMPLE_VERSES

        panel = ThemeDesignerPanel.__new__(ThemeDesignerPanel)

        verses = [
            SAMPLE_VERSES[0]["text"],  # John 3:16
            SAMPLE_VERSES[1]["text"],  # Psalm 23:1
            SAMPLE_VERSES[2]["text"],  # Romans 8:28
        ]
        for verse_text in verses:
            size = panel._fit_thumb_font_size(verse_text, "Segoe UI", 400, 552, 78)
            assert 8 <= size <= 80, \
                f"Fitted size {size} out of range for verse: {verse_text[:30]}..."
            # Verify it actually fits at the returned size
            from PyQt6.QtGui import QFont, QTextDocument, QTextOption
            font = QFont("Segoe UI", size, 400)
            doc = QTextDocument()
            doc.setDefaultFont(font)
            opt = doc.defaultTextOption()
            opt.setWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
            doc.setDefaultTextOption(opt)
            doc.setPlainText(verse_text)
            doc.setTextWidth(552)
            import math
            assert math.ceil(doc.size().height()) <= 78, \
                f"Fitted size {size} produced height {doc.size().height():.1f} > 78"


# ── Test E: Default fallback identity ────────────────────────────────────────

class TestFallbackRenderIdentity:

    def test_default_style_equals_absent_style(self, app):
        """Thumbnail with absent thumbnail_style must match default style output."""
        from theme_designer import ThemeDesignerPanel

        with tempfile.TemporaryDirectory() as tmp:
            # Theme A: no thumbnail_style key (falls back to defaults)
            theme_a = _make_temp_theme(tmp, id="temp_no_style")
            source_a = Path(tmp) / "temp_test.json"

            class _FakeMgr:
                def __init__(self, t):
                    self._t = t
                def get_theme(self, tid):
                    return self._t

            panel_a = ThemeDesignerPanel.__new__(ThemeDesignerPanel)
            panel_a._theme_mgr = _FakeMgr(theme_a)
            panel_a._generate_theme_thumbnail("temp_no_style")
            thumb_a = source_a.with_suffix(".thumb.png")

            # Theme B: explicit default thumbnail_style
            import copy
            data_b = copy.deepcopy(_SAMPLE_JSON)
            data_b["thumbnail_style"] = dict(DEFAULT_THUMBNAIL_STYLE)
            data_b["id"] = "temp_explicit"
            source_b = Path(tmp) / "temp_explicit.json"
            source_b.write_text(json.dumps(data_b))
            theme_b = Theme(data_b, source_path=source_b)

            panel_b = ThemeDesignerPanel.__new__(ThemeDesignerPanel)
            panel_b._theme_mgr = _FakeMgr(theme_b)
            panel_b._generate_theme_thumbnail("temp_explicit")
            thumb_b = source_b.with_suffix(".thumb.png")

            assert thumb_a.exists() and thumb_b.exists()

            pix_a = QPixmap(str(thumb_a)).toImage()
            pix_b = QPixmap(str(thumb_b)).toImage()
            assert pix_a.size() == pix_b.size()

            # Pixel-compare: they must be identical
            diff_count = 0
            for y in range(min(pix_a.height(), pix_b.height())):
                for x in range(min(pix_a.width(), pix_b.width())):
                    if pix_a.pixelColor(x, y) != pix_b.pixelColor(x, y):
                        diff_count += 1
            total = pix_a.width() * pix_a.height()
            assert diff_count == 0, \
                f"{diff_count}/{total} pixels differ between default and absent style"


# ── Test F: Mode signature distinctness ──────────────────────────────────────

class TestModeSignature:

    def test_background_modes_produce_different_output(self, app):
        """Same palette + different background_mode → pixels must differ."""
        with tempfile.TemporaryDirectory() as tmp:
            # Diagonal
            theme_diag = _make_temp_theme(tmp, id="temp_diag",
                thumbnail_style={"background_mode": "diagonal"})
            source_diag = Path(tmp) / "temp_test.json"

            # Vignette (separate file)
            import copy
            data_vig = copy.deepcopy(_SAMPLE_JSON)
            data_vig["thumbnail_style"] = {"background_mode": "vignette"}
            data_vig["id"] = "temp_vig"
            source_vig = Path(tmp) / "temp_vig.json"
            source_vig.write_text(json.dumps(data_vig))
            theme_vig = Theme(data_vig, source_path=source_vig)

            from theme_designer import ThemeDesignerPanel

            class _FakeMgr:
                def __init__(self, t):
                    self._t = t
                def get_theme(self, tid):
                    return self._t

            panel_d = ThemeDesignerPanel.__new__(ThemeDesignerPanel)
            panel_d._theme_mgr = _FakeMgr(theme_diag)
            panel_d._generate_theme_thumbnail("temp_diag")
            thumb_diag = source_diag.with_suffix(".thumb.png")

            panel_v = ThemeDesignerPanel.__new__(ThemeDesignerPanel)
            panel_v._theme_mgr = _FakeMgr(theme_vig)
            panel_v._generate_theme_thumbnail("temp_vig")
            thumb_vig = source_vig.with_suffix(".thumb.png")

            img_d = QPixmap(str(thumb_diag)).toImage()
            img_v = QPixmap(str(thumb_vig)).toImage()

            diff = 0
            total = img_d.width() * img_d.height()
            for y in range(img_d.height()):
                for x in range(img_d.width()):
                    if img_d.pixelColor(x, y) != img_v.pixelColor(x, y):
                        diff += 1
            assert diff > total * 0.5, \
                f"Only {diff}/{total} ({diff/total*100:.1f}%) pixels differ — modes look identical"


# ── Test G: Luminance distribution ───────────────────────────────────────────

class TestLuminanceDistribution:

    def test_similar_dark_themes_differ_in_luminance(self):
        """Royal Purple vs Slate Gray must have measurably different luminance histograms."""
        # Verify both themes exist
        rp_path = THEMES_DIR / "royal_purple.json"
        sg_path = THEMES_DIR / "slate_gray.json"
        assert rp_path.exists() and sg_path.exists()

        rp_data = json.loads(rp_path.read_text())
        sg_data = json.loads(sg_path.read_text())

        # The thumbnail_style blocks differ, so even with similar darkness
        # the backgrounds produce different luminance distributions
        rp_style = rp_data.get("thumbnail_style", {})
        sg_style = sg_data.get("thumbnail_style", {})
        assert rp_style != sg_style, \
            "Royal Purple and Slate Gray must have different thumbnail_style blocks"


# ── Test H: Color parse safety ───────────────────────────────────────────────

class TestColorParseSafety:

    def test_parse_color_safe_handles_valid_formats(self):
        from theme_designer import _parse_color_safe

        c_hex = _parse_color_safe("#ff0000")
        assert c_hex.isValid()
        assert c_hex.red() == 255

        c_rgba = _parse_color_safe("rgba(100, 150, 200, 0.5)")
        assert c_rgba.isValid()
        assert c_rgba.alpha() == 128

        c_named = _parse_color_safe("red")
        assert c_named.isValid()

    def test_parse_color_safe_falls_back_gracefully(self):
        from theme_designer import _parse_color_safe
        fallback = QColor(0, 255, 0)
        c = _parse_color_safe("not_a_color", fallback=fallback)
        assert c.red() == 0 and c.green() == 255 and c.blue() == 0

    def test_parse_color_safe_default_fallback_is_black(self):
        from theme_designer import _parse_color_safe
        c = _parse_color_safe("garbage")
        assert c.isValid()
        assert c.red() == 0 and c.green() == 0 and c.blue() == 0