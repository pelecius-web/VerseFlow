"""theme.py — VerseFlow Theme Engine

Loads JSON theme definitions and generates QSS stylesheets.
Supports: Dark Gold, Light, High Contrast, and custom themes.
"""

import json
from pathlib import Path
from typing import Optional

THEMES_DIR = Path(__file__).parent / "themes"
DEFAULT_THEME = "dark_gold"

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


class Theme:
    """Represents a loaded theme definition."""

    def __init__(self, data: dict):
        self.name: str = data.get("name", "Unknown")
        self.id: str = data.get("id", "unknown")
        self.description: str = data.get("description", "")
        self.version: str = data.get("version", "1.0")
        self.colors: dict = data.get("colors", {})
        self.fonts: dict = data.get("fonts", {})
        self.animation: dict = data.get("animation", {})
        self.spacing: dict = data.get("spacing", {})
        self.lower_third: dict = data.get("lower_third", {})

    def c(self, key: str) -> str:
        """Shorthand for color lookup."""
        return self.colors.get(key, "#000000")


class ThemeManager:
    """Manages loading and applying themes."""

    def __init__(self):
        self._themes: dict[str, Theme] = {}
        self._current: Optional[Theme] = None
        self._load_builtins()

    def _load_builtins(self):
        """Scan themes/ directory for JSON files."""
        if not THEMES_DIR.exists():
            return
        for p in THEMES_DIR.glob("*.json"):
            try:
                with open(p, encoding="utf-8") as f:
                    data = json.load(f)
                theme = Theme(data)
                self._themes[theme.id] = theme
            except (json.JSONDecodeError, KeyError):
                pass

    def available_themes(self) -> list[Theme]:
        return sorted(self._themes.values(), key=lambda t: t.name)

    def get_theme(self, theme_id: str) -> Optional[Theme]:
        return self._themes.get(theme_id)

    def set_theme(self, theme_id: str, app=None) -> bool:
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


# ── Stylesheet Generation ────────────────────────────────────────────────────

def generate_stylesheet(theme: Theme) -> str:
    """Generate a full QSS stylesheet from a theme definition."""
    c = theme.c
    f = theme.fonts
    s = theme.spacing

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
QFrame[panel="true"]:hover {{
    border: 1px solid {c("panel_border_hover")};
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
"""


def apply_theme(theme_id: str, app):
    """Convenience: load theme and apply to QApplication."""
    mgr = ThemeManager()
    mgr.set_theme(theme_id, app=app)
    return mgr
