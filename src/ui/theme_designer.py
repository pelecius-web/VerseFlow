"""theme_designer.py — VerseFlow Theme Designer Panel (v1.3.0 Phase 2)

Three-panel UI (themes list / live preview / property editor) for editing
congregation-display themes. The center preview embeds a real DisplayWidget
instance — pixel-identical to what the congregation sees.

Key design rules:
  - Editing always operates on a deep_copy() of a registry Theme.
    Mutations never propagate until explicit Save.
  - Save and Apply are gated during live service (override dialog escape hatch).
  - Built-in themes (dark_gold, light, high_contrast) are read-only.
  - The preview's DisplayWidget uses a _DummyDisplayController — never the
    real one — so sample verses never pollute Live History and NDI never
    captures designer frames.
  - Property scope is the curated 33 keys that DisplayWidget actually reads.
    The ~70 operator-panel QSS keys are excluded because edits would produce
    zero visible change in the preview.
"""

import logging
import math
import re
import random as _random
from dataclasses import dataclass
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal, QObject, QTimer, QRectF
from PyQt6.QtGui import (
    QFont, QColor, QKeySequence, QPixmap, QIcon, QPainter, QLinearGradient,
    QTextDocument, QTextOption, QTextCursor, QTextCharFormat,
)
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame,
    QLabel, QPushButton,
    QScrollArea, QGridLayout, QSplitter, QComboBox, QDoubleSpinBox,
    QSpinBox, QCheckBox, QFontComboBox, QLineEdit,
    QColorDialog, QInputDialog, QMessageBox, QSizePolicy,
    QButtonGroup, QFileDialog, QApplication,
)

from theme import Theme, ThemeManager, WEIGHT_MAP, BUILTIN_THEME_IDS
from display_widget import DisplayWidget
from constants import DISPLAY_MODE_FULLSCREEN, DISPLAY_MODE_LOWER_THIRD
from icons import get_palette_icon, get_layers_icon, get_settings_gear_icon

logger = logging.getLogger("VerseFlow")


# ── Schema descriptor ────────────────────────────────────────────────────────

@dataclass(frozen=True)
class PropertySpec:
    """Descriptor for one editable theme property.

    json_path:    Dotted path on Theme (e.g., "lower_third.background_color")
    label:        Human-readable label shown in the editor
    widget_kind:  One of "color", "float", "int", "bool", "font_family",
                  "font_weight", "image_path", "enum"
    section:      Group label ("Display Colors", "Fullscreen", "Lower-Third")
    options:      Optional dict — for "enum" gives choices, for "float" gives min/max/step,
                  for "image_path" gives extensions
    tooltip:      Optional hover text
    """
    json_path: str
    label: str
    widget_kind: str
    section: str
    options: Optional[dict] = None
    tooltip: Optional[str] = None


# ── 33-property schema ──────────────────────────────────────────────────────

THEME_EDITOR_SCHEMA: list[PropertySpec] = [
    # ── Operator-Visible Display Colors (5) ────────────────────────────────
    # These five drive _apply_theme_styling on DisplayWidget itself.
    # Confirmed by code trace: c('gold'), c('bg_primary'), c('bg_secondary'),
    # c('text_primary'), c('text_faint') in display_widget.py:948-1009.
    PropertySpec("colors.gold",         "Accent (gold)",     "color", "Display Colors"),
    PropertySpec("colors.bg_primary",   "Background — top",  "color", "Display Colors"),
    PropertySpec("colors.bg_secondary", "Background — bottom","color","Display Colors"),
    PropertySpec("colors.text_primary", "Verse text",        "color", "Display Colors"),
    PropertySpec("colors.text_faint",   "Footer / faint",    "color", "Display Colors"),

    # ── Fullscreen mode (10) ───────────────────────────────────────────────
    PropertySpec("fullscreen.background_color",         "Background color",   "color",       "Fullscreen"),
    PropertySpec("fullscreen.background_image",         "Background image",   "image_path",  "Fullscreen",
                 options={"extensions": [".png", ".jpg", ".jpeg", ".svg"]}),
    PropertySpec("fullscreen.background_image_fit",     "Image fit",          "enum",        "Fullscreen",
                 options={"choices": ["cover", "contain", "stretch", "tile"]}),
    PropertySpec("fullscreen.background_image_opacity", "Image opacity",      "float",       "Fullscreen",
                 options={"min": 0.0, "max": 1.0, "step": 0.05}),
    PropertySpec("fullscreen.ref_color",                "Reference color",    "color",       "Fullscreen"),
    PropertySpec("fullscreen.verse_color",              "Verse color",        "color",       "Fullscreen"),
    PropertySpec("fullscreen.ref_font_family",          "Reference font",     "font_family", "Fullscreen"),
    PropertySpec("fullscreen.ref_font_weight",          "Reference weight",   "font_weight", "Fullscreen"),
    PropertySpec("fullscreen.verse_font_family",        "Verse font",         "font_family", "Fullscreen"),
    PropertySpec("fullscreen.verse_font_weight",        "Verse weight",       "font_weight", "Fullscreen"),

    # ── Lower-third mode (20) ──────────────────────────────────────────────
    PropertySpec("lower_third.background_color",      "Band color",          "color",       "Lower-Third"),
    PropertySpec("lower_third.background_alpha",      "Band opacity",        "float",       "Lower-Third",
                 options={"min": 0.0, "max": 1.0, "step": 0.05}),
    PropertySpec("lower_third.background_image",      "Band image",          "image_path",  "Lower-Third",
                 options={"extensions": [".png", ".jpg", ".jpeg", ".svg"]}),
    PropertySpec("lower_third.background_image_fit",  "Band image fit",      "enum",        "Lower-Third",
                 options={"choices": ["cover", "contain", "stretch", "tile"]}),
    PropertySpec("lower_third.height_ratio",          "Band height (× win)", "float",       "Lower-Third",
                 options={"min": 0.10, "max": 0.50, "step": 0.01}),
    PropertySpec("lower_third.accent_color",          "Accent color",        "color",       "Lower-Third"),
    PropertySpec("lower_third.ref_color",             "Reference color",     "color",       "Lower-Third"),
    PropertySpec("lower_third.verse_color",           "Verse color",         "color",       "Lower-Third"),
    PropertySpec("lower_third.ref_font_family",       "Reference font",      "font_family", "Lower-Third"),
    PropertySpec("lower_third.verse_font_family",     "Verse font",          "font_family", "Lower-Third"),
    PropertySpec("lower_third.ref_font_weight",       "Reference weight",    "font_weight", "Lower-Third"),
    PropertySpec("lower_third.verse_font_weight",     "Verse weight",        "font_weight", "Lower-Third"),
    PropertySpec("lower_third.church_name_color",     "Church name color",   "color",       "Lower-Third"),
    PropertySpec("lower_third.logo_path",             "Logo image",          "image_path",  "Lower-Third",
                 options={"extensions": [".png", ".jpg", ".jpeg", ".svg"]}),
    PropertySpec("lower_third.show_logo_placeholder", "Show placeholder",    "bool",        "Lower-Third"),
    PropertySpec("lower_third.logo_width_ratio",      "Logo width (× win)",  "float",       "Lower-Third",
                 options={"min": 0.05, "max": 0.30, "step": 0.01}),
    PropertySpec("lower_third.logo_max_height_ratio", "Logo max height (× band)", "float",  "Lower-Third",
                 options={"min": 0.40, "max": 1.00, "step": 0.05}),
    PropertySpec("lower_third.show_separator",        "Show separator",      "bool",        "Lower-Third"),
    PropertySpec("lower_third.separator_color",       "Separator color",     "color",       "Lower-Third"),
    PropertySpec("lower_third.separator_width",       "Separator width (px)","int",         "Lower-Third",
                 options={"min": 1, "max": 8, "step": 1}),
    # NOTE: lower_third.transition.{type,duration_ms} are deferred to Phase 3.
]


