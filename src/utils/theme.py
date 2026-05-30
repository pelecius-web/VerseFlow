"""theme.py — VerseFlow Theme Engine (v2)

Loads JSON theme definitions and generates QSS stylesheets.
Supports: Dark Gold, Light, High Contrast, and custom themes.

v2: Schema versioning, per-channel theme isolation, application font loading.
"""

import copy
import json
import logging
import re
from pathlib import Path
from typing import Optional

from constants import (
    LOWER_THIRD_BACKGROUND_ALPHA,
    LOWER_THIRD_HEIGHT_RATIO,
    LOWER_THIRD_LOGO_MAX_HEIGHT_RATIO,
    LOWER_THIRD_SEPARATOR_WIDTH,
)

logger = logging.getLogger("VerseFlow")

THEMES_DIR = Path(__file__).parent / "themes"
FONTS_DIR = THEMES_DIR / "fonts"
DEFAULT_THEME = "dark_gold"
KNOWN_SCHEMA_VERSIONS = {"1.0", "2.0"}

# ── Thumbnail style enums ────────────────────────────────────────────────
THUMBNAIL_BACKGROUND_MODES = {"diagonal", "radial", "vignette", "flat", "split", "wash"}
THUMBNAIL_SURFACES = {"none", "soft_grain", "paper", "glass", "broadcast_grid"}
THUMBNAIL_ACCENT_LAYOUTS = {"top_rule", "bottom_rule", "side_rail", "corner_bracket", "double_rule"}
THUMBNAIL_TEXT_TREATMENTS = {"live_centered"}

DEFAULT_THUMBNAIL_STYLE = {
    "background_mode": "diagonal",
    "surface": "none",
    "accent_layout": "top_rule",
    # Reserved metadata for a future contrast pass; current renderer can ignore it safely.
    "contrast_boost": 1.0,
    "text_treatment": "live_centered",
}

BUILTIN_THEME_IDS = {
    "dark_gold", "light", "high_contrast",
    "midnight_blue", "forest_green", "crimson_red",
    "royal_purple", "warm_amber", "slate_gray", "pastel_calm",
}

# Weight name → QFont.Weight mapping
WEIGHT_MAP = {
    "Thin": 100,
    "ExtraLight": 200,
    "Light": 300,
    "Normal": 400,
    "Medium": 500,
    "DemiBold": 600,
    "Bold": 700,
    "ExtraBold": 800,
    "Black": 900,
}

# Default typography scale — emitted by generate_stylesheet() when a theme
# lacks the section. Matches the 4-entry initial population in built-in JSONs.
# Invariant: typography dict values must be numeric/string primitives that
# never contain unbalanced braces — this protects generate_stylesheet()'s
# f-string injection point from ValueError crashes. (F8 mitigation)
TYPOGRAPHY_DEFAULTS = {
    "compact":   {"size": 9,  "weight": "Bold",   "uppercase": True,  "letter_spacing": 2},
    "standard":  {"size": 13, "weight": "Bold",   "uppercase": False, "letter_spacing": 0},
    "body":      {"size": 10, "weight": "Normal", "uppercase": False, "letter_spacing": 0},
    "hint":      {"size": 9,  "weight": "Normal", "uppercase": False, "letter_spacing": 0},
}

# Color token mapping per typography entry (Deviation 2, F2 fix).
# Section headers (compact, standard) use gold — matches current QLabel[section-header] rules.
# Body labels use text_primary — matches standard QLabel color.
# Hint labels use nav_inactive_text — matches current QLabel[hint="true"].
# Future entries (e.g., caption in v1.4.0) add their token here as a one-line edit.
TYPO_COLOR_TOKENS = {
    "compact":  "gold",
    "standard": "gold",
    "body":     "text_primary",
    "hint":     "nav_inactive_text",
}