# ── Sample verses ────────────────────────────────────────────────────────────

SAMPLE_VERSES: list[dict] = [
    {
        "reference": "John 3:16",
        "translation": "KJV",
        "text": "For God so loved the world, that he gave his only begotten Son, "
                "that whosoever believeth in him should not perish, but have everlasting life.",
    },
    {
        "reference": "Psalm 23:1",
        "translation": "KJV",
        "text": "The LORD is my shepherd; I shall not want.",
    },
    {
        "reference": "Romans 8:28",
        "translation": "KJV",
        "text": "And we know that all things work together for good to them that love God, "
                "to them who are the called according to his purpose.",
    },
    {
        "reference": "Hebrews 1:1-3",
        "translation": "KJV",
        "text": "God, who at sundry times and in divers manners spake in time past unto the "
                "fathers by the prophets, hath in these last days spoken unto us by his Son, "
                "whom he hath appointed heir of all things, by whom also he made the worlds; "
                "who being the brightness of his glory, and the express image of his person, "
                "and upholding all things by the word of his power.",
    },
]


# ── Sandbox controller ───────────────────────────────────────────────────────

class _DummyDisplayController(QObject):
    """Sandboxed controller for designer preview. No DB, no window, no live history."""
    verse_changed = pyqtSignal(dict)
    layout_changed = pyqtSignal(str)
    translations_changed = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current = None
        self.secondary_translations = []

    def push_verse(self, verse: dict):
        self.current = verse
        self.verse_changed.emit(verse)
        self.translations_changed.emit(self.secondary_translations)

    def clear(self):
        self.current = None
        self.verse_changed.emit({})
        self.translations_changed.emit([])


# ── Module-level helpers ──────────────────────────────────────────────────────

def _make_column_header(title: str, icon: QIcon = None) -> QWidget:
    """Create a standard-variant section header for Theme Designer column titles.

    Uses the typography system's 'standard' variant and the 'gold-dot' QSS selector.
    Optionally includes a 16px icon to the left of the gold dot.
    Pattern matches SettingsPanel._make_section_header (variant="standard", icon=QIcon).
    """
    container = QWidget()
    layout = QHBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(8)
    if icon is not None:
        icon_label = QLabel()
        icon_label.setPixmap(icon.pixmap(16, 16))
        icon_label.setFixedSize(16, 16)
        layout.addWidget(icon_label)
    dot = QFrame()
    dot.setFixedSize(6, 6)
    dot.setProperty("gold-dot", True)
    layout.addWidget(dot)
    label = QLabel(title.upper())
    label.setProperty("section-header", "standard")
    layout.addWidget(label)
    layout.addStretch()
    return container


# ── Theme Card Widget ──────────────────────────────────────────────────────

class ThemeCardWidget(QFrame):
    """Visual theme selector card. Displays thumbnail on top and name below.

    Styled cleanly via global stylesheet rules.
    """
    clicked = pyqtSignal(str)  # Emits theme_id

    def __init__(self, theme_id: str, name: str, thumb_path: str, is_builtin: bool, parent=None):
        super().__init__(parent)
        self.theme_id = theme_id
        self.name = name
        self.thumb_path = thumb_path
        self.is_builtin = is_builtin
        self._selected = False
        self._setup_ui()

    def _setup_ui(self):
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)

        self.thumb_lbl = QLabel()
        self.thumb_lbl.setFixedSize(300, 96)
        self.thumb_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        from pathlib import Path
        if self.thumb_path and Path(self.thumb_path).exists():
            pixmap = QPixmap(self.thumb_path)
            self.thumb_lbl.setPixmap(pixmap)
            self.thumb_lbl.setScaledContents(True)
        else:
            self.thumb_lbl.setText("No Preview")
            self.thumb_lbl.setFont(QFont("Segoe UI", 7))
            self.thumb_lbl.setProperty("thumb-fallback", True)
        layout.addWidget(self.thumb_lbl)

        self.name_lbl = QLabel(self.name)
        self.name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.name_lbl.setFont(QFont("Segoe UI", 8))
        layout.addWidget(self.name_lbl)
        self.setProperty("builtin", self.is_builtin)

        self.update_style()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.theme_id)

    def set_selected(self, selected: bool):
        self._selected = selected
        self.update_style()

    def update_style(self):
        self.setProperty("selected", self._selected)
        self.style().unpolish(self)
        self.style().polish(self)


# ── Themes List Panel (left column) ─────────────────────────────────────────

class ThemesListPanel(QFrame):
    """Left column: list of available themes in a 2-column thumbnail grid."""

    theme_selected = pyqtSignal(str)
    new_requested = pyqtSignal()
    duplicate_requested = pyqtSignal(str)
    delete_requested = pyqtSignal(str)

    def __init__(self, theme_mgr: ThemeManager, parent=None):
        super().__init__(parent)
        self._theme_mgr = theme_mgr
        self._cards: dict[str, ThemeCardWidget] = {}
        self._setup_ui()

    def _setup_ui(self):
        self.setFixedWidth(340)
        self.setProperty("designer-panel", True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        layout.addWidget(_make_column_header("Themes", icon=get_palette_icon(size=16)))

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setProperty("designer-scroll", True)

        self._scroll_content = QWidget()
        self._grid = QGridLayout(self._scroll_content)
        self._grid.setContentsMargins(6, 6, 6, 6)
        self._grid.setSpacing(8)
        self._scroll.setWidget(self._scroll_content)
        layout.addWidget(self._scroll, 1)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(4)

        self._new_btn = QPushButton("New")
        self._new_btn.setProperty("designer-action-btn", True)
        self._new_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._new_btn.clicked.connect(self.new_requested.emit)
        btn_row.addWidget(self._new_btn)

        self._dup_btn = QPushButton("Duplicate")
        self._dup_btn.setProperty("designer-action-btn", True)
        self._dup_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._dup_btn.clicked.connect(self._on_duplicate)
        self._dup_btn.setEnabled(False)
        btn_row.addWidget(self._dup_btn)

        self._del_btn = QPushButton("Delete")
        self._del_btn.setProperty("designer-action-btn", True)
        self._del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._del_btn.clicked.connect(self._on_delete)
        self._del_btn.setEnabled(False)
        btn_row.addWidget(self._del_btn)

        layout.addLayout(btn_row)
        self.refresh_list()

    def refresh_list(self):
        """Re-populate the single-column grid from theme manager registry."""
        while self._grid.count():
            item = self._grid.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        self._cards.clear()
        for row, theme in enumerate(self._theme_mgr.available_themes()):
            thumb_path = None
            if theme.source_path:
                thumb_path = str(theme.source_path.with_suffix(".thumb.png"))
            is_builtin = theme.id in BUILTIN_THEME_IDS

            card = ThemeCardWidget(theme.id, theme.name, thumb_path, is_builtin, self)
            card.clicked.connect(self._on_card_clicked)
            self._cards[theme.id] = card

            self._grid.addWidget(card, row, 0)

        self._grid.setRowStretch(row + 1, 1)

    def current_theme_id(self) -> Optional[str]:
        for theme_id, card in self._cards.items():
            if card._selected:
                return theme_id
        return None

    def reselect(self, theme_id: str):
        self._select_card(theme_id)

    def _select_card(self, theme_id: str):
        for card_id, card in self._cards.items():
            card.set_selected(card_id == theme_id)
        self._update_button_states(theme_id)

    def _on_card_clicked(self, theme_id: str):
        self._select_card(theme_id)
        self.theme_selected.emit(theme_id)

    def _update_button_states(self, theme_id: str):
        is_builtin = theme_id in BUILTIN_THEME_IDS
        self._dup_btn.setEnabled(True)
        self._del_btn.setEnabled(not is_builtin)

    def _on_duplicate(self):
        theme_id = self.current_theme_id()
        if theme_id:
            self.duplicate_requested.emit(theme_id)

    def _on_delete(self):
        theme_id = self.current_theme_id()
        if theme_id and theme_id not in BUILTIN_THEME_IDS:
            self.delete_requested.emit(theme_id)


# ── Preview Surface (center column) ──────────────────────────────────────────

class PreviewSurface(QFrame):
    """Center column: embedded DisplayWidget + mode toggle + verse picker + Apply."""

    apply_requested = pyqtSignal(str)  # target: "main", "alt", "both"

    def __init__(self, theme_mgr: ThemeManager, parent=None):
        super().__init__(parent)
        self._theme_mgr = theme_mgr
        self._dummy = _DummyDisplayController()
        self._current_verse: dict = SAMPLE_VERSES[0]
        self._setup_ui()

    @property
    def dummy_controller(self):
        """Public property to access the sandbox dummy controller."""
        return self._dummy

    @property
    def current_verse(self):
        """Public property to read the currently-selected sample verse."""
        return self._current_verse

    def _setup_ui(self):
        self.setProperty("designer-panel", True)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        layout.addWidget(_make_column_header("Preview", icon=get_layers_icon()))

        # Mode toggle row
        mode_row = QHBoxLayout()
        mode_row.setSpacing(4)

        mode_label = QLabel("Mode:")
        mode_label.setProperty("typography", "hint")
        mode_row.addWidget(mode_label)

        self._mode_group = QButtonGroup(self)
        self._fs_btn = QPushButton("Fullscreen")
        self._fs_btn.setFixedHeight(28)
        self._fs_btn.setFont(QFont("Segoe UI", 9))
        self._fs_btn.setProperty("mode-btn", "active")
        self._fs_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._mode_group.addButton(self._fs_btn)
        mode_row.addWidget(self._fs_btn)

        self._lt_btn = QPushButton("Lower-Third")
        self._lt_btn.setFixedHeight(28)
        self._lt_btn.setFont(QFont("Segoe UI", 9))
        self._lt_btn.setProperty("mode-btn", "inactive")
        self._lt_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._mode_group.addButton(self._lt_btn)
        mode_row.addWidget(self._lt_btn)

        self._mode_group.buttonClicked.connect(self._on_mode_toggle)
        mode_row.addStretch()
        layout.addLayout(mode_row)

        # Sample verse picker row
        verse_row = QHBoxLayout()
        verse_row.setSpacing(6)

        verse_label = QLabel("Verse:")
        verse_label.setProperty("typography", "hint")
        verse_row.addWidget(verse_label)

        self._verse_combo = QComboBox()
        self._verse_combo.setFixedHeight(28)
        self._verse_combo.setFont(QFont("Segoe UI", 9))
        self._verse_combo.setProperty("designer-combo", True)
        for v in SAMPLE_VERSES:
            self._verse_combo.addItem(v["reference"])
        self._verse_combo.currentIndexChanged.connect(self._on_verse_changed)
        verse_row.addWidget(self._verse_combo, 1)
        layout.addLayout(verse_row)

        # Embedded DisplayWidget (expanding)
        self._display_widget = DisplayWidget(
            display_controller=self._dummy,
            theme_manager=self._theme_mgr,
            church_name="Sample Church",
        )
        self._display_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self._display_widget, 1)

        # Apply controls row
        apply_row = QHBoxLayout()
        apply_row.setSpacing(6)

        target_label = QLabel("Apply to:")
        target_label.setProperty("typography", "hint")
        apply_row.addWidget(target_label)

        self._target_combo = QComboBox()
        self._target_combo.setFixedHeight(28)
        self._target_combo.setFont(QFont("Segoe UI", 9))
        self._target_combo.addItems(["Main", "Alt", "Both"])
        self._target_combo.setProperty("designer-combo", True)
        apply_row.addWidget(self._target_combo)

        self._apply_btn = QPushButton("Apply")
        self._apply_btn.setFixedHeight(28)
        self._apply_btn.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self._apply_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._apply_btn.setProperty("accent", "green")
        self._apply_btn.clicked.connect(self._on_apply)
        apply_row.addWidget(self._apply_btn)

        apply_row.addStretch()
        layout.addLayout(apply_row)

        # Push initial verse to preview
        self._dummy.push_verse(self._current_verse)

    def set_theme(self, theme: Theme):
        """Apply theme to the embedded DisplayWidget and push current verse."""
        self._display_widget.set_theme(theme)
        self._dummy.push_verse(self._current_verse)

    def set_display_mode(self, mode: str):
        """Set display mode on the embedded widget and re-push verse."""
        self._display_widget.set_display_mode(mode)
        self._dummy.push_verse(self._current_verse)
        self._update_mode_buttons(mode)

    def refresh(self):
        """Re-apply current theme + verse (cheap repaint)."""
        self._display_widget.set_theme(self._display_widget._theme)
        self._dummy.push_verse(self._current_verse)

    def clear_theme(self):
        """Clear preview to blank state."""
        self._dummy.clear()
        self._display_widget._clear_all_mode_content()

    def _on_mode_toggle(self, button):
        if button is self._fs_btn:
            self.set_display_mode(DISPLAY_MODE_FULLSCREEN)
        else:
            self.set_display_mode(DISPLAY_MODE_LOWER_THIRD)

    def _on_verse_changed(self, index: int):
        if 0 <= index < len(SAMPLE_VERSES):
            self._current_verse = SAMPLE_VERSES[index]
            self._dummy.push_verse(self._current_verse)

    def _on_apply(self):
        target = self._target_combo.currentText().lower()
        self.apply_requested.emit(target)

    def _update_mode_buttons(self, mode: str):
        is_fs = mode == DISPLAY_MODE_FULLSCREEN
        self._fs_btn.setProperty("mode-btn", "active" if is_fs else "inactive")
        self._fs_btn.style().unpolish(self._fs_btn)
        self._fs_btn.style().polish(self._fs_btn)
        self._lt_btn.setProperty("mode-btn", "inactive" if is_fs else "active")
        self._lt_btn.style().unpolish(self._lt_btn)
        self._lt_btn.style().polish(self._lt_btn)


# ── Property Editor (right column) ───────────────────────────────────────────