class Theme:
    """Represents a loaded theme definition."""

    SCHEMA_VERSION = "2.0"

    # Fallback values for schema v1.0 themes missing these sections
    FALLBACK_COLORS = {
        "bg_primary": "#0f0f1a",
        "bg_secondary": "#0a0a14",
        "gold": "#c8a03c",
        "text_primary": "#e8e2d8",
    }

    def __init__(self, data: dict, source_path: Path = None):
        self.name: str = data.get("name", "Unknown")
        self.id: str = data.get("id", "unknown")
        self.description: str = data.get("description", "")
        self.version: str = data.get("version", "1.0")
        self.schema_version: str = data.get("schema_version", "1.0")
        if self.schema_version not in KNOWN_SCHEMA_VERSIONS:
            logger.warning("[Theme] Unknown schema_version '%s'; treating as 1.0", self.schema_version)
            self.schema_version = "1.0"
        self.source_path: Path = source_path
        self.author: str = data.get("author", "")  # E2 fix: was silently dropped
        self.colors: dict = data.get("colors", {})
        self.fonts: dict = data.get("fonts", {})
        self.animation: dict = data.get("animation", {})
        self.spacing: dict = data.get("spacing", {})
        self.lower_third: dict = data.get("lower_third", {})
        self.typography: dict = data.get("typography", copy.deepcopy(TYPOGRAPHY_DEFAULTS))
        self.fullscreen: dict = data.get("fullscreen", {})
        self.thumbnail_style: dict = data.get("thumbnail_style", {})
        if self.schema_version == "1.0":
            self._upgrade_to_v2()
        self._normalize_thumbnail_style()

    def c(self, key: str) -> str:
        """Shorthand for color lookup."""
        return self.colors.get(key, "#000000")

    def _upgrade_to_v2(self):
        """Upgrade schema v1.0 themes to v2.0 in memory only.

        Fills missing lower_third keys with defaults, creates fullscreen
        section from color defaults, and sets schema_version.
        On-disk JSON is never modified.
        """
        # Lower-third defaults — all 22 keys from plan §4.1
        lt_defaults = {
            "logo_path":              None,
            "logo_format":            "auto",
            "show_logo_placeholder":  True,
            "logo_width_ratio":       self.lower_third.get("logo_width_ratio", 0.16),
            "logo_max_height_ratio":  self.lower_third.get("logo_max_height_ratio", LOWER_THIRD_LOGO_MAX_HEIGHT_RATIO),
            "show_separator":         True,
            "separator_color":        self.colors.get("gold", "#c8a03c"),
            "separator_width":        self.lower_third.get("separator_width", LOWER_THIRD_SEPARATOR_WIDTH),
            "background_image":       None,
            "background_image_fit":   "cover",
            "background_alpha":       self.lower_third.get("background_alpha", LOWER_THIRD_BACKGROUND_ALPHA),
            "height_ratio":           self.lower_third.get("height_ratio", LOWER_THIRD_HEIGHT_RATIO),
            "background_color":       self.lower_third.get("background_color", "#0a0a14"),
            "accent_color":           self.colors.get("gold", "#c8a03c"),
            "ref_color":              self.colors.get("gold", "#c8a03c"),
            "verse_color":            self.colors.get("text_primary", "#e8e2d8"),
            "ref_font_family":        self.fonts.get("family", "Segoe UI"),
            "verse_font_family":      self.fonts.get("family", "Segoe UI"),
            "verse_font_weight":      "Normal",
            "ref_font_weight":        "Bold",
            "church_name_color":      self.colors.get("gold", "#c8a03c"),
            "transition":             {"type": "none", "duration_ms": 200, "easing": "OutCubic"},
        }
        for key, val in lt_defaults.items():
            self.lower_third.setdefault(key, val)

        if not self.fullscreen:
            self.fullscreen = {
                "background_color":         self.colors.get("bg_secondary", "#0a0a14"),
                "background_image":         None,
                "background_image_fit":     "cover",
                "background_image_opacity": 1.0,
                "ref_color":                self.colors.get("gold", "#c8a03c"),
                "verse_color":              self.colors.get("text_primary", "#e8e2d8"),
                "ref_font_family":          self.fonts.get("family", "Segoe UI"),
                "ref_font_weight":          "Black",
                "verse_font_family":        self.fonts.get("family", "Segoe UI"),
                "verse_font_weight":        "Normal",
            }

        # Typography defaults (Phase 0 — additive section, no schema_version bump)
        if not self.typography:
            self.typography = copy.deepcopy(TYPOGRAPHY_DEFAULTS)

        self.schema_version = self.SCHEMA_VERSION

    def _normalize_thumbnail_style(self):
        """Apply defaults and validate enum values for thumbnail_style."""
        raw = getattr(self, "thumbnail_style", None) or {}
        normalized = dict(DEFAULT_THUMBNAIL_STYLE)
        for key in DEFAULT_THUMBNAIL_STYLE:
            if key in raw:
                normalized[key] = raw[key]
        if normalized["background_mode"] not in THUMBNAIL_BACKGROUND_MODES:
            logger.warning("[Theme] Invalid thumbnail_style.background_mode '%s', using default",
                           normalized["background_mode"])
            normalized["background_mode"] = DEFAULT_THUMBNAIL_STYLE["background_mode"]
        if normalized["surface"] not in THUMBNAIL_SURFACES:
            logger.warning("[Theme] Invalid thumbnail_style.surface '%s', using default",
                           normalized["surface"])
            normalized["surface"] = DEFAULT_THUMBNAIL_STYLE["surface"]
        if normalized["accent_layout"] not in THUMBNAIL_ACCENT_LAYOUTS:
            logger.warning("[Theme] Invalid thumbnail_style.accent_layout '%s', using default",
                           normalized["accent_layout"])
            normalized["accent_layout"] = DEFAULT_THUMBNAIL_STYLE["accent_layout"]
        if normalized["text_treatment"] not in THUMBNAIL_TEXT_TREATMENTS:
            logger.warning("[Theme] Invalid thumbnail_style.text_treatment '%s', using default",
                           normalized["text_treatment"])
            normalized["text_treatment"] = DEFAULT_THUMBNAIL_STYLE["text_treatment"]
        self.thumbnail_style = normalized

    def update(self, json_path: str, value) -> None:
        """Set a value at a dotted JSON path on the in-memory theme.

        Examples:
            theme.update("lower_third.background_color", "#ff0000")
            theme.update("fullscreen.ref_color", "#c8a03c")
            theme.update("colors.gold", "#ffaa00")
            theme.update("lower_third.transition.type", "fade")

        Path components must be `dict` keys. Lists are not supported in v1.3.0.
        Unknown paths raise KeyError — callers must validate against the schema first.
        """
        parts = json_path.split(".")
        target = self
        for part in parts[:-1]:
            if hasattr(target, part) and isinstance(getattr(target, part), dict):
                target = getattr(target, part)
            elif isinstance(target, dict) and part in target:
                target = target[part]
            else:
                raise KeyError(f"Unknown theme path: {json_path}")
        leaf = parts[-1]
        if isinstance(target, dict):
            target[leaf] = value
        else:
            raise KeyError(f"Path leaf is not a dict: {json_path}")

    def deep_copy(self) -> "Theme":
        """Return a fully independent Theme instance.

        Used by the designer to sandbox edits — mutations on the copy never
        propagate to the registry's shared instance until Save.
        """
        data = {
            "name": self.name,
            "id": self.id,
            "description": self.description,
            "version": self.version,
            "schema_version": self.schema_version,
            "author": self.author,  # E2 fix: preserve author on deep copy
            "colors": copy.deepcopy(self.colors),
            "fonts": copy.deepcopy(self.fonts),
            "animation": copy.deepcopy(self.animation),
            "spacing": copy.deepcopy(self.spacing),
            "typography": copy.deepcopy(self.typography),   # Phase 0 (B1)
            "lower_third": copy.deepcopy(self.lower_third),
            "fullscreen": copy.deepcopy(self.fullscreen),
            "thumbnail_style": copy.deepcopy(self.thumbnail_style),
        }
        new_theme = Theme(data, source_path=self.source_path)
        return new_theme

    def _to_dict(self) -> dict:
        """Serialize to JSON-compatible dict. Keep schema_version v2.0 on save."""
        return {
            "name": self.name,
            "id": self.id,
            "description": self.description,
            "version": self.version,
            "schema_version": self.schema_version,
            "author": getattr(self, "author", ""),
            "colors": self.colors,
            "fonts": self.fonts,
            "animation": self.animation,
            "spacing": self.spacing,
            "typography": self.typography,   # Phase 0 (B1)
            "fullscreen": self.fullscreen,
            "lower_third": self.lower_third,
            "thumbnail_style": self.thumbnail_style,
        }

    def save(self) -> bool:
        """Write theme to its source_path. Returns False if path is None or IO fails.

        Refuses if id is in BUILTIN_THEME_IDS — overwriting a built-in is not allowed.
        Use save_as() to clone a built-in into a user theme.
        """
        if self.source_path is None:
            logger.warning("[Theme] Cannot save: source_path is None")
            return False
        if self.id in BUILTIN_THEME_IDS:
            logger.warning("[Theme] Cannot save built-in theme '%s'. Use Save As.", self.id)
            return False
        try:
            with open(self.source_path, "w", encoding="utf-8") as f:
                json.dump(self._to_dict(), f, indent=2, ensure_ascii=False)
            return True
        except IOError as e:
            logger.error("[Theme] Failed to save '%s': %s", self.id, e)
            return False

    def save_as(self, path: Path, new_id: str, new_name: str) -> "Theme":
        """Write theme to a new path with a new id and name.

        Mutates self.id, self.name, and self.source_path in-place.
        This is safe because callers (ThemeManager.create_theme) always call
        deep_copy() on the source before calling save_as(), so the registry
        instance is never modified. Do not call save_as() on a live registry
        Theme directly — always deep_copy() first. (E9 invariant documented)

        Returns self (the mutated copy) after writing to disk.
        """
        self.id = new_id
        self.name = new_name
        self.source_path = path
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self._to_dict(), f, indent=2, ensure_ascii=False)
        except IOError as e:
            logger.error("[Theme] Failed to save_as '%s': %s", path, e)
            raise
        return self

    def delete(self) -> bool:
        """Delete the theme's source file. Refuses for built-ins.

        Returns True on success, False on failure (built-in, missing path, IO error).
        """
        if self.id in BUILTIN_THEME_IDS:
            logger.warning("[Theme] Cannot delete built-in theme '%s'", self.id)
            return False
        if self.source_path is None or not self.source_path.exists():
            return False
        try:
            self.source_path.unlink()
            thumb_path = self.source_path.with_suffix(".thumb.png")
            thumb_path.unlink(missing_ok=True)
            return True
        except OSError as e:
            logger.error("[Theme] Failed to delete '%s': %s", self.id, e)
            return False