class PropertyEditor(QScrollArea):
    """Right column: auto-generated property rows from THEME_EDITOR_SCHEMA."""

    property_changed = pyqtSignal(str, object)  # (json_path, new_value)

    def __init__(self, theme_mgr: ThemeManager, parent=None):
        super().__init__(parent)
        self._theme_mgr = theme_mgr
        self._widgets: dict[str, QWidget] = {}  # json_path → widget
        self._theme_dir = None  # set by load_theme for relpath computation
        self._setup_ui()

    def _setup_ui(self):
        self.setFixedWidth(380)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setProperty("designer-panel", True)

        container = QWidget()
        self._container_layout = QVBoxLayout(container)
        self._container_layout.setContentsMargins(12, 12, 12, 12)
        self._container_layout.setSpacing(6)

        self._container_layout.addWidget(_make_column_header("Properties", icon=get_settings_gear_icon()))

        # Group by section
        current_section = None
        for spec in THEME_EDITOR_SCHEMA:
            if spec.section != current_section:
                current_section = spec.section
                section_header = QLabel(spec.section)
                section_header.setProperty("section-header", "standard")
                self._container_layout.addWidget(section_header)

            self._add_property_row(spec)

        self._container_layout.addStretch()
        self.setWidget(container)

    def _add_property_row(self, spec: PropertySpec):
        row = QHBoxLayout()
        row.setSpacing(8)

        # Label
        label = QLabel(spec.label.upper())
        label.setProperty("typography", "compact")
        label.setFixedWidth(110)
        if spec.tooltip:
            label.setToolTip(spec.tooltip)
        row.addWidget(label)

        # Widget
        widget = self._create_widget(spec)
        # For image_path, the widget is a container; store the inner QLineEdit
        # For font_family, the widget is a container; store the inner QFontComboBox
        if spec.widget_kind == "image_path":
            inner = widget.findChild(QLineEdit)
            if inner is not None:
                self._widgets[spec.json_path] = inner
            else:
                self._widgets[spec.json_path] = widget
        elif spec.widget_kind == "font_family":
            inner = widget.findChild(QFontComboBox)
            if inner is not None:
                self._widgets[spec.json_path] = inner
            else:
                self._widgets[spec.json_path] = widget
        else:
            self._widgets[spec.json_path] = widget
        row.addWidget(widget, 1)

        self._container_layout.addLayout(row)

    def _create_widget(self, spec: PropertySpec) -> QWidget:
        kind = spec.widget_kind

        if kind == "color":
            btn = QPushButton()
            btn.setFixedSize(40, 28)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    border: 2px solid rgba(255,255,255,0.15);
                    border-radius: 4px;
                }
            """)
            btn.clicked.connect(lambda: self._pick_color(spec.json_path, btn))
            btn.setProperty("_json_path", spec.json_path)
            return btn

        if kind == "float":
            spin = QDoubleSpinBox()
            spin.setDecimals(2)
            opts = spec.options or {}
            spin.setRange(opts.get("min", 0.0), opts.get("max", 1.0))
            spin.setSingleStep(opts.get("step", 0.01))
            spin.setFixedHeight(28)
            spin.setFont(QFont("Segoe UI", 9))
            spin.setProperty("designer-spin", True)
            spin.valueChanged.connect(lambda v, p=spec.json_path: self.property_changed.emit(p, v))
            spin.setProperty("_json_path", spec.json_path)
            return spin

        if kind == "int":
            spin = QSpinBox()
            opts = spec.options or {}
            spin.setRange(opts.get("min", 0), opts.get("max", 100))
            spin.setSingleStep(opts.get("step", 1))
            spin.setFixedHeight(28)
            spin.setFont(QFont("Segoe UI", 9))
            spin.setProperty("designer-spin", True)
            spin.valueChanged.connect(lambda v, p=spec.json_path: self.property_changed.emit(p, v))
            spin.setProperty("_json_path", spec.json_path)
            return spin

        if kind == "bool":
            cb = QCheckBox()
            cb.setFont(QFont("Segoe UI", 9))
            cb.setProperty("designer-checkbox", True)
            cb.toggled.connect(lambda v, p=spec.json_path: self.property_changed.emit(p, v))
            cb.setProperty("_json_path", spec.json_path)
            return cb

        if kind == "font_family":
            container = QWidget()
            row = QHBoxLayout(container)
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(4)
            combo = QFontComboBox()
            combo.setFixedHeight(28)
            combo.setMinimumWidth(0)
            combo.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
            combo.setFont(QFont("Segoe UI", 9))
            combo.setProperty("designer-combo", True)
            combo.currentFontChanged.connect(
                lambda f, p=spec.json_path: self.property_changed.emit(p, f.family())
            )
            combo.setProperty("_json_path", spec.json_path)
            row.addWidget(combo, 1)
            btn = QPushButton("Import")
            btn.setFixedHeight(28)
            btn.setFixedWidth(60)
            btn.setFont(QFont("Segoe UI", 8))
            btn.setProperty("accent", "gold")
            btn.clicked.connect(lambda checked, c=combo: self._import_font(c))
            row.addWidget(btn)
            return container

        if kind == "font_weight":
            combo = QComboBox()
            combo.setFixedHeight(28)
            combo.setFont(QFont("Segoe UI", 9))
            combo.setProperty("designer-combo", True)
            combo.addItems(WEIGHT_MAP.keys())
            combo.currentTextChanged.connect(
                lambda t, p=spec.json_path: self.property_changed.emit(p, t)
            )
            combo.setProperty("_json_path", spec.json_path)
            return combo

        if kind == "image_path":
            container = QWidget()
            h = QHBoxLayout(container)
            h.setContentsMargins(0, 0, 0, 0)
            h.setSpacing(4)

            line = QLineEdit()
            line.setFixedHeight(28)
            line.setFont(QFont("Segoe UI", 9))
            line.setProperty("designer-input", True)
            line.editingFinished.connect(lambda p=spec.json_path: self.property_changed.emit(p, line.text()))
            line.setProperty("_json_path", spec.json_path)
            h.addWidget(line, 1)

            browse_btn = QPushButton("…")
            browse_btn.setFixedSize(28, 28)
            browse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            browse_btn.setProperty("designer-browse-btn", True)
            exts = (spec.options or {}).get("extensions", [".png", ".jpg"])
            browse_btn.clicked.connect(lambda: self._browse_image(line, spec.json_path, exts))
            h.addWidget(browse_btn)

            return container

        if kind == "enum":
            combo = QComboBox()
            combo.setFixedHeight(28)
            combo.setFont(QFont("Segoe UI", 9))
            combo.setProperty("designer-combo", True)
            choices = (spec.options or {}).get("choices", [])
            combo.addItems(choices)
            combo.currentTextChanged.connect(
                lambda t, p=spec.json_path: self.property_changed.emit(p, t)
            )
            combo.setProperty("_json_path", spec.json_path)
            return combo

        # Fallback: QLineEdit for unknown widget kinds
        line = QLineEdit()
        line.setFixedHeight(28)
        line.setProperty("designer-input", True)
        return line

    def load_theme(self, theme: Theme):
        """Populate every row from the theme's current values."""
        # Cache theme directory for relative path computation
        if theme.source_path is not None:
            self._theme_dir = theme.source_path.parent
        else:
            self._theme_dir = None
        for spec in THEME_EDITOR_SCHEMA:
            value = self._resolve_path(theme, spec.json_path)
            widget = self._widgets.get(spec.json_path)
            if widget is None:
                continue

            widget.blockSignals(True)
            kind = spec.widget_kind

            if kind == "color":
                color_val = value or "#000000"
                widget.setStyleSheet(
                    f"QPushButton {{ background: {color_val}; border: 2px solid rgba(255,255,255,0.15); border-radius: 4px; }}"
                )
                widget.setProperty("_color_value", color_val)

            elif kind in ("float", "int"):
                if value is not None:
                    widget.setValue(value)

            elif kind == "bool":
                widget.setChecked(bool(value))

            elif kind == "font_family":
                if value:
                    widget.setCurrentFont(QFont(value))

            elif kind == "font_weight":
                if value and value in WEIGHT_MAP:
                    idx = list(WEIGHT_MAP.keys()).index(value)
                    widget.setCurrentIndex(idx)

            elif kind == "image_path":
                # image_path stores a QLineEdit inside a container widget
                if value is not None:
                    widget.setText(str(value))
                else:
                    widget.setText("")

            elif kind == "enum":
                if value:
                    idx = widget.findText(str(value))
                    if idx >= 0:
                        widget.setCurrentIndex(idx)

            widget.blockSignals(False)

    def _resolve_path(self, theme: Theme, json_path: str):
        """Walk the dotted path on a Theme instance to retrieve the current value."""
        parts = json_path.split(".")
        target = theme
        for part in parts[:-1]:
            if hasattr(target, part) and isinstance(getattr(target, part), dict):
                target = getattr(target, part)
            elif isinstance(target, dict) and part in target:
                target = target[part]
            else:
                return None
        leaf = parts[-1]
        if isinstance(target, dict):
            return target.get(leaf)
        return None

    def clear(self):
        """Reset all property widgets to safe defaults (no theme loaded)."""
        for spec in THEME_EDITOR_SCHEMA:
            kind = spec.widget_kind
            widget = self._widgets.get(spec.json_path)
            if widget is None:
                continue
            if kind == "color":
                widget.setStyleSheet(
                    "QPushButton { background: #000000; border: 2px solid rgba(255,255,255,0.15); border-radius: 4px; }"
                )
                widget.setProperty("_color_value", "#000000")
            elif kind in ("float", "int"):
                widget.setValue(0)
            elif kind == "bool":
                widget.setChecked(False)
            elif kind == "font_family":
                widget.setCurrentFont(QFont("Segoe UI"))
            elif kind == "font_weight":
                widget.setCurrentIndex(0)
            elif kind == "image_path":
                widget.setText("")
            elif kind == "enum":
                widget.setCurrentIndex(0)
        self._theme_dir = None

    def _pick_color(self, json_path: str, btn: QPushButton):
        current = btn.property("_color_value") or "#000000"
        color = QColorDialog.getColor(QColor(current), self, "Pick Color")
        if color.isValid():
            btn.setStyleSheet(
                f"QPushButton {{ background: {color.name()}; border: 2px solid rgba(255,255,255,0.15); border-radius: 4px; }}"
            )
            btn.setProperty("_color_value", color.name())
            self.property_changed.emit(json_path, color.name())

    def _browse_image(self, line_edit: QLineEdit, json_path: str, extensions: list):
        ext_str = " ".join(extensions)
        filter_str = f"Images ({ext_str})"
        path, _ = QFileDialog.getOpenFileName(self, "Select Image", "", filter_str)
        if path:
            # Relativize against the theme directory for portability (Decision 6)
            import os
            display_path = path
            if self._theme_dir is not None:
                try:
                    rel = os.path.relpath(path, str(self._theme_dir))
                    if not rel.startswith(".."):
                        display_path = rel
                except ValueError:
                    pass  # different drives on Windows — keep absolute
            line_edit.setText(display_path)
            self.property_changed.emit(json_path, display_path)

    def _import_font(self, target_combo: QFontComboBox):
        """Import a .ttf/.otf font file into themes/fonts/, then refresh the combo.

        Steps: pick file → copy to themes/fonts/ → re-scan fonts → update combo.
        """
        from pathlib import Path as _Path
        path, _ = QFileDialog.getOpenFileName(
            self, "Import Font", "", "Font files (*.ttf *.otf)")
        if not path:
            return

        src = _Path(path)
        fonts_dir = _Path(__file__).resolve().parent.parent / "utils" / "themes" / "fonts"
        fonts_dir.mkdir(parents=True, exist_ok=True)

        import shutil
        dest = fonts_dir / src.name
        if dest.exists():
            QMessageBox.information(self, "Font Already Imported",
                f"'{src.name}' is already in themes/fonts/.")
            return

        try:
            shutil.copy2(str(src), str(dest))
        except Exception as e:
            QMessageBox.warning(self, "Import Failed",
                f"Could not copy font:\n{e}")
            return

        # Re-scan fonts so the combo sees the new font immediately
        self._theme_mgr._load_application_fonts()

        # Refresh the QFontComboBox
        target_combo.update()

    # _spin_style / _combo_style removed in Phase 4 — styling via global QSS [designer-spin] / [designer-combo] selectors