class ThemeManager:
    """Manages loading and applying themes."""

    def __init__(self):
        self._themes: dict[str, Theme] = {}
        self._current: Optional[Theme] = None
        self.application_fonts: set[str] = set()
        self._loaded_font_paths: set[str] = set()
        self._load_builtins()
        self._load_application_fonts()

    def _load_builtins(self):
        """Scan themes/ directory for JSON files."""
        if not THEMES_DIR.exists():
            return
        for p in THEMES_DIR.glob("*.json"):
            try:
                with open(p, encoding="utf-8") as f:
                    data = json.load(f)
                theme = Theme(data, source_path=p)
                self._themes[theme.id] = theme
            except (json.JSONDecodeError, KeyError):
                pass

    def _load_application_fonts(self):
        """Load custom fonts from themes/fonts/ directory.

        Scans for .ttf and .otf files and registers them via QFontDatabase.
        Returns the number of font families loaded. Re-entrant — subsequent
        calls only register newly-added files (per-file tracking via
        _loaded_font_paths).
        """
        if not FONTS_DIR.exists():
            return 0

        from PyQt6.QtGui import QFontDatabase

        count = 0
        for ext in ("*.ttf", "*.otf"):
            for font_file in FONTS_DIR.glob(ext):
                font_path = str(font_file)
                if font_path in self._loaded_font_paths:
                    continue
                try:
                    font_id = QFontDatabase.addApplicationFont(font_path)
                    if font_id >= 0:
                        families = QFontDatabase.applicationFontFamilies(font_id)
                        self.application_fonts.update(families)
                        self._loaded_font_paths.add(font_path)
                        count += len(families)
                except Exception:
                    pass  # Non-fatal: log and continue
        return count

    def available_themes(self) -> list[Theme]:
        return sorted(self._themes.values(), key=lambda t: t.name)

    def get_theme(self, theme_id: str) -> Optional[Theme]:
        return self._themes.get(theme_id)

    def set_theme(self, theme_id: str, app=None) -> bool:
        """Set the global application theme (deprecated for per-channel use).

        DEPRECATED: Use set_app_theme() for the global QSS, and
        DisplayChannel.set_theme() for per-channel themes. This method
        remains for backward compatibility with main.py and settings_panel.py.
        """
        logger.warning("[ThemeManager] set_theme() deprecated. Use set_app_theme().")
        return self.set_app_theme(theme_id, app)

    def set_app_theme(self, theme_id: str, app=None) -> bool:
        """Set the global application theme and generate QSS.

        This is the ONLY method that should call QApplication.setStyleSheet().
        Per-channel themes use DisplayChannel.set_theme() instead.
        """
        theme = self._themes.get(theme_id)
        if theme is None:
            return False
        self._current = theme
        if app is not None:
            app.setStyleSheet(generate_stylesheet(theme))
        return True

    @property
    def current(self) -> Optional[Theme]:
        return self._current

    def reload_theme(self, theme_id: str) -> Optional[Theme]:
        """Re-read the theme JSON from disk and replace the registry instance.

        Used after Save to ensure all channels referencing this theme see the
        updated values. Returns the fresh Theme, or None if the file is gone
        or unparseable.
        """
        theme = self._themes.get(theme_id)
        if theme is None or theme.source_path is None:
            return None
        if not theme.source_path.exists():
            # File was deleted — drop from registry
            del self._themes[theme_id]
            return None
        try:
            with open(theme.source_path, encoding="utf-8") as f:
                data = json.load(f)
            new_theme = Theme(data, source_path=theme.source_path)
            self._themes[theme_id] = new_theme
            return new_theme
        except (json.JSONDecodeError, KeyError) as e:
            logger.error("[ThemeManager] reload_theme '%s' failed: %s", theme_id, e)
            return None

    @staticmethod
    def _sanitize_id(raw_id: str) -> str:
        raw_id = raw_id.strip().lower()
        raw_id = raw_id.replace(" ", "_")
        raw_id = re.sub(r'[^a-z0-9_-]', '', raw_id)
        raw_id = re.sub(r'[_-]{2,}', '_', raw_id)
        return raw_id.strip('_-')

    def create_theme(self, new_id: str, new_name: str, source: Theme) -> Optional[Theme]:
        """Duplicate a source theme to a new file. Returns the new Theme on success.

        Refuses if new_id already exists or contains invalid characters.
        """
        new_id = self._sanitize_id(new_id)
        if not new_id:
            logger.warning("[ThemeManager] Empty theme id after sanitization")
            return None
        if new_id in self._themes:
            logger.warning("[ThemeManager] Theme id '%s' already exists", new_id)
            return None
        new_path = THEMES_DIR / f"{new_id}.json"
        if new_path.exists():
            logger.warning("[ThemeManager] File '%s' already exists", new_path)
            return None
        new_theme = source.deep_copy()
        new_theme.save_as(new_path, new_id, new_name)
        self._themes[new_id] = new_theme
        return new_theme