# ── Theme Designer Panel (top-level) ─────────────────────────────────────────

# ── Noise tile (deterministic seed, precomputed once) ────────────────────────
_SEED = 42
_NOISE_TILE: Optional["QPixmap"] = None


def _get_noise_tile(size: int = 128) -> "QPixmap":
    """Return a precomputed noise tile for soft_grain surface treatment."""
    global _NOISE_TILE
    if _NOISE_TILE is not None:
        return _NOISE_TILE
    rng = _random.Random(_SEED)
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    for y in range(size):
        for x in range(size):
            alpha = rng.randint(0, 12)
            if alpha > 0:
                painter.setPen(QColor(255, 255, 255, alpha))
                painter.drawPoint(x, y)
    painter.end()
    _NOISE_TILE = pix
    return _NOISE_TILE


# ── Color parsing helper ─────────────────────────────────────────────────────

def _parse_color_safe(value: str, fallback: Optional[QColor] = None) -> QColor:
    """Parse a color string safely.

    Handles hex, named colors, and CSS rgba()/rgb() strings. Falls back to the
    provided default color on parse failure — never crashes on malformed input.
    """
    c = QColor(value)
    if c.isValid():
        return c
    m = re.fullmatch(
        r"rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)"
        r"(?:\s*,\s*(\d*\.?\d+)\s*)?\)",
        value,
    )
    if m:
        r, g, b = (int(m.group(i)) for i in range(1, 4))
        alpha = m.group(4)
        if alpha is None:
            return QColor(r, g, b)
        a = int(round(float(alpha) * 255))
        return QColor(r, g, b, max(0, min(255, a)))
    logger.warning("[Theme] Failed to parse color '%s'; using fallback", value)
    return fallback if fallback is not None else QColor(0, 0, 0)


# ── Thumbnail paint dispatchers ──────────────────────────────────────────────

def _paint_thumb_background(painter, style, bg_primary, bg_secondary, W, H):
    """Dispatch background rendering by style.background_mode."""
    mode = style.get("background_mode", "diagonal")
    if mode == "diagonal":
        grad = QLinearGradient(0, 0, W, H)
        grad.setColorAt(0.0, bg_primary)
        grad.setColorAt(1.0, bg_secondary)
        painter.fillRect(0, 0, W, H, grad)
    elif mode == "radial":
        from PyQt6.QtGui import QRadialGradient
        cx, cy = W * 0.5, H * 0.35
        radius = max(W, H) * 0.8
        grad = QRadialGradient(cx, cy, radius)
        grad.setColorAt(0.0, bg_primary)
        grad.setColorAt(1.0, bg_secondary)
        painter.fillRect(0, 0, W, H, grad)
    elif mode == "vignette":
        from PyQt6.QtGui import QPainterPath
        painter.fillRect(0, 0, W, H, bg_secondary)
        path = QPainterPath()
        path.addRoundedRect(QRectF(W * 0.06, H * 0.04, W * 0.88, H * 0.92), 12, 12)
        brush = QColor(bg_primary)
        painter.fillPath(path, brush)
    elif mode == "flat":
        painter.fillRect(0, 0, W, H, bg_primary)
    elif mode == "split":
        split_y = int(H * 0.4)
        painter.fillRect(0, 0, W, split_y, bg_secondary)
        painter.fillRect(0, split_y, W, H - split_y, bg_primary)
    elif mode == "wash":
        from PyQt6.QtGui import QRadialGradient
        painter.fillRect(0, 0, W, H, bg_primary)
        glow = QColor(bg_secondary)
        glow.setAlphaF(0.30)
        cx, cy = W * 0.5, H * 0.3
        grad = QRadialGradient(cx, cy, max(W, H) * 0.7)
        grad.setColorAt(0.0, glow)
        grad.setColorAt(1.0, Qt.GlobalColor.transparent)
        painter.fillRect(0, 0, W, H, grad)


def _paint_thumb_surface(painter, style, W, H):
    """Dispatch surface overlay by style.surface."""
    surface = style.get("surface", "none")
    if surface == "none":
        return
    if surface == "soft_grain":
        tile = _get_noise_tile()
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Overlay)
        for y in range(0, H, tile.height()):
            for x in range(0, W, tile.width()):
                painter.drawPixmap(x, y, tile)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
    elif surface == "paper":
        for i, frac in enumerate([0.12, 0.38, 0.62, 0.85]):
            y = int(H * frac)
            alpha = 5 if i % 2 == 0 else 3
            painter.fillRect(0, y, W, 2, QColor(255, 255, 255, alpha))
    elif surface == "glass":
        grad = QLinearGradient(0, 0, W * 0.4, H * 0.4)
        grad.setColorAt(0.0, QColor(255, 255, 255, 38))
        grad.setColorAt(0.5, QColor(255, 255, 255, 0))
        painter.fillRect(0, 0, W, H, grad)
    elif surface == "broadcast_grid":
        step = 12
        for y in range(step, H, step):
            painter.setPen(QColor(255, 255, 255, 8))
            painter.drawLine(0, y, W, y)


def _paint_thumb_accent(painter, style, color, W, H, ref_bottom_y, band_y, layer):
    """Dispatch accent element by style.accent_layout and layer."""
    layout = style.get("accent_layout", "top_rule")
    margin = 24

    if layout == "top_rule" and layer == "under_text":
        y = ref_bottom_y + 2
        painter.fillRect(margin, y, W - margin * 2, 8, color)
    elif layout == "bottom_rule" and layer == "over_band":
        y = band_y - 8
        painter.fillRect(margin, y, W - margin * 2, 8, color)
    elif layout == "side_rail" and layer == "under_text":
        painter.fillRect(W - 24, 0, 4, H, color)
    elif layout == "corner_bracket" and layer == "under_text":
        arm = 12
        thick = 2
        # top-right
        painter.fillRect(W - margin - arm, margin, arm, thick, color)
        painter.fillRect(W - margin - thick, margin, thick, arm, color)
        # bottom-left
        painter.fillRect(margin, H - 28 - arm, arm, thick, color)
        painter.fillRect(margin, H - 28 - arm, thick, arm, color)
    elif layout == "double_rule" and layer == "under_text":
        y1 = ref_bottom_y + 2
        y2 = ref_bottom_y + 8
        rcolor = QColor(color)
        rcolor.setAlphaF(0.6)
        painter.fillRect(margin, y1, W - margin * 2, 2, rcolor)
        painter.fillRect(margin, y2, W - margin * 2, 2, rcolor)