# ── Stylesheet Generation ────────────────────────────────────────────────────

def generate_stylesheet(theme: Theme) -> str:
    """Generate a full QSS stylesheet from a theme definition."""
    c = theme.c
    f = theme.fonts
    s = theme.spacing

    # ── Typography selectors (Phase 0: Decision 5 token-based loop) ──
    typo_rules = []
    family = f.get("family", "Segoe UI")
    compact_spec = theme.typography.get("compact", TYPOGRAPHY_DEFAULTS["compact"])
    for name, spec in theme.typography.items():
        size = spec.get("size", 9)
        weight = spec.get("weight", "Bold")
        weight_num = WEIGHT_MAP.get(weight, 700)
        uppercase = spec.get("uppercase", False)
        ls = spec.get("letter_spacing", 0)
        color_token = TYPO_COLOR_TOKENS.get(name, "gold")   # Deviation 2: per-entry color

        text_transform = "uppercase" if uppercase else "none"

        typo_rules.append(
            f'QLabel[typography="{name}"] {{\n'
            f'    color: {c(color_token)};\n'
            f'    font-family: "{family}";\n'
            f'    font-size: {size}px;\n'
            f'    font-weight: {weight_num};\n'
            f'    text-transform: {text_transform};\n'
            f'    letter-spacing: {ls}px;\n'
            f'    background: transparent;\n'
            f'}}\n'
        )
        typo_rules.append(
            f'QLabel[section-header="{name}"] {{\n'
            f'    color: {c(color_token)};\n'
            f'    font-family: "{family}";\n'
            f'    font-size: {size}px;\n'
            f'    font-weight: {weight_num};\n'
            f'    text-transform: {text_transform};\n'
            f'    letter-spacing: {ls}px;\n'
            f'    background: transparent;\n'
            f'}}\n'
        )

    typography_qss = "\n".join(typo_rules)

    return f"""
/* ── Global ── */
QMainWindow {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 {c("bg_primary")}, stop:1 {c("bg_secondary")});
    color: {c("text_primary")};
}}
QWidget {{
    background: transparent;
    color: {c("text_primary")};
}}
QMainWindow > QWidget {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 {c("bg_primary")}, stop:1 {c("bg_secondary")});
}}

/* ── Sidebar ── */
QFrame[sidebar="true"] {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 {c("bg_sidebar")}, stop:1 {c("bg_sidebar_end")});
    border-right: 1px solid {c("gold_dim")};
}}

/* ── Panels ── */
QFrame[panel="true"] {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 {c("bg_panel_start")}, stop:1 {c("bg_panel_end")});
    border: 1px solid {c("panel_border")};
    border-radius: {s["border_radius"]}px;
}}
QFrame[panel-dot="true"] {{
    border-radius: 4px;
}}

/* ── Preview ── */
QFrame[preview="true"] {{
    background: qradialgradient(cx:0.5, cy:0.5, radius:1.2,
        fx:0.4, fy:0.3,
        stop:0 {c("bg_preview_center")}, stop:1 {c("bg_preview_edge")});
    border: 1px solid {c("gold_border")};
    border-radius: 16px;
}}

/* ── Cross-Ref Panel ── */
QFrame[crossref="true"] {{
    background: {c("crossref_bg")};
    border: 1px solid {c("crossref_border")};
    border-radius: 8px;
}}

/* ── Draft Panel ── */
QFrame[draft="true"] {{
    background: {c("draft_bg")};
    border: 1px solid {c("draft_border")};
    border-radius: 8px;
}}

/* ── Inputs ── */
QLineEdit {{
    background: {c("bg_input")};
    color: {c("text_primary")};
    border: 1px solid {c("input_border")};
    border-radius: {s["input_border_radius"]}px;
    padding: 0 16px;
    selection-background-color: {c("gold_dim")};
}}
QLineEdit:focus {{
    border: 1px solid {c("input_focus_border")};
}}
QLineEdit::placeholder {{
    color: {c("text_faint")};
}}
QComboBox {{
    background: {c("bg_input")};
    color: {c("text_primary")};
    border: 1px solid {c("input_border")};
    border-radius: {s["input_border_radius"]}px;
    padding: 0 12px;
}}
QComboBox::drop-down {{
    border: none;
    width: 20px;
}}
QComboBox::down-arrow {{
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid {c("gold")};
    width: 0;
    height: 0;
    margin-right: 8px;
}}
QComboBox QAbstractItemView {{
    background: {c("bg_primary")};
    color: {c("text_primary")};
    border: 1px solid {c("input_border")};
    selection-background-color: {c("gold_dim")};
}}

/* ── ScrollAreas ── */
QScrollArea {{
    border: none;
    background: transparent;
}}
QScrollArea > QWidget > QWidget {{
    background: transparent;
}}

/* ── Scrollbars ── */
QScrollBar:vertical {{
    background: transparent;
    width: 6px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {c("scrollbar")};
    border-radius: 3px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{
    background: {c("scrollbar_hover")};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: transparent;
}}

/* ── Status bar ── */
QStatusBar {{
    background: {c("bg_statusbar")};
    color: {c("text_faint")};
    border-top: 1px solid {c("statusbar_border")};
    font-size: 11px;
}}
QStatusBar QLabel {{
    color: {c("text_faint")};
    font-size: 11px;
}}

/* ── PushButtons ── */
QPushButton {{
    background: {c("gold_dim")};
    color: {c("gold")};
    border: 1px solid {c("gold_border")};
    border-radius: 6px;
    padding: 6px 12px;
}}
QPushButton:hover {{
    background: rgba(200,160,60,0.25);
}}
QPushButton:pressed {{
    background: rgba(200,160,60,0.35);
}}

/* ── Cards (settings section groupings) ── */
QFrame[card="true"] {{
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 {c("bg_panel_start")}, stop:1 {c("bg_panel_end")});
    border: 1px solid {c("panel_border")};
    border-radius: {s["card_border_radius"]}px;
}}
/* panel_border_hover intentionally dead after Phase 1 hover removal */

/* ── Typography / Section Headers (Phase 0: Decision 5 token-based loop) ── */
{typography_qss}

/* ── Gold Dot Indicators ── */
QFrame[gold-dot="true"] {{
    background: {c("gold")};
    border-radius: 3px;
}}

/* ── Gold Separator Lines ── */
QFrame[separator="true"] {{
    background: {c("gold_dim")};
    max-height: 1px;
}}

/* ── Hint Labels ── */
QLabel[hint="true"] {{
    color: {c("nav_inactive_text")};
    font-size: 9px;
    background: transparent;
}}

/* ── Error Labels (Phase 1: token-based red_text) ── */
QLabel[error="true"] {{
    color: {c("red_text")};
    background: transparent;
}}

/* ── Result Labels ── */
QLabel[result="true"] {{
    color: {c("gold")};
    background: transparent;
}}

/* ── CheckBoxes ── */
QCheckBox {{
    color: {c("text_primary")};
    spacing: 8px;
    background: transparent;
}}
QCheckBox::indicator {{
    width: 14px;
    height: 14px;
    border: 1px solid {c("input_border")};
    border-radius: 3px;
    background: {c("bg_input")};
}}
QCheckBox::indicator:checked {{
    background: {c("gold_dim")};
    border: 1px solid {c("gold_border")};
}}
QCheckBox::indicator:hover {{
    border: 1px solid {c("input_focus_border")};
}}

/* ── Dialogs ── */
QDialog {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 {c("bg_primary")}, stop:1 {c("bg_secondary")});
    color: {c("text_primary")};
}}
QDialog QLabel {{
    color: {c("text_primary")};
    background: transparent;
}}

/* ── TextEdit ── */
QTextEdit {{
    background: {c("bg_input")};
    color: {c("text_primary")};
    border: 1px solid {c("input_border")};
    border-radius: {s["input_border_radius"]}px;
}}

/* ── Button Accent Variants ── */
QPushButton[accent="gold"] {{
    background: {c("gold_dim")};
    color: {c("gold")};
    border: 1px solid {c("gold_border")};
}}
QPushButton[accent="gold"]:hover {{ background: rgba(200,160,60,0.25); }}
QPushButton[accent="gold"]:pressed {{ background: rgba(200,160,60,0.1); }}

QPushButton[accent="green"] {{
    background: {c("green_dim")};
    color: {c("green")};
    border: 1px solid rgba(76,175,125,0.3);
}}
QPushButton[accent="green"]:hover {{ background: rgba(76,175,125,0.25); }}
QPushButton[accent="green"]:pressed {{ background: rgba(76,175,125,0.15); }}

QPushButton[accent="subtle"] {{
    background: rgba(20,20,36,0.5);
    color: {c("nav_inactive_text")};
    border: 1px solid {c("input_border")};
}}
QPushButton[accent="subtle"]:hover {{
    background: rgba(200,160,60,0.1);
    color: rgba(200,160,60,0.7);
}}

/* ── Nav Tab Buttons (Home/Settings sidebar tabs) ── */
QPushButton[accent="nav-tab-active"] {{
    background: {c("gold_dim")};
    color: {c("gold")};
    border: 1px solid {c("gold_border")};
    border-radius: 4px;
    padding: 0 16px;
    font-weight: 600;
}}
QPushButton[accent="nav-tab"] {{
    background: rgba(20,20,36,0.5);
    color: {c("nav_inactive_text")};
    border: 1px solid {c("input_border")};
    border-radius: 4px;
    padding: 0 16px;
    font-weight: 400;
}}
QPushButton[accent="nav-tab"]:hover {{
    background: rgba(200,160,60,0.10);
    color: rgba(200,160,60,0.7);
}}
/* NOTE: nav-tab base background uses hardcoded rgba(20,20,36,0.5)
   (dark_gold-specific). nav-tab:hover uses hardcoded gold RGBA.
   QSS cannot compose rgba(c("gold"), 0.10) or rgba(c("bg_input"), 0.5).
   Same pattern as accent="subtle" base, accent="gold":hover,
   accent="green":hover, accent="subtle":hover. Known limitation. (R3)
   nav-tab-active intentionally has no :hover/:pressed — the active tab
   stays static (see Deviation 6 item 3). */

/* ── Output Target Segmented Buttons ── */
QPushButton[accent="output-target"] {{
    background: rgba(200,160,60,0.08);
    color: rgba(200,160,60,0.5);
    border: 1px solid rgba(200,160,60,0.15);
    border-radius: 4px;
    padding: 0 12px;
    font-weight: bold;
    font-size: 9px;
}}
QPushButton[accent="output-target"]:checked {{
    background: rgba(200,160,60,0.20);
    color: {c("gold")};
    border: 1px solid rgba(200,160,60,0.40);
}}
QPushButton[accent="output-target"]:hover {{
    background: rgba(200,160,60,0.15);
}}
QPushButton[accent="output-target"]:checked:hover {{
    background: rgba(200,160,60,0.25);
}}
/* NOTE: Output target border uses gold rgba (not input_border token).
   Preserves gold-border visual identity (Finding C). :checked:hover
   added — absent in original inline. */

/* ── Destructive Buttons (Hide, Clear History) ── */
QPushButton[accent="destructive"] {{
    background: {c("red_dim")};
    color: {c("red")};
    border: 1px solid rgba(224,92,75,0.30);
    border-radius: 6px;
}}
QPushButton[accent="destructive"]:hover {{
    background: rgba(224,92,75,0.25);
    border: 1px solid rgba(224,92,75,0.35);
}}
QPushButton[accent="destructive"]:pressed {{
    background: rgba(224,92,75,0.35);
}}
/* NOTE: btn_hide bg=0.15 matches red_dim=0.15 (zero shift).
   btn_clear_history bg=0.12→0.15 (3% shift, minimal).
   btn_clear_history border=0.20→0.30 (10% shift, documented R5).
   Hover/pressed use same hardcoded rgba pattern as accent="gold"
   and accent="green" hover selectors (R3). */

/* ── Mode Toggle (segmented control) ── */
QPushButton[mode-toggle="left"] {{
    background: {c("gold_dim")};
    color: {c("gold")};
    border: 1px solid {c("gold_border")};
    border-radius: 6px 0 0 6px;
    padding: 0 16px;
    font-weight: 600;
}}
QPushButton[mode-toggle="left-inactive"] {{
    background: rgba(20,20,36,0.5);
    color: {c("nav_inactive_text")};
    border: 1px solid {c("input_border")};
    border-radius: 6px 0 0 6px;
    padding: 0 16px;
    font-weight: 400;
}}
QPushButton[mode-toggle="right"] {{
    background: {c("gold_dim")};
    color: {c("gold")};
    border: 1px solid {c("gold_border")};
    border-radius: 0 6px 6px 0;
    padding: 0 16px;
    font-weight: 600;
}}
QPushButton[mode-toggle="right-inactive"] {{
    background: rgba(20,20,36,0.5);
    color: {c("nav_inactive_text")};
    border: 1px solid {c("input_border")};
    border-radius: 0 6px 6px 0;
    padding: 0 16px;
    font-weight: 400;
}}
/* NOTE: No :hover/:pressed rules. ModeToggle has no hover feedback
   in current codebase (verified lines 75-87). Intentional: segmented
   controls typically don't provide hover on active segment. (F8) */

/* ── Gold Dot (green variant for keyword/draft headers) ── */
QFrame[gold-dot-green="true"] {{
    background: {c("green")};
    border-radius: 3px;
}}

/* ── Version Badge (sidebar footer) ── */
QLabel[version-badge="true"] {{
    color: {c("nav_inactive_text")};
    font-size: 8px;
    background: transparent;
}}

/* ── Preview Tab Widget ── */
QTabWidget[preview-tabs="true"]::pane {{
    border: none;
    background: transparent;
}}
QTabWidget[preview-tabs="true"] QTabBar::tab {{
    background: rgba(30,30,50,0.6);
    color: {c("nav_inactive_text")};
    padding: 4px 16px;
    font-weight: bold;
    border: none;
    font-size: 10px;
}}
QTabWidget[preview-tabs="true"] QTabBar::tab:selected {{
    color: {c("gold")};
    background: {c("gold_dim")};
}}
QTabWidget[preview-tabs="true"] QTabBar::tab:hover {{
    color: {c("gold")};
}}

/* ── Compact Combo Mode (Display Mode dropdowns) ── */
QComboBox[combo-mode="true"] {{
    padding: 0 6px;
    border-radius: 4px;
}}

/* ── Section Header: compact-green variant ── */
QLabel[section-header="compact-green"] {{
    color: {c("green")};
    font-family: "{family}";
    font-size: {compact_spec.get("size", 9)}px;
    font-weight: {WEIGHT_MAP.get(compact_spec.get("weight", "Bold"), 700)};
    text-transform: {"uppercase" if compact_spec.get("uppercase", True) else "none"};
    letter-spacing: {compact_spec.get("letter_spacing", 2)}px;
    background: transparent;
}}
/* NOTE: compact-green derives all typography properties from the
   compact scale via compact_spec variable, overriding only color.
   Not a new typography scale — a section-header color variant. (F5)
   Future compact scale changes (e.g., high_contrast at 11px)
   automatically propagate to this variant. */

/* ── Preview Verse Label (set_preview_verse content) ── */
QLabel[preview-verse="true"] {{
    color: {c("text_primary")};
    background: transparent;
    padding: 6px;
}}
/* NOTE: Current inline uses #d8d0c0; theme text_primary = #e8e2d8.
   ~6% brightness shift. Intentional: text_primary is canonical
   verse-content color matching DisplayPreview._render_single_view
   which also uses text_primary. (R2) */

/* ── Theme Designer Widgets (Phase 4) ── */

/* Spin boxes (replaces _spin_style helper — R2) */
QDoubleSpinBox[designer-spin="true"], QSpinBox[designer-spin="true"] {{
    background: {c("bg_input")};
    color: {c("text_primary")};
    border: 1px solid {c("input_border")};
    border-radius: 4px;
    padding: 0 6px;
}}
QDoubleSpinBox[designer-spin="true"]::up-button, QSpinBox[designer-spin="true"]::up-button,
QDoubleSpinBox[designer-spin="true"]::down-button, QSpinBox[designer-spin="true"]::down-button {{
    width: 16px;
    border: none;
    background: {c("gold_dim")};
}}

/* Combo boxes (replaces _combo_style helper — R2) */
QComboBox[designer-combo="true"] {{
    background: {c("bg_input")};
    color: {c("text_primary")};
    border: 1px solid {c("input_border")};
    border-radius: 4px;
    padding: 0 8px;
}}
QComboBox[designer-combo="true"]::drop-down {{
    border: none;
    width: 20px;
}}
QComboBox[designer-combo="true"]::down-arrow {{
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid {c("gold")};
    width: 0;
    height: 0;
    margin-right: 8px;
}}
QComboBox[designer-combo="true"] QAbstractItemView {{
    background: {c("bg_panel_start")};
    color: {c("text_primary")};
    border: 1px solid {c("input_border")};
    selection-background-color: {c("gold_dim")};
}}

/* Mode toggle buttons (replaces _mode_btn_style helper — R2) */
QPushButton[mode-btn="active"] {{
    background: {c("gold_dim")};
    color: {c("gold")};
    border: 1px solid {c("gold_border")};
    border-radius: 3px;
    padding: 0 10px;
}}
QPushButton[mode-btn="inactive"] {{
    background: {c("bg_input")};
    color: {c("nav_inactive_text")};
    border: 1px solid {c("input_border")};
    border-radius: 3px;
    padding: 0 10px;
}}
QPushButton[mode-btn="inactive"]:hover {{
    background: {c("gold_dim")};
    color: {c("gold")};
}}

/* Designer panel backgrounds */
QFrame[designer-panel="true"], QScrollArea[designer-panel="true"] {{
    background: {c("bg_panel_start")};
    border: 1px solid {c("input_border")};
    border-radius: 8px;
}}
QScrollArea[designer-scroll="true"] {{
    background: {c("bg_input")};
    border: 1px solid {c("panel_border")};
    border-radius: 4px;
}}

/* Designer action buttons (New/Duplicate/Delete/Save/SaveAs/Delete in header) */
QPushButton[designer-action-btn="true"] {{
    background: {c("bg_input")};
    color: {c("nav_inactive_text")};
    border: 1px solid {c("input_border")};
    border-radius: 4px;
    padding: 0 16px;
    font-family: 'Segoe UI';
    font-size: 10px;
}}
QPushButton[designer-action-btn="true"]:hover {{
    background: {c("gold_dim")};
    color: {c("gold")};
    border: 1px solid {c("gold_border")};
}}
QPushButton[designer-action-btn="true"]:disabled {{
    color: {c("text_faint")};
    border: 1px solid {c("input_border")};
}}

/* Designer header bar (50px top bar) */
QFrame[designer-header="true"] {{
    background: {c("bg_sidebar")};
    border-bottom: 1px solid {c("input_border")};
}}
QLabel[designer-title="true"] {{
    color: {c("text_primary")};
}}

/* Designer utility widgets */
QCheckBox[designer-checkbox="true"] {{
    color: {c("text_dim")};
}}
QCheckBox[designer-checkbox="true"]::indicator {{
    width: 16px;
    height: 16px;
}}
QLineEdit[designer-input="true"] {{
    background: {c("bg_input")};
    color: {c("text_primary")};
    border: 1px solid {c("input_border")};
    border-radius: 4px;
    padding: 0 8px;
}}
QPushButton[designer-browse-btn="true"] {{
    background: {c("bg_input")};
    color: {c("nav_inactive_text")};
    border: 1px solid {c("input_border")};
    border-radius: 4px;
}}
QPushButton[designer-browse-btn="true"]:hover {{
    background: {c("gold_dim")};
    color: {c("gold")};
}}

/* Thumb fallback placeholder (Step 7a) */
QLabel[thumb-fallback="true"] {{
    background: rgba(128,128,128,0.15);
    color: rgba(128,128,128,0.6);
    border: 1px dashed rgba(128,128,128,0.3);
    border-radius: 4px;
}}

/* ── ThemeCardWidget (grid thumbnails) ── */
ThemeCardWidget {{
    background: rgba(15, 15, 26, 0.3);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 6px;
}}
ThemeCardWidget:hover {{
    background: {c("card_hover_bg")};
    border: 1px solid {c("card_hover_border")};
}}
ThemeCardWidget[selected="true"] {{
    background: {c("card_highlight_bg")};
    border: 2px solid {c("card_highlight_border")};
}}
ThemeCardWidget[builtin="true"] QLabel {{
    color: {c("gold")};
}}
ThemeCardWidget[builtin="false"] QLabel {{
    color: {c("text_primary")};
}}
"""


def apply_theme(theme_id: str, app):
    """Convenience: load theme and apply to QApplication."""
    mgr = ThemeManager()
    mgr.set_theme(theme_id, app=app)
    return mgr