class ThemeDesignerPanel(QWidget):
    """Top-level three-column layout: ThemesList | Preview | PropertyEditor."""

    back_requested = pyqtSignal()

    def __init__(self, theme_mgr: ThemeManager, channel_manager=None, parent=None):
        super().__init__(parent)
        self._theme_mgr = theme_mgr
        self._channel_manager = channel_manager
        self._active_theme: Optional[Theme] = None  # deep-copied editing instance
        self._original_id: Optional[str] = None      # id at open time, for save target
        self._dirty: bool = False
        self._setup_ui()

        # Auto-select the current or first available theme on open.
        # Deferred via QTimer.singleShot(0) so _on_theme_selected runs
        # after the widget tree is realized and the first layout pass
        # has settled — prevents stale verse labels from a render on
        # an unrealized (zero-geometry) widget.
        QTimer.singleShot(0, self._auto_select_initial_theme)

    def _auto_select_initial_theme(self):
        """Select current or first theme after the widget tree is realized."""
        target = self._theme_mgr.current
        if target is None:
            available = self._theme_mgr.available_themes()
            if available:
                target = available[0]
        if target is not None:
            self._themes_list._select_card(target.id)
            self._on_theme_selected(target.id)

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── Header row (50px) ────────────────────────────────────────────────
        header = QFrame()
        header.setFixedHeight(50)
        header.setProperty("designer-header", True)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 8, 16, 8)
        header_layout.setSpacing(12)

        # Palette icon (Phase 2)
        palette_icon_label = QLabel()
        palette_icon_label.setPixmap(get_palette_icon(size=16).pixmap(16, 16))
        palette_icon_label.setFixedSize(16, 16)
        header_layout.addWidget(palette_icon_label)

        title = QLabel("Theme Designer")
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        title.setProperty("designer-title", True)
        header_layout.addWidget(title)

        header_layout.addStretch()

        self._save_btn = QPushButton("Save")
        self._save_btn.setFixedHeight(32)
        self._save_btn.setProperty("designer-action-btn", True)
        self._save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._save_btn.setEnabled(False)
        self._save_btn.clicked.connect(self._on_save)
        header_layout.addWidget(self._save_btn)

        self._save_as_btn = QPushButton("Save As")
        self._save_as_btn.setFixedHeight(32)
        self._save_as_btn.setProperty("designer-action-btn", True)
        self._save_as_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._save_as_btn.setEnabled(False)
        self._save_as_btn.clicked.connect(self._on_save_as)
        header_layout.addWidget(self._save_as_btn)

        self._delete_btn = QPushButton("Delete")
        self._delete_btn.setFixedHeight(32)
        self._delete_btn.setProperty("designer-action-btn", True)
        self._delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._delete_btn.setEnabled(False)
        self._delete_btn.clicked.connect(self._on_delete)
        header_layout.addWidget(self._delete_btn)

        self._back_btn = QPushButton("Back to Settings")
        self._back_btn.setFixedHeight(32)
        self._back_btn.setProperty("accent", "gold")
        self._back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._back_btn.clicked.connect(self._on_back_requested)
        header_layout.addWidget(self._back_btn)

        main_layout.addWidget(header)

        # ── Three-column layout ──────────────────────────────────────────────
        columns = QHBoxLayout()
        columns.setSpacing(8)
        columns.setContentsMargins(8, 8, 8, 8)

        self._themes_list = ThemesListPanel(self._theme_mgr)
        columns.addWidget(self._themes_list)

        self._preview = PreviewSurface(self._theme_mgr)
        columns.addWidget(self._preview, 1)

        self._property_editor = PropertyEditor(self._theme_mgr)
        columns.addWidget(self._property_editor)

        main_layout.addLayout(columns, 1)

        # ── Signal wiring ────────────────────────────────────────────────────
        self._themes_list.theme_selected.connect(self._on_theme_selected)
        self._themes_list.new_requested.connect(self._on_new)
        self._themes_list.duplicate_requested.connect(self._on_duplicate)
        self._themes_list.delete_requested.connect(self._on_delete_by_id)
        self._property_editor.property_changed.connect(self._on_property_changed)
        self._preview.apply_requested.connect(self._on_apply)

    # ── Theme selection ──────────────────────────────────────────────────────

    def _on_theme_selected(self, theme_id: str):
        if not self._confirm_discard_changes():
            self._themes_list.reselect(self._original_id)
            return

        registry_theme = self._theme_mgr.get_theme(theme_id)
        if registry_theme is None:
            logger.warning("[ThemeDesigner] Unknown theme_id '%s'", theme_id)
            return

        self._active_theme = registry_theme.deep_copy()
        self._original_id = theme_id
        self._dirty = False

        self._property_editor.load_theme(self._active_theme)
        self._preview.set_theme(self._active_theme)

        self._update_header_buttons()

    def _update_header_buttons(self):
        has_active = self._active_theme is not None
        if not has_active:
            self._save_btn.setEnabled(False)
            self._save_as_btn.setEnabled(False)
            self._delete_btn.setEnabled(False)
            return

        is_builtin = self._active_theme.id in BUILTIN_THEME_IDS
        self._save_btn.setEnabled(not is_builtin)
        self._save_as_btn.setEnabled(True)
        self._delete_btn.setEnabled(not is_builtin)

    # ── Property editing ─────────────────────────────────────────────────────

    def _on_property_changed(self, json_path: str, value):
        if self._active_theme is None:
            return
        self._active_theme.update(json_path, value)
        self._dirty = True
        self._preview.refresh()

    # ── Thumbnail generation ────────────────────────────────────────────────

    THUMB_W = 600
    THUMB_H = 192

    def _fit_thumb_font_size(self, text, font_family, font_weight, verse_width, max_height):
        """Binary search for largest verse font that fits the thumbnail clip area.

        Mirrors DisplayWidget._calc_single_font_size logic — measures via
        QTextDocument with the same wrap model used during thumbnail painting.
        """
        min_font, max_font = 8, 80
        best = min_font
        max_iters = math.ceil(math.log2(max_font - min_font + 1)) + 1
        for _ in range(max_iters):
            if min_font > max_font:
                break
            mid = (min_font + max_font) // 2
            font = QFont(font_family, mid, font_weight)
            doc = QTextDocument()
            doc.setDefaultFont(font)
            opt = doc.defaultTextOption()
            opt.setWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
            doc.setDefaultTextOption(opt)
            doc.setPlainText(text)
            doc.setTextWidth(verse_width)
            if doc.size().height() <= max_height:
                best = mid
                min_font = mid + 1
            else:
                max_font = mid - 1
        return best

    def _generate_theme_thumbnail(self, theme_id: str):
        """Generate a purpose-built thumbnail PNG using QPainter.

        Paints directly at 2x card resolution (600x192) from theme property
        values — no widget grab, no scaling, no screen resolution dependency.
        Renders: gradient background, gold reference header with separator,
        verse text (word-wrapped, centered), lower-third band accent strip.
        """
        theme = self._theme_mgr.get_theme(theme_id)
        if not theme or not theme.source_path:
            return

        c = theme.c
        fs = theme.fullscreen

        bg_primary = _parse_color_safe(c("bg_primary"), QColor("#0f0f1a"))
        bg_secondary = _parse_color_safe(c("bg_secondary"), QColor("#0a0a14"))
        gold_fallback = _parse_color_safe(c("gold"), QColor("#c8a03c"))
        text_fallback = _parse_color_safe(c("text_primary"), QColor("#e8e2d8"))
        ref_color = _parse_color_safe(fs.get("ref_color", c("gold")), gold_fallback)
        verse_color = _parse_color_safe(fs.get("verse_color", c("text_primary")), text_fallback)
        faint_color = _parse_color_safe(c("text_faint"), QColor(232, 226, 216, 46))

        ref_family = fs.get("ref_font_family", theme.fonts.get("family", "Segoe UI"))
        ref_weight = WEIGHT_MAP.get(fs.get("ref_font_weight", "Black"), 900)
        verse_family = fs.get("verse_font_family", theme.fonts.get("family", "Segoe UI"))
        verse_weight = WEIGHT_MAP.get(fs.get("verse_font_weight", "Normal"), 400)

        ref_text = SAMPLE_VERSES[1]["reference"].upper()  # Psalm 23:1
        verse_text = SAMPLE_VERSES[1]["text"]  # "The LORD is my shepherd; I shall not want."

        W, H = self.THUMB_W, self.THUMB_H
        pixmap = QPixmap(W, H)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        # ── Background + surface ──────────────────────────────────────────
        style = theme.thumbnail_style
        _paint_thumb_background(painter, style, bg_primary, bg_secondary, W, H)
        _paint_thumb_surface(painter, style, W, H)

        # ── Reference text (14pt bold, gold, uppercase with letter-spacing) ──
        ref_font = QFont(ref_family, 14)
        ref_font.setWeight(ref_weight)
        painter.setFont(ref_font)
        painter.setPen(ref_color)

        ref_extra_spacing = 6
        x_ref = 24
        y_ref = 36
        for ch in ref_text:
            painter.drawText(x_ref, y_ref, ch)
            x_ref += painter.fontMetrics().horizontalAdvance(ch) + ref_extra_spacing

        ref_bottom_y = 46

        # ── Accent — under text ──────────────────────────────────────────────
        band_y = H - 28
        _paint_thumb_accent(painter, style, ref_color, W, H,
                           ref_bottom_y, band_y, layer="under_text")

        # ── Verse text (font fitted to fill available space) ─────────────────
        verse_top = ref_bottom_y + 8 + 8  # 62
        verse_left = 24
        verse_right = W - 24
        verse_width = verse_right - verse_left
        verse_max_h = H - verse_top - 52

        verse_size = self._fit_thumb_font_size(
            verse_text, verse_family, verse_weight, verse_width, verse_max_h)
        verse_font = QFont(verse_family, verse_size)
        verse_font.setWeight(verse_weight)

        doc = QTextDocument()
        doc.setDefaultFont(verse_font)
        opt = doc.defaultTextOption()
        opt.setWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
        opt.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        doc.setDefaultTextOption(opt)
        doc.setPlainText(verse_text)
        doc.setTextWidth(verse_width)
        cursor = QTextCursor(doc)
        cursor.select(QTextCursor.SelectionType.Document)
        char_format = QTextCharFormat()
        char_format.setForeground(verse_color)
        cursor.setCharFormat(char_format)

        painter.setFont(verse_font)
        painter.setPen(verse_color)
        painter.translate(verse_left, verse_top)
        doc.drawContents(painter, QRectF(0, 0, verse_width, verse_max_h))
        painter.translate(-verse_left, -verse_top)

        # ── Lower-third band preview (bottom accent strip) ───────────────────
        lt = theme.lower_third
        band_color = _parse_color_safe(
            lt.get("background_color", c("bg_primary")),
            _parse_color_safe(c("bg_primary"), QColor("#0f0f1a")),
        )
        band_opacity = float(lt.get("background_alpha", 0.85))
        band_h = 28
        band_color.setAlphaF(band_opacity)
        painter.fillRect(0, H - band_h, W, band_h, band_color)

        # ── Accent — over band ───────────────────────────────────────────────
        _paint_thumb_accent(painter, style, ref_color, W, H,
                           ref_bottom_y, band_y, layer="over_band")

        # ── Footer line (10pt, text_faint) ───────────────────────────────────
        faint_font = QFont("Segoe UI", 10)
        painter.setFont(faint_font)
        painter.setPen(faint_color)
        painter.drawText(24, H - 8, "KJV")

        painter.end()

        thumb_path = theme.source_path.with_suffix(".thumb.png")
        pixmap.save(str(thumb_path), "PNG")

    def showEvent(self, event):
        super().showEvent(event)

        missing_ids = []
        for theme in self._theme_mgr.available_themes():
            if theme.source_path:
                thumb_path = theme.source_path.with_suffix(".thumb.png")
                if not thumb_path.exists():
                    missing_ids.append(theme.id)
                elif thumb_path.stat().st_size < 8192:
                    thumb_path.unlink(missing_ok=True)
                    missing_ids.append(theme.id)

        if missing_ids:
            from PyQt6.QtCore import QTimer
            current_id = self._original_id
            for idx, tid in enumerate(missing_ids):
                QTimer.singleShot(100 * (idx + 1), lambda t=tid, orig_id=current_id: self._generate_thumbnail_spaced(t, orig_id))

    def _generate_thumbnail_spaced(self, theme_id: str, original_id: str = None):
        """Spaced generation callback. Generates thumbnail and refreshes grid selection."""
        self._generate_theme_thumbnail(theme_id)
        self._themes_list.refresh_list()
        target_id = original_id or self._original_id
        if target_id:
            self._themes_list.reselect(target_id)

    # ── Save / Save As ──────────────────────────────────────────────────────

    def _on_save(self):
        if self._active_theme is None:
            return

        # Live-service guard
        if self._any_channel_live():
            if not self._confirm_override_live():
                return

        success = self._active_theme.save()
        if success:
            self._theme_mgr.reload_theme(self._original_id)
            self._generate_theme_thumbnail(self._original_id)
            self._themes_list.refresh_list()
            self._themes_list.reselect(self._original_id)
            self._dirty = False
            self.statusBar_msg(f"Theme '{self._active_theme.name}' saved.")
        else:
            QMessageBox.warning(self, "Save Failed",
                                f"Could not save theme '{self._active_theme.name}'.\n\n"
                                "Built-in themes cannot be overwritten. Use Save As instead.")

    def _on_save_as(self):
        if self._active_theme is None:
            return

        new_id, ok = QInputDialog.getText(self, "Save As — New Theme",
                                          "Theme ID:",
                                          text=f"{self._original_id}_copy")
        if not ok or not new_id.strip():
            return
        new_id = new_id.strip()

        new_name, ok = QInputDialog.getText(self, "Save As — Theme Name",
                                             "Display name:",
                                             text=f"{self._active_theme.name} (Copy)")
        if not ok or not new_name.strip():
            return
        new_name = new_name.strip()

        new_theme = self._theme_mgr.create_theme(new_id, new_name, source=self._active_theme)
        if new_theme is not None:
            self._generate_theme_thumbnail(new_theme.id)
            self._themes_list.refresh_list()
            self._on_theme_selected(new_theme.id)
            self.statusBar_msg(f"Theme '{new_name}' created as '{new_theme.id}'.")
        else:
            QMessageBox.warning(self, "Save As Failed",
                                "Could not create theme.\n\n"
                                "The ID may already exist or contain invalid characters.")

    # ── Delete ───────────────────────────────────────────────────────────────

    def _on_delete(self):
        if self._active_theme is None:
            return
        if not self._confirm_discard_changes():
            return
        self._confirm_delete_theme(self._active_theme.id)

    def _on_delete_by_id(self, theme_id: str):
        if theme_id in BUILTIN_THEME_IDS:
            return
        self._confirm_delete_theme(theme_id)

    def _confirm_delete_theme(self, theme_id: str):
        theme = self._theme_mgr.get_theme(theme_id)
        if theme is None:
            return

        reply = QMessageBox.question(
            self, "Delete Theme",
            f"Delete theme '{theme.name}' ({theme_id})?\n\nThis cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        success = theme.delete()
        if success:
            self._theme_mgr.reload_theme(theme_id)  # drops stale entry (file missing)
            self._themes_list.refresh_list()
            # Clear active theme if it was the one deleted
            if self._active_theme and self._active_theme.id == theme_id:
                self._active_theme = None
                self._original_id = None
                self._dirty = False
                self._update_header_buttons()
                self._property_editor.clear()
                self._preview.clear_theme()
            self.statusBar_msg(f"Theme '{theme.name}' deleted.")
        else:
            QMessageBox.warning(self, "Delete Failed",
                                f"Could not delete theme '{theme.name}'.")

    # ── New ──────────────────────────────────────────────────────────────────

    def _on_new(self):
        if not self._confirm_discard_changes():
            return
        new_id, ok = QInputDialog.getText(self, "New Theme",
                                          "Theme ID:")
        if not ok or not new_id.strip():
            return
        new_id = new_id.strip()

        new_name, ok = QInputDialog.getText(self, "New Theme",
                                             "Display name:")
        if not ok or not new_name.strip():
            return
        new_name = new_name.strip()

        # Duplicate from dark_gold as the base
        base = self._theme_mgr.get_theme("dark_gold")
        if base is None:
            QMessageBox.warning(self, "New Theme Failed", "Cannot find base theme 'dark_gold'.")
            return

        new_theme = self._theme_mgr.create_theme(new_id, new_name, source=base)
        if new_theme is not None:
            self._generate_theme_thumbnail(new_theme.id)
            self._themes_list.refresh_list()
            self._on_theme_selected(new_theme.id)
            self.statusBar_msg(f"Theme '{new_name}' created.")
        else:
            QMessageBox.warning(self, "New Theme Failed",
                                "Could not create theme.\n\n"
                                "The ID may already exist or contain invalid characters.")

    # ── Duplicate ────────────────────────────────────────────────────────────

    def _on_duplicate(self, source_id: str):
        if not self._confirm_discard_changes():
            return
        source = self._theme_mgr.get_theme(source_id)
        if source is None:
            return

        new_id = f"{source_id}_copy"
        new_name = f"{source.name} (Copy)"

        new_theme = self._theme_mgr.create_theme(new_id, new_name, source=source)
        if new_theme is not None:
            self._generate_theme_thumbnail(new_theme.id)
            self._themes_list.refresh_list()
            self._on_theme_selected(new_theme.id)
            self.statusBar_msg(f"Theme '{new_name}' duplicated from '{source.name}'.")
        else:
            QMessageBox.warning(self, "Duplicate Failed",
                                f"Could not duplicate theme. ID '{new_id}' may already exist.")

    # ── Apply ────────────────────────────────────────────────────────────────

    def _on_apply(self, target: str):
        if self._active_theme is None:
            return

        # Live-service guard
        if self._any_channel_live():
            if not self._confirm_override_live():
                return

        # Ensure theme is saved before applying
        if self._dirty:
            reply = QMessageBox.question(
                self, "Unsaved Theme",
                "You have unsaved changes. Apply will use the current edited state,\n"
                "but changes will not persist until you Save.\n\n"
                "Continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        channels = self._resolve_channels(target)
        for ch in channels:
            if ch is not None:
                ch.set_theme(self._active_theme.deep_copy())

        self.statusBar_msg(f"Theme '{self._active_theme.name}' applied to {target}.")

    def _resolve_channels(self, target: str):
        if self._channel_manager is None:
            return []
        if target == "both":
            return [
                self._channel_manager.get_channel("main"),
                self._channel_manager.get_channel("alt"),
            ]
        return [self._channel_manager.get_channel(target)]

    # ── Back navigation ──────────────────────────────────────────────────────

    def _on_back_requested(self):
        if not self._confirm_discard_changes():
            return
        self._dirty = False
        self.back_requested.emit()

    # ── Unsaved-changes guard (E5) ───────────────────────────────────────────

    def _confirm_discard_changes(self) -> bool:
        """Prompt the operator when there are unsaved edits.

        Returns True if it is safe to proceed (user confirmed discard or no
        dirty state). Returns False if the user chose to cancel.
        """
        if not self._dirty:
            return True
        reply = QMessageBox.question(
            self, "Unsaved Changes",
            f"'{self._active_theme.name}' has unsaved changes.\n\n"
            "Discard changes and continue?",
            QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        return reply == QMessageBox.StandardButton.Discard

    # ── Live-channel guard ───────────────────────────────────────────────────

    def _any_channel_live(self) -> bool:
        if self._channel_manager is None:
            return False
        for name in self._channel_manager.channel_names():
            ch = self._channel_manager.get_channel(name)
            if ch is not None and ch.is_live:
                return True
        return False

    def _confirm_override_live(self) -> bool:
        """Show 'Override Live' dialog. Returns True on confirm."""
        reply = QMessageBox.warning(
            self, "Override Live Service",
            "A channel is currently live (verse on display).\n\n"
            "Saving or applying a theme during a live service may cause a "
            "visible flicker on the congregation display.\n\n"
            "Continue anyway?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return reply == QMessageBox.StandardButton.Yes

    # ── Status bar helper ────────────────────────────────────────────────────

    def statusBar_msg(self, msg: str):
        """Show a temporary message in the main window's status bar."""
        main_win = self.window()
        if hasattr(main_win, 'statusBar') and callable(main_win.statusBar):
            main_win.statusBar().showMessage(msg, 4000)
