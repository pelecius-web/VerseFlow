"""home_panel.py - VerseFlow main operator panel & all widgets it alone uses.

Contains:
    ModeToggle:              Verse Lookup | Keyword Search selector
    SearchLineEdit:          QLineEdit that auto-selects on focus
    HomePanel:               top-level operator UI (left sidebar + right content)
    DisplayPreview:          reads DisplayController state, renders compact preview
    VerseLiveHistoryPanel:   scrollable log of every verse sent to display
    HistoryEntryCard:        single clickable row inside VerseLiveHistoryPanel

Extracted from main.py in v0.7.11 modularization.
Audited v0.7.12
"""

import logging
import re
from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QEvent, QSize

logger = logging.getLogger("VerseFlow")
from PyQt6.QtGui import QFont, QFontMetrics, QIcon, QKeySequence, QShortcut
from PyQt6.QtGui import QTextDocument, QTextOption
from PyQt6.QtWidgets import (
    QApplication, QWidget, QFrame, QVBoxLayout, QHBoxLayout,
    QStackedWidget, QLabel, QLineEdit, QPushButton, QScrollArea,
    QMessageBox, QFileDialog, QTabWidget,
)

import icons
from constants import resolve_book, BOOK_ABBREV_MAP
from document_manager import DocumentManager
from queue_panel import QueuePanel
from playlist_panel import PlaylistPanel
from navigator import VerseNavigator, KeywordResults
from editors import DraftEditor, TranslationMenu
from db_layer import abbreviate_translation


# ── ModeToggle ───────────────────────────────────────────────────────────────

class ModeToggle(QFrame):
    """Verse Lookup | Keyword Search toggle."""
    mode_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_mode = "Verse Lookup"
        self.setFixedHeight(34)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.btn_verse = QPushButton("Verse Lookup")
        self.btn_keyword = QPushButton("Keyword Search")
        for btn in (self.btn_verse, self.btn_keyword):
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFont(QFont("Segoe UI", 10))
            btn.setFixedHeight(34)

        self.btn_verse.clicked.connect(lambda: self._set_mode("Verse Lookup"))
        self.btn_keyword.clicked.connect(lambda: self._set_mode("Keyword Search"))

        layout.addWidget(self.btn_verse)
        layout.addWidget(self.btn_keyword)

        self._refresh_style()

    def _set_mode(self, mode):
        self.current_mode = mode
        self._refresh_style()
        self.mode_changed.emit(mode)

    def _refresh_style(self):
        for btn, name in [(self.btn_verse, "Verse Lookup"), (self.btn_keyword, "Keyword Search")]:
            active = name == self.current_mode
            if btn == self.btn_verse:
                btn.setProperty("mode-toggle", "left" if active else "left-inactive")
            else:
                btn.setProperty("mode-toggle", "right" if active else "right-inactive")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

# ── Home Panel (search + preview + Phase 1 components) ───────────────────────

class SearchLineEdit(QLineEdit):
    """QLineEdit that selects all text on focus for instant overwrite."""
    def focusInEvent(self, event):
        super().focusInEvent(event)
        QTimer.singleShot(0, self.selectAll)


class HomePanel(QWidget):
    """Main operator panel with left sidebar and right content area.
    
    Layout:
    ┌──────────────┬─────────────────────────────┐
    │              │   Display Preview           │
    │  Left Panel  ┌─────────────────────────────┤
    │              │                             │
    │  - Search    │   Verse Navigator           │
    │  - Settings  │   (main content area)       │
    │  - Controls  │                             │
    │              ┌─────────────────────────────┤
    │              │   Cross-References          │
    └──────────────┴─────────────────────────────┘
    """
    stack_nav_requested = pyqtSignal(int)  # Request MainWindow to change stack page

    def __init__(self, db, display, parent=None, channel_manager=None, ndi_manager=None, theme_mgr=None):
        super().__init__(parent)
        self.db = db
        self.display = display
        # v1.1.0 Phase 1: ChannelManager stored for future channel-aware UI.
        # Existing code continues to use self.display directly.
        self.channel_manager = channel_manager
        self.ndi_manager = ndi_manager
        self.theme_mgr = theme_mgr
        self._last_push_source = None  # Track where the live verse came from
        self._last_push_verse = None   # Track the exact verse data last pushed
        self._section_header_icon_labels = []  # For future theme-switch retint

        # ── Category 1: Document Manager (single source of truth) ─────────────
        self.doc_manager = DocumentManager(self)
        self.doc_manager.document_changed.connect(self._on_document_changed)

        # Sync toggle tracker with display changes to prevent desync
        display.verse_changed.connect(self._sync_push_tracker)

        # Main horizontal layout
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # ═══════════════════════════════════════════════════════════
        # LEFT SIDEBAR (280px fixed width)
        # ═══════════════════════════════════════════════════════════
        left_sidebar = QFrame()
        left_sidebar.setProperty("sidebar", True)
        left_sidebar.setFixedWidth(280)
        left_layout = QVBoxLayout(left_sidebar)
        left_layout.setContentsMargins(12, 12, 12, 12)
        left_layout.setSpacing(12)
        
        # Navigation tabs (Home / Settings) — lives inside sidebar so it doesn't push other columns down
        tab_row = QHBoxLayout()
        tab_row.setSpacing(8)

        self.btn_tab_home = QPushButton("Home")
        self.btn_tab_home.setFixedHeight(32)
        self.btn_tab_home.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.btn_tab_home.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_tab_home.setProperty("accent", "nav-tab-active")
        self.btn_tab_home.clicked.connect(lambda: self.stack_nav_requested.emit(0))
        tab_row.addWidget(self.btn_tab_home)

        self.btn_tab_settings = QPushButton("Settings")
        self.btn_tab_settings.setFixedHeight(32)
        self.btn_tab_settings.setFont(QFont("Segoe UI", 10))
        self.btn_tab_settings.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_tab_settings.setProperty("accent", "nav-tab")
        self.btn_tab_settings.clicked.connect(lambda: self.stack_nav_requested.emit(1))
        tab_row.addWidget(self.btn_tab_settings)

        tab_row.addStretch()
        left_layout.addLayout(tab_row)
        
        # Version badge
        version = QLabel("v1.3.0")
        version.setProperty("version-badge", True)
        left_layout.addWidget(version)
        
        # Separator
        left_layout.addWidget(self._make_separator())
        
        # Draft editor (moved to left sidebar to occupy empty space)
        left_layout.addWidget(self._make_section_header("Draft Editor", variant="compact-green"))
        
        self.draft_editor = DraftEditor()
        self.draft_editor.draft_changed.connect(display.set_draft)
        self.draft_editor.publish_requested.connect(display.publish_draft)
        left_layout.addWidget(self.draft_editor)
        
        left_layout.addStretch()
        
        main_layout.addWidget(left_sidebar)
        
        # ═══════════════════════════════════════════════════════════
        # CENTER SPACE (320px fixed width)
        # ═══════════════════════════════════════════════════════════
        center_space = QFrame()
        center_space.setProperty("panel", True)
        center_space.setFixedWidth(320)
        center_layout = QVBoxLayout(center_space)
        center_layout.setContentsMargins(12, 12, 12, 12)
        center_layout.setSpacing(12)
        
        # Translation menu (dropdown with checkboxes)
        self.trans_menu = TranslationMenu(db, parent=self)
        self.trans_menu.translation_changed.connect(self._on_translation_changed)
        center_layout.addWidget(self.trans_menu)
        
        # Search input
        self.search_input = SearchLineEdit()
        self.search_input.setPlaceholderText('e.g. "John 3:16"…')
        self.search_input.setFont(QFont("Segoe UI", 13))
        self.search_input.setMinimumHeight(40)
        self.search_input.returnPressed.connect(self._do_search)
        self.search_input.installEventFilter(self)
        center_layout.addWidget(self.search_input)
        
        # Mode toggle (compact)
        self.mode_toggle = ModeToggle()
        self.mode_toggle.mode_changed.connect(self._on_mode_changed)
        center_layout.addWidget(self.mode_toggle)
        
        # Separator
        center_layout.addWidget(self._make_separator())

        # Verse Navigation Buttons (Up/Down)
        center_layout.addWidget(self._make_section_header("Verse Navigation", variant="compact"))

        nav_buttons_widget = QWidget()
        nav_buttons_layout = QHBoxLayout(nav_buttons_widget)
        nav_buttons_layout.setContentsMargins(0, 0, 0, 0)
        nav_buttons_layout.setSpacing(8)

        # Up button
        self.nav_up_btn = QPushButton()
        self.nav_up_btn.setIcon(icons.get_arrow_up_icon(size=20))
        self.nav_up_btn.setIconSize(QSize(20, 20))
        self.nav_up_btn.setText("Up")
        self.nav_up_btn.setFixedHeight(36)
        self.nav_up_btn.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.nav_up_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.nav_up_btn.setProperty("accent", "gold")
        self.nav_up_btn.clicked.connect(self._navigate_verse_up)
        nav_buttons_layout.addWidget(self.nav_up_btn)

        # Down button
        self.nav_down_btn = QPushButton()
        self.nav_down_btn.setIcon(icons.get_arrow_down_icon(size=20))
        self.nav_down_btn.setIconSize(QSize(20, 20))
        self.nav_down_btn.setText("Down")
        self.nav_down_btn.setFixedHeight(36)
        self.nav_down_btn.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.nav_down_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.nav_down_btn.setProperty("accent", "gold")
        self.nav_down_btn.clicked.connect(self._navigate_verse_down)
        nav_buttons_layout.addWidget(self.nav_down_btn)

        center_layout.addWidget(nav_buttons_widget)

        # Separator
        center_layout.addWidget(self._make_separator())

        # Display Controls: Show / Hide buttons
        center_layout.addWidget(self._make_section_header("Display Controls", variant="compact"))

        display_controls = QHBoxLayout()
        display_controls.setSpacing(8)

        self.btn_show = QPushButton()
        self.btn_show.setIcon(icons.get_play_icon(size=24))
        self.btn_show.setIconSize(QSize(24, 24))
        self.btn_show.setText("Show")
        self.btn_show.setFixedHeight(40)
        self.btn_show.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.btn_show.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_show.setProperty("accent", "green")
        self.btn_show.clicked.connect(self._on_show)
        display_controls.addWidget(self.btn_show)

        self.btn_hide = QPushButton()
        self.btn_hide.setIcon(icons.get_stop_icon(size=24))
        self.btn_hide.setIconSize(QSize(24, 24))
        self.btn_hide.setText("Hide")
        self.btn_hide.setFixedHeight(40)
        self.btn_hide.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.btn_hide.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_hide.setProperty("accent", "destructive")
        self.btn_hide.clicked.connect(self._on_hide)
        display_controls.addWidget(self.btn_hide)

        center_layout.addLayout(display_controls)

        # ── Phase 4: Dual Output ──────────────────────────────────────────────────
        # Alt verse_changed is emitted via ChannelManager.channel_changed but
        # is NOT wired to queue/playlist sync. This is intentional scope control:
        # queue/playlist only track Main's live state. Cross-channel sync is Phase 5+.

        center_layout.addWidget(self._make_separator())

        # OUTPUT TARGET segmented buttons: Main | Alt | All
        target_label = QLabel("Output Target")
        target_label.setFont(QFont("Segoe UI", 9))
        target_label.setProperty("hint", True)
        center_layout.addWidget(target_label)

        target_row = QHBoxLayout()
        target_row.setSpacing(4)

        self._output_target = "main"
        self._target_btns = {}
        from PyQt6.QtWidgets import QButtonGroup
        self._target_group = QButtonGroup(self)
        for name, label in [("main", "Main"), ("alt", "Alt"), ("all", "All")]:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setFixedHeight(28)
            btn.setProperty("accent", "output-target")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self._target_group.addButton(btn)
            self._target_btns[name] = btn
            target_row.addWidget(btn)
        self._target_btns["main"].setChecked(True)
        center_layout.addLayout(target_row)
        for name, btn in self._target_btns.items():
            btn.clicked.connect(lambda _checked, n=name: self._on_target_changed(n))

        # DISPLAY MODE dropdowns
        mode_label = QLabel("Display Mode")
        mode_label.setFont(QFont("Segoe UI", 9))
        mode_label.setProperty("hint", True)
        center_layout.addWidget(mode_label)

        mode_row = QHBoxLayout()
        mode_row.setSpacing(6)

        mode_items = ["Fullscreen", "Lower Third"]
        mode_values = ["fullscreen", "lower_third"]

        main_mode_label = QLabel("Main:")
        main_mode_label.setFont(QFont("Segoe UI", 8))
        main_mode_label.setProperty("hint", True)
        mode_row.addWidget(main_mode_label)

        from PyQt6.QtWidgets import QComboBox
        self.combo_main_mode = QComboBox()
        self.combo_main_mode.addItems(mode_items)
        self.combo_main_mode.setFixedHeight(26)
        self.combo_main_mode.setFont(QFont("Segoe UI", 9))
        self.combo_main_mode.setProperty("combo-mode", True)
        mode_row.addWidget(self.combo_main_mode, 1)

        alt_mode_label = QLabel("Alt:")
        alt_mode_label.setFont(QFont("Segoe UI", 8))
        alt_mode_label.setProperty("hint", True)
        mode_row.addWidget(alt_mode_label)

        self.combo_alt_mode = QComboBox()
        self.combo_alt_mode.addItems(mode_items)
        self.combo_alt_mode.setCurrentIndex(1)  # Lower Third default
        self.combo_alt_mode.setFixedHeight(26)
        self.combo_alt_mode.setFont(QFont("Segoe UI", 9))
        self.combo_alt_mode.setProperty("combo-mode", True)
        mode_row.addWidget(self.combo_alt_mode, 1)

        center_layout.addLayout(mode_row)

        # Phase 4: Wire mode dropdowns and channel status updates
        mode_values = ["fullscreen", "lower_third"]
        self.combo_main_mode.currentIndexChanged.connect(
            lambda idx: self.channel_manager.set_channel_mode("main", mode_values[idx]) if 0 <= idx < len(mode_values) else None
        )
        self.combo_alt_mode.currentIndexChanged.connect(
            lambda idx: self.channel_manager.set_channel_mode("alt", mode_values[idx]) if 0 <= idx < len(mode_values) else None
        )
        if self.channel_manager:
            self.channel_manager.channel_changed.connect(self._update_channel_status)

        # Playlist Panel (Integrated Stage 4)
        self.playlist_panel = PlaylistPanel(self.doc_manager, self.display, self)
        center_layout.addWidget(self.playlist_panel, 1)

        main_layout.addWidget(center_space)
        
        # ═══════════════════════════════════════════════════════════
        # RIGHT CONTENT AREA (expanding, main workspace)
        # ═══════════════════════════════════════════════════════════
        right_content = QWidget()
        right_layout = QVBoxLayout(right_content)
        right_layout.setContentsMargins(12, 12, 12, 12)
        right_layout.setSpacing(12)
        
        # TOP: Tabbed Preview (300px) — Phase 5 dual-channel preview

        preview_box = QFrame()
        preview_box.setProperty("panel", True)
        preview_box.setFixedHeight(300)
        preview_box_layout = QVBoxLayout(preview_box)
        preview_box_layout.setContentsMargins(0, 0, 0, 0)
        preview_box_layout.setSpacing(0)

        self.preview_tabs = QTabWidget()
        self.preview_tabs.setFixedHeight(280)
        self.preview_tabs.setProperty("preview-tabs", True)

        alt_controller = self.channel_manager.get_channel("alt").controller
        self.preview_main = DisplayPreview(self.display)
        self.preview_alt = DisplayPreview(alt_controller)
        self.preview_tabs.addTab(self.preview_main, "Main Preview")
        self.preview_tabs.addTab(self.preview_alt, "Alt Preview")

        preview_box_layout.addWidget(self.preview_tabs)

        self.lbl_preview_status = QLabel("MAIN — CLEAR — Fullscreen    ALT — CLEAR — Lower Third")
        self.lbl_preview_status.setFont(QFont("Segoe UI", 8))
        self.lbl_preview_status.setProperty("hint", True)
        self.lbl_preview_status.setContentsMargins(12, 2, 12, 2)
        self.lbl_preview_status.setFixedHeight(20)
        preview_box_layout.addWidget(self.lbl_preview_status)

        right_layout.addWidget(preview_box)

        # BOTTOM: Stacked panel for navigator / keyword results
        self.result_stack = QStackedWidget()
        right_layout.addWidget(self.result_stack, 2)  # Proportionally takes 2/3 of space

        # Panel 0: Verse Navigator
        navigator_box = QFrame()
        navigator_box.setProperty("panel", True)
        navigator_layout = QVBoxLayout(navigator_box)
        navigator_layout.setContentsMargins(12, 10, 12, 10)
        navigator_layout.setSpacing(6)

        navigator_layout.addWidget(self._make_section_header("Verse Navigator", variant="compact"))

        self.navigator = VerseNavigator(
            db, display,
            push_callback=self._route_push,
            clear_callback=self._route_clear,
        )
        self.navigator.verse_pushed.connect(lambda v: self._push_verse(v, source="navigator"))
        self.navigator.state_changed.connect(self._on_navigator_state_changed)
        navigator_layout.addWidget(self.navigator)

        self.result_stack.addWidget(navigator_box)  # index 0

        # Panel 1: Keyword Results
        keyword_box = QFrame()
        keyword_box.setProperty("panel", True)
        keyword_layout = QVBoxLayout(keyword_box)
        keyword_layout.setContentsMargins(12, 10, 12, 10)
        keyword_layout.setSpacing(6)

        keyword_layout.addWidget(self._make_section_header("Keyword Results", variant="compact-green"))

        self.keyword_results = KeywordResults(db, display)
        self.keyword_results.verse_pushed.connect(lambda v: self._push_verse(v, source="search"))
        keyword_layout.addWidget(self.keyword_results)

        self.result_stack.addWidget(keyword_box)  # index 1

        # BOTTOM: Queue & History Sub Panels (NEW location)
        bottom_sub_panels = QHBoxLayout()
        bottom_sub_panels.setSpacing(12)
        bottom_sub_panels.setContentsMargins(0, 0, 0, 0)

        # 1) Queue Panel (Integrated)
        self.queue_panel = QueuePanel(self.doc_manager, display)
        bottom_sub_panels.addWidget(self.queue_panel, 1)

        # Wire queue_requested signals from navigator and keyword results
        self.navigator.queue_requested.connect(self.queue_panel.add_verse)
        self.keyword_results.queue_requested.connect(self.queue_panel.add_verse)
        
        self.navigator.playlist_requested.connect(self.playlist_panel.add_verse)
        self.keyword_results.playlist_requested.connect(self.playlist_panel.add_verse)

        # Wire preview_requested to load the verse chapter context and show preview
        self.queue_panel.preview_requested.connect(self._preview_queued_verse)
        
        # Wire queue push button to correctly load into the VerseNavigator and go live
        self.queue_panel.verse_pushed.connect(lambda v: self._push_verse(v, source="queue"))

        # Wire move to playlist (Stage 4 Fix)
        self.queue_panel.move_to_playlist_requested.connect(self.playlist_panel.add_verse)

        # Route channel updates through channel_manager instead of display directly
        self.channel_manager.channel_changed.connect(self._on_any_channel_changed)

        # Wire playlist_panel signals (ensure queue_panel exists first)
        self.playlist_panel.add_to_queue_requested.connect(self.queue_panel.add_verse)
        self.playlist_panel.preview_requested.connect(self._preview_queued_verse)
        self.playlist_panel.verse_pushed.connect(self._on_playlist_verse_pushed)
        self.playlist_panel.verse_cleared.connect(self._on_playlist_verse_cleared)
        self.playlist_panel.open_requested.connect(self._on_playlist_open)
        self.playlist_panel.save_as_requested.connect(self._on_playlist_save_as)

        # 2) Verse Live History Panel
        hist_container = QFrame()
        hist_container.setProperty("panel", True)
        hist_layout = QVBoxLayout(hist_container)
        hist_layout.setContentsMargins(6, 4, 6, 4)
        hist_layout.setSpacing(2)

        hist_mini_header = QHBoxLayout()
        hist_mini_header.setSpacing(4)
        dot_hist = QFrame()
        dot_hist.setFixedSize(6, 6)
        dot_hist.setProperty("gold-dot", True)
        hist_mini_header.addWidget(dot_hist)
        hist_mini_label = QLabel("LIVE HISTORY")
        hist_mini_label.setProperty("section-header", "compact")
        hist_mini_header.addWidget(hist_mini_label)
        hist_mini_header.addStretch()

        # Clear History button (Premium SVG Trash Can)
        self.btn_clear_history = QPushButton()
        self.btn_clear_history.setIcon(icons.get_trash_icon())
        self.btn_clear_history.setIconSize(QSize(16, 16))
        self.btn_clear_history.setFixedSize(24, 24)
        self.btn_clear_history.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_clear_history.setToolTip("Clear Live History")
        self.btn_clear_history.setProperty("accent", "destructive")
        self.btn_clear_history.clicked.connect(self._clear_history)
        hist_mini_header.addWidget(self.btn_clear_history)

        hist_layout.addLayout(hist_mini_header)

        self.verse_live_history = VerseLiveHistoryPanel(self.display)
        hist_layout.addWidget(self.verse_live_history)
        
        # Connect strictly to State 1 -> 2 transitions for history logging to prevent clutter
        self.navigator.verse_went_live.connect(self.verse_live_history.add_verse)

        # Connect history click to restore (replaces parent.parent() traversal)
        self.verse_live_history.verse_clicked.connect(self._restore_from_history)
        
        bottom_sub_panels.addWidget(hist_container, 1)

        bottom_container = QWidget()
        bottom_container.setLayout(bottom_sub_panels)
        
        # Flexibly ratio the space: Navigator gets 2/3 stretch, Bottom gets 1/3 stretch
        right_layout.addWidget(bottom_container, 1)

        main_layout.addWidget(right_content, 1)

        # Populate translations
        self._populate_translations("English KJV")

        # Current translation tracker
        self.current_translation = "English KJV"

        # Flag to prevent eventFilter from intercepting Enter during search processing
        self._processing_search = False

        # Debounced search-as-you-type timer for keyword search mode
        self.search_timer = QTimer()
        self.search_timer.setSingleShot(True)
        self.search_timer.setInterval(250)  # ms delay after typing stops
        self.search_timer.timeout.connect(self._do_search)

        # Connect text changes to timer
        self.search_input.textChanged.connect(self._on_search_text_changed)

        # Install global event filter for keyboard focus on navigator
        # This ensures arrow keys and Enter always work on navigator when active (state > 0)
        QApplication.instance().installEventFilter(self)

        # ── Ctrl+L: Focus search input (operator live-service standard) ──────────
        search_focus_sc = QShortcut(QKeySequence("Ctrl+L"), self)
        search_focus_sc.activated.connect(self._focus_search)
    
    def _make_section_header(self, title: str, variant: str = "compact", icon: QIcon = None) -> QWidget:
        """Gold dot + typography-sized label + optional icon, wrapped in QWidget.

        NOTE: No setFont() call on the label — the typography QSS selector
        provides all font properties (size, weight, family, letter-spacing,
        text-transform). SettingsPanel._make_section_header includes a
        redundant setFont() from the pre-typography-system era. (F7)
        """
        container = QWidget()
        header = QHBoxLayout(container)
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(8)
        if icon is not None:
            icon_label = QLabel()
            icon_label.setPixmap(icon.pixmap(16, 16))
            icon_label.setFixedSize(16, 16)
            header.addWidget(icon_label)
            self._section_header_icon_labels.append((icon_label, title))
        dot = QFrame()
        dot.setFixedSize(6, 6)
        if variant == "compact-green":
            dot.setProperty("gold-dot-green", True)
        else:
            dot.setProperty("gold-dot", True)
        header.addWidget(dot)
        label = QLabel(title.upper())
        label.setProperty("section-header", variant)
        header.addWidget(label)
        header.addStretch()
        return container

    def _make_separator(self) -> QFrame:
        """1px gold-dim separator line using property selector."""
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setProperty("separator", True)
        sep.setFixedHeight(1)
        return sep

    def _refresh_section_header_icons(self):
        """Rebuild section header icons using the current theme's gold color.

        Call this when the active theme changes to retint icons.
        Currently NOT wired to any signal — provided for Phase 4+ integration.
        Currently a no-op because home_panel section headers have no icons yet;
        icons will be added when Phase 4 wires theme-switch retinting.
        """
        theme = self.theme_mgr.current if self.theme_mgr else None
        gold = theme.c("gold") if theme else "#c8a03c"
        for icon_label, title in self._section_header_icon_labels:
            # Future: map title to icon factory, regenerate with gold color
            pass

    def _focus_search(self):
        """Ctrl+L: Focus the search input for rapid verse lookup.
        Clears the navigator if active and re-enables the input."""
        nav = getattr(self, 'navigator', None)
        if nav and nav._state > 0:
            nav.clear()
        self.search_input.setEnabled(True)
        self.search_input.setFocus()
        self.search_input.selectAll()

    # Note: stack_nav_requested signal kept for backward compatibility
    # Tab navigation moved to MainWindow
    
    def _populate_translations(self, default_trans=""):
        """Populate translation selector."""
        # This is now handled by TranslationSelector
        pass

    def _navigate_verse_up(self):
        """Navigate to previous verse and update screen if in State 2 (displaying)."""
        if not self.navigator.verses or self.navigator.highlighted_idx <= 0:
            return
        
        # Move highlight up
        new_idx = self.navigator.highlighted_idx - 1
        self.navigator._move_highlight(new_idx)
        
        # If in State 2 (displaying), update screen
        if self.navigator._state == 2:
            verse = self.navigator.verses[new_idx]
            self._route_push(verse)

    def _navigate_verse_down(self):
        """Navigate to next verse and update screen if in State 2 (displaying)."""
        if not self.navigator.verses or self.navigator.highlighted_idx >= len(self.navigator.verses) - 1:
            return
        
        # Move highlight down
        new_idx = self.navigator.highlighted_idx + 1
        self.navigator._move_highlight(new_idx)
        
        # If in State 2 (displaying), update screen
        if self.navigator._state == 2:
            verse = self.navigator.verses[new_idx]
            self._route_push(verse)

    def _route_push(self, verse: dict):
        """Push verse to the current output target."""
        t = self._output_target
        if t == "main":
            self.channel_manager.push_to_channel("main", verse)
        elif t == "alt":
            self.channel_manager.push_to_channel("alt", verse)
        elif t == "all":
            self.channel_manager.push_to_all(verse)
        else:
            logger.error("_route_push: unknown target '%s', falling back to main", t)
            self.channel_manager.push_to_channel("main", verse)

    def _route_clear(self):
        """Clear the current output target."""
        t = self._output_target
        if t == "main":
            self.channel_manager.clear_channel("main")
        elif t == "alt":
            self.channel_manager.clear_channel("alt")
        elif t == "all":
            self.channel_manager.clear_all()
        else:
            logger.error("_route_clear: unknown target '%s', falling back to main", t)
            self.channel_manager.clear_channel("main")

    def _on_target_changed(self, new_target: str):
        if new_target == self._output_target:
            return
        previous = self._output_target
        self._output_target = new_target
        self.channel_manager.switch_target(new_target, previous)
        # Refresh navigator state to match new target's current verse
        primary_ch = "main" if new_target in ("main", "all") else "alt"
        ch = self.channel_manager.get_channel(primary_ch)
        if ch:
            self._sync_navigator_state(ch.current)

    def _on_any_channel_changed(self, channel_name: str, state: dict):
        """Route channel updates to UI panels based on current target."""
        primary = "main" if self._output_target in ("main", "all") else "alt"
        if channel_name != primary:
            return
        verse = state.get("current") or {}
        self.queue_panel.sync_live_state(verse)
        self.playlist_panel.sync_live_state(verse)
        self._sync_navigator_state(verse)
    
    def _on_translation_changed(self, action):
        """Handle translation change.

        Action formats:
        - "default:KJV" → Set KJV as default checked translation
        - "override:KJV" → Replace everything with KJV (text click)
        - "overlay:NIV" → Add NIV as overlay (checkbox checked)
        - "remove:NIV" → Remove NIV overlay (checkbox unchecked)
        """
        if not action:
            return

        parts = action.split(":", 1)
        if len(parts) != 2:
            return

        action_type, translation = parts

        if action_type == "default":
            # Set new default — reload navigator with this translation
            self.current_translation = translation
            self.trans_menu.current_primary = translation
            if self.navigator.verses:
                self.navigator.reload_translation(translation)
            # Update display to show same verse reference in the new translation
            if self.display.current:
                current_ref = self.display.current.get("reference", "")
                if current_ref:
                    ref_match = re.match(r'(.+?)\s+(\d+):(\d+)', current_ref)
                    if ref_match:
                        book_name = ref_match.group(1).strip()
                        chapter = int(ref_match.group(2))
                        verse_num = int(ref_match.group(3))
                        book = resolve_book(book_name)
                        if book:
                            verse_data = self.db.get_verse(
                                f"{book} {chapter}:{verse_num}", translation
                            )
                            if verse_data:
                                self.display.push_verse(verse_data)

        elif action_type == "override":
            # Override mode: replace everything
            self.current_translation = translation
            self.trans_menu.current_primary = translation

            # Get current displayed verse reference
            current_ref = self.display.current.get("reference", "") if self.display.current else ""

            # Reload navigator with new translation (preserves state/highlight)
            if self.navigator.verses:
                self.navigator.reload_translation(translation)

            # Update the actual verse on screen to new translation
            if current_ref:
                # Parse reference to get book/chapter/verse
                ref_match = re.match(r'(.+?)\s+(\d+):(\d+)', current_ref)
                if ref_match:
                    book_name = ref_match.group(1).strip()
                    chapter = int(ref_match.group(2))
                    verse_num = int(ref_match.group(3))

                    # Resolve book name
                    book = resolve_book(book_name)
                    if book:
                        verse_data = self.db.get_verse(f"{book} {chapter}:{verse_num}", translation)
                        if verse_data:
                            # Push new verse - this updates display.current AND emits signal
                            self.display.push_verse(verse_data)
                            # Clear overlays since we're overriding
                            self.display.clear_translations()

        elif action_type == "overlay":
            # Overlay mode: add translation above current
            # Build ALL overlays from scratch based on checked_translations order
            self._rebuild_display_overlays()

        elif action_type == "remove":
            # Remove overlay: rebuild remaining overlays
            self._rebuild_display_overlays()

    def _rebuild_display_overlays(self):
        """Rebuild all display overlays based on checked_translations order.

        checked_translations = [AMP, ESV, MSG] (in order of checking)
        current_primary = MSG (last checked = n)
        Display order (top to bottom): MSG, ESV, AMP
        """
        if not self.navigator.verses or self.navigator.highlighted_idx < 0:
            return

        checked = self.trans_menu.checked_translations[:]
        current_primary = self.trans_menu.current_primary

        # Step 0: Reload navigator with current primary
        self.navigator.reload_translation(current_primary)

        # Step 1: Look up verse in current primary
        verse = self.navigator.verses[self.navigator.highlighted_idx]
        if not verse:
            return

        primary_verse = self.db.get_verse(
            f"{verse['book']} {verse['chapter']}:{verse['verse']}", current_primary
        )
        if not primary_verse:
            return

        # Step 2: Push primary first — ensures display.current is updated
        # BEFORE overlay ops trigger translations_changed → _sync_navigator_state.
        # Prevents State 2 → State 1 reset from translation mismatch.
        # (Stale overlays from push_verse's internal auto-resolution are
        # immediately replaced by clear + rebuild below.)
        self.display.push_verse(primary_verse)

        # Step 3: Clear stale overlays and rebuild with correct set
        self.display.clear_translations()

        others = [t for t in checked if t != current_primary]
        others.reverse()

        for trans_name in others:
            overlay_verse = self.db.get_verse(
                f"{verse['book']} {verse['chapter']}:{verse['verse']}", trans_name
            )
            if overlay_verse:
                self.display.add_translation(overlay_verse)
    
    def _on_search_text_changed(self, text):
        """Restart the debounce timer on every keystroke in keyword search mode only.
        In verse lookup mode, we wait for Enter press to avoid false matches on partial input."""
        if self.mode_toggle.current_mode == "Keyword Search":
            self.search_timer.start()
        # In Verse Lookup mode, do NOT auto-search — wait for Enter

    def _on_mode_changed(self, mode):
        """Handle mode change (Verse Lookup | Keyword Search)."""
        if mode == "Verse Lookup":
            self.search_input.setPlaceholderText('e.g. "John 3:16"…')
            self.result_stack.setCurrentIndex(0)  # Show navigator
            # Don't auto-search in verse lookup — wait for Enter
        else:
            self.search_input.setPlaceholderText('e.g. "faith", "love", "light of the world"…')
            self.result_stack.setCurrentIndex(1)  # Show keyword results
            # Auto-search in keyword mode if there's text
            text = self.search_input.text().strip()
            if text:
                self._do_search()

    def _on_document_changed(self):
        """Placeholder for future reactions to document-level changes."""
        pass

    def _sync_push_tracker(self, verse):
        """Keep toggle memory in sync with display state (especially for Undo/Clear)."""
        if not verse:
            self._last_push_verse = None
            self._last_push_source = None

    def _sync_navigator_state(self, verse):
        """Reset navigator to State 1 when an external source (playlist/queue) takes over display.

        Also handles channel clears: when verse is empty/None, resets navigator
        to State 1 so the state badge reflects the cleared display.
        """
        if not verse:
            nav = getattr(self, 'navigator', None)
            if nav and nav._state == 2:
                nav._state = 1
                nav._refresh_hl_style(nav.highlighted_idx)
                nav._update_state_badge()
                nav._update_hint()
                nav.state_changed.emit(nav._state)
            return

        nav = getattr(self, 'navigator', None)
        if not nav or nav._state != 2:
            return

        # Check if the current display verse matches navigator's highlighted verse
        nav_verse = None
        if nav.highlighted_idx >= 0 and nav.highlighted_idx < len(nav.verses):
            nav_verse = nav.verses[nav.highlighted_idx]

        if not nav_verse:
            nav._state = 1
            nav._refresh_hl_style(nav.highlighted_idx)
            nav._update_state_badge()
            nav._update_hint()
            nav.state_changed.emit(nav._state)
            return

        # Compare by entry_id first, then reference + translation
        verse_id = verse.get("entry_id", "")
        nav_id = nav_verse.get("entry_id", "")
        verse_ref = verse.get("reference", "")
        nav_ref = nav_verse.get("reference", "")
        verse_trans = verse.get("translation", "")
        nav_trans = nav_verse.get("translation", "")

        is_same = (verse_id and nav_id and verse_id == nav_id) or \
                  (verse_ref == nav_ref and verse_trans == nav_trans)

        if not is_same:
            # External source took over - reset navigator to READY state
            nav._state = 1
            nav._refresh_hl_style(nav.highlighted_idx)
            nav._update_state_badge()
            nav._update_hint()
            nav.state_changed.emit(nav._state)

    def _on_navigator_state_changed(self, state):
        """Handle navigator state changes.
        Defer setEnabled calls to avoid Qt focus re-dispatch bug during
        synchronous state changes (e.g., load_chapter → state_changed.emit)."""
        if state == 0:
            QTimer.singleShot(0, lambda: (self.search_input.setEnabled(True), self.search_input.setFocus()))
        else:
            QTimer.singleShot(0, lambda: self.search_input.setEnabled(False))

    def _on_show(self):
        """Send the currently highlighted verse to external screen (same as Enter)."""
        nav = getattr(self, 'navigator', None)
        if nav and nav.highlighted_idx >= 0 and nav.highlighted_idx < len(nav.verses):
            verse = nav.verses[nav.highlighted_idx]
            if nav._state == 1:
                nav._on_card_pushed(verse)
            elif nav._state == 2:
                self._route_push(verse)
        else:
            logger.debug("No highlighted verse to display")

    def _on_hide(self):
        """Clear external screen and return navigator to State 1."""
        self._last_push_source = None
        self._last_push_verse = None
        self._route_clear()

    # ── Phase 4: Dual-output channel methods ─────────────────────────────────────

    def _on_playlist_verse_pushed(self, verse: dict):
        """Handle playlist verse push — routes via current target."""
        self._route_push(verse)

    def _on_playlist_verse_cleared(self):
        """Handle playlist verse clear — routes via current target."""
        self._route_clear()

    # ── Phase 4: Dual-output channel methods ─────────────────────────────────────

    def _update_channel_status(self, channel_name: str, state: dict):
        """Update tab indicators (●/○) and preview status row.

        Called by channel_manager.channel_changed on every push/clear/mode change.
        """
        if state is None:
            return

        # Update tab indicator — state dict already contains is_live from get_state()
        tab_index = 0 if channel_name == "main" else 1
        is_live = state.get("is_live", False)
        indicator = "●" if is_live else "○"
        name = "Main Preview" if channel_name == "main" else "Alt Preview"
        self.preview_tabs.setTabText(tab_index, f"{name} {indicator}")

        # Update single status row below preview tabs
        self._update_preview_status_row()

    def _update_preview_status_row(self):
        """Render the compact status info row below the preview tabs."""
        main_state = self.channel_manager.get_channel("main").get_state()
        alt_state = self.channel_manager.get_channel("alt").get_state()

        def _fmt(state, label):
            live = state.get("is_live")
            mode = state.get("display_mode", "fullscreen").replace("_", " ").title()
            if live:
                current = state.get("current") or {}
                ref = current.get("reference", "")
                trans = abbreviate_translation(current.get("translation", ""))
                if trans:
                    return f"{label} — LIVE — {mode} — {ref} {trans}"
                return f"{label} — LIVE — {mode} — {ref}"
            return f"{label} — CLEAR — {mode}"

        def _ndi(ch_name):
            if self.ndi_manager is None:
                return ""
            sender = self.ndi_manager.get_sender(ch_name)
            if sender is None:
                return ""
            if not sender.is_enabled():
                return " ○"
            return " ●" if sender.is_active() else " ○"

        self.lbl_preview_status.setText(
            f"{_fmt(main_state, 'MAIN')}{_ndi('main')}    {_fmt(alt_state, 'ALT')}{_ndi('alt')}"
        )

    def _add_highlighted_to_queue(self):
        """Add the highlighted navigator verse to the queue if available."""
        nav = getattr(self, 'navigator', None)
        queue_panel = getattr(self, 'queue_panel', None)
        if not nav or not queue_panel:
            return False
        if nav.highlighted_idx < 0 or nav.highlighted_idx >= len(nav.verses):
            return False

        verse = nav.verses[nav.highlighted_idx]
        if not verse:
            return False

        queue_panel.add_verse(verse)
        return True

    def _clear_history(self):
        """Clear verse live history panel."""
        if self.verse_live_history:
            self.verse_live_history.clear()

    def _restore_from_history(self, verse):
        """Restore a verse from history to the display."""
        if not verse or "reference" not in verse:
            return
            
        ref = verse["reference"]
        trans = verse.get("translation", self.trans_menu.current_primary)
        
        # Note: we temporarily detach the history logic to prevent duplicate logging
        # when we push this to screen 
        
        # 1. Update translation if different
        if self.current_translation != trans:
            self._on_translation_changed(f"override:{trans}")
            
        # 2. Parse reference to retrieve exact book/chapter
        ref_match = re.match(r'(.+?)\s+(\d+):(\d+)', ref)
        if ref_match:
            book_name = ref_match.group(1).strip()
            chapter = int(ref_match.group(2))
            verse_num = int(ref_match.group(3))
            
            book = resolve_book(book_name)
            if book:
                # 3. Disconnect briefly to avoid logging the history payload back onto itself
                self.navigator.verse_went_live.disconnect(self.verse_live_history.add_verse)
                
                # 4. Load chapter and push exact verse
                result = self.db.lookup_verse(f"{book} {chapter}:1", trans)
                if result and result.get("verses"):
                    self.navigator.load_chapter(book, chapter, result["verses"], target_verse=verse_num)
                    for i, v in enumerate(self.navigator.verses):
                        if v.get("verse") == verse_num or str(v.get("verse")) == str(verse_num):
                            self.navigator._move_highlight(i)
                            self.navigator._on_card_pushed(v)
                            break
                        
                # 5. Reconnect history logger
                self.navigator.verse_went_live.connect(self.verse_live_history.add_verse)

    def _do_search(self):
        """Execute search based on current mode."""
        import time
        self._processing_search = True  # Block eventFilter Enter interception
        _deferred_reset = False  # True only when a QTimer handles the flag reset
        try:
            q = self.search_input.text().strip()
            if not q:
                self.navigator.clear()
                self.keyword_results.set_verses([])
                return

            t0 = time.perf_counter()
            if self.mode_toggle.current_mode == "Verse Lookup":
                # Verse lookup → load chapter
                result = self.db.lookup_verse(q, self.current_translation)
                if result and result.get("verses"):
                    self.navigator.load_chapter(
                        result["book"], result["chapter"], result["verses"],
                        target_verse=result.get("target_verse", 0)
                    )
                    self.result_stack.setCurrentIndex(0)
                    elapsed = (time.perf_counter() - t0) * 1000
                    logger.info("Loaded %s %d — %d verses in %.1fms", result['book'], result['chapter'], len(result['verses']), elapsed)
                    # NOTE: Do NOT call search_input.setEnabled(False) synchronously here —
                    # it triggers Qt's focus re-dispatch bug, causing the current Enter keypress
                    # to be re-delivered to the navigator and push to State 2.
                    # _on_navigator_state_changed already handles disabling via deferred QTimer.
                    # Clear flag after focus moves to navigator (Enter event fully processed)
                    _deferred_reset = True  # QTimer below owns the _processing_search reset
                    QTimer.singleShot(250, lambda: setattr(self, '_processing_search', False))
                    QTimer.singleShot(200, lambda: self.navigator.setFocus())
                else:
                    # Fall back to keyword
                    result = self.db.search(q, self.current_translation)
                    if isinstance(result, dict):
                        self.keyword_results.set_verses(result["verses"], total=result["total"], capped=result["capped"], query=q)
                    else:
                        self.keyword_results.set_verses(result)
                    self.result_stack.setCurrentIndex(1)
                    elapsed = (time.perf_counter() - t0) * 1000
                    n = len(result["verses"]) if isinstance(result, dict) else len(result)
                    logger.info("%d keyword results in %.1fms", n, elapsed)
                    self.search_input.setEnabled(True)
            else:
                # Keyword search mode
                result = self.db.search(q, self.current_translation)
                if isinstance(result, dict):
                    self.keyword_results.set_verses(result["verses"], total=result["total"], capped=result["capped"], query=q)
                else:
                    self.keyword_results.set_verses(result)
                self.result_stack.setCurrentIndex(1)
                elapsed = (time.perf_counter() - t0) * 1000
                n = len(result["verses"]) if isinstance(result, dict) else len(result)
                logger.info("%d keyword results in %.1fms", n, elapsed)
                self.search_input.setEnabled(True)
        except Exception as e:
            logger.error("CRASH in _do_search: %s", e, exc_info=True)
        finally:
            if not _deferred_reset:
                self._processing_search = False

    def _preview_queued_verse(self, verse):
        """Preview a verse from the queue panel safely in State 1 without going live.
        Loads the chapter context in the navigator."""
        # DEFENSIVE: Validate verse is a dict to prevent crashes from malformed data
        if not isinstance(verse, dict):
            logger.warning("_preview_queued_verse received non-dict type: %s", type(verse).__name__)
            return
        if not verse:
            return
            
        # 1. Provide rapid feedback in the Preview Panel immediately (Main tab)
        self.preview_main.set_preview_verse(verse)
        self.preview_tabs.setCurrentIndex(0)  # Switch to Main tab
        
        # 2. Look up the full chapter in the background and load into the Navigator (State 1)
        book = verse.get("book", "")
        chapter = verse.get("chapter", 0)
        target_verse = verse.get("verse", 0)
        translation = verse.get("translation", self.current_translation)

        verses = self.db.lookup_verse(f"{book} {chapter}:1", translation)
        if verses and verses.get("verses"):
            self.navigator.load_chapter(
                book, chapter, verses["verses"],
                target_verse=target_verse
            )
            self.result_stack.setCurrentIndex(0)
            self.search_input.setEnabled(False)

    def _push_verse(self, verse, source=None):
        """Push verse to display. 
        Toggles OFF if the same item is pushed from the SAME source.
        """
        # DEFENSIVE: Validate verse is a dict to prevent crashes from malformed data
        if not isinstance(verse, dict):
            logger.warning("_push_verse received non-dict type: %s", type(verse).__name__)
            return
        if not verse:
            return

        # Handle source-locked toggle (HARDENED: Compare intent, not just display state)
        if source == self._last_push_source and self._last_push_verse:
            # Check for match (ID or Reference+Translation)
            match = False
            last_v = self._last_push_verse
            if verse.get("id") and last_v.get("id"):
                match = (verse["id"] == last_v["id"])
            else:
                match = (verse.get("reference") == last_v.get("reference") and 
                         verse.get("translation") == last_v.get("translation"))
            
            if match:
                # Toggle OFF requested
                self._on_hide()
                return

        # PUSH ON or SOURCE SWITCH
        self._last_push_source = source
        self._last_push_verse = verse
        # Load the full chapter in the navigator
        book = verse.get("book", "")
        chapter = verse.get("chapter", 0)
        target_verse = verse.get("verse", 0)
        translation = verse.get("translation", "")

        # Look up all verses in this chapter
        verses = self.db.lookup_verse(f"{book} {chapter}:1", translation)
        if verses and verses.get("verses"):
            self.navigator.load_chapter(
                book, chapter, verses["verses"],
                target_verse=target_verse
            )
            self.result_stack.setCurrentIndex(0)  # Switch to navigator view
            self.search_input.setEnabled(False)
            
            # Find and push the exact target verse to trigger State 2
            for v in self.navigator.verses:
                if v.get("verse") == target_verse or str(v.get("verse")) == str(target_verse):
                    self.navigator._on_card_pushed(v)
                    break

    def _maybe_save_changes(self) -> bool:
        """Prompt to save if there are unsaved changes. Returns True if safe to proceed, False to cancel."""
        from PyQt6.QtWidgets import QMessageBox, QFileDialog
        from pathlib import Path
        doc = self.doc_manager

        if not doc.is_dirty:
            return True

        reply = QMessageBox.question(
            self,
            "Unsaved Changes",
            f'"{doc.display_name()}" has unsaved changes.\n\nSave before continuing?',
            QMessageBox.StandardButton.Save |
            QMessageBox.StandardButton.Discard |
            QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Save,
        )

        if reply == QMessageBox.StandardButton.Save:
            if doc.current_file:
                ok, msg = doc.save()
                if not ok:
                    detail = f"\n\nDetail: {msg}" if msg else ""
                    QMessageBox.critical(self, "Save Failed", f"Failed to save playlist.{detail}")
                return ok
            else:
                path, _ = QFileDialog.getSaveFileName(
                    self, "Save Playlist", "", "VerseFlow Playlists (*.verseplaylist)"
                )
                if path:
                    ok, msg = doc.save_as(Path(path))
                    if not ok:
                        detail = f"\n\nDetail: {msg}" if msg else ""
                        QMessageBox.critical(self, "Save Failed", f"Failed to save playlist to:\n{path}{detail}")
                    return ok
                else:
                    return False
        elif reply == QMessageBox.StandardButton.Cancel:
            return False

        return True  # Discard changes

    def _on_playlist_open(self):
        """Open a .verseplaylist file."""
        if not self._maybe_save_changes():
            return
            
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Playlist", "", "VerseFlow Playlists (*.verseplaylist)"
        )
        if path:
            ok, msg = self.doc_manager.open_file(Path(path))
            if not ok:
                detail = f"\n\nDetail: {msg}" if msg else ""
                QMessageBox.critical(
                    self, "Open Failed",
                    f"Failed to open playlist:\n{path}{detail}"
                )

    def _on_playlist_save_as(self):
        """Save current playlist to a new file."""
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Playlist As", "", "VerseFlow Playlists (*.verseplaylist)"
        )
        if path:
            ok, msg = self.doc_manager.save_as(Path(path))
            if not ok:
                detail = f"\n\nDetail: {msg}" if msg else ""
                QMessageBox.critical(
                    self, "Save Failed",
                    f"Failed to save playlist to:\n{path}{detail}"
                )
    
    def eventFilter(self, obj, event):
        """Global event filter: keeps keyboard focus on navigator when active.
        Also handles Escape and mouse clicks on search input.
        """
        # Safely check for navigator attribute
        navigator = getattr(self, 'navigator', None)
        if navigator is None:
            return super().eventFilter(obj, event)
            
        et = event.type()

        # When navigator is active (state > 0), intercept arrow keys and Enter globally
        # This ensures they always work on navigator regardless of where focus is
        # SKIP if we're currently processing a search (avoid immediate State 2 jump)
        if navigator._state > 0 and not self._processing_search:
            if et == QEvent.Type.KeyPress:
                key = event.key()
                if key in (Qt.Key.Key_Up, Qt.Key.Key_Down, Qt.Key.Key_Return, Qt.Key.Key_Enter):
                    if event.isAutoRepeat():
                        return True  # Swallow held-key auto-repeat
                    navigator.keyPressEvent(event)
                    return True  # Event handled

        # Search input specific handling
        if obj == self.search_input:
            if et == QEvent.Type.KeyPress:
                if event.key() == Qt.Key.Key_Escape:
                    if navigator._state > 0:
                        navigator.clear()
                    self.search_input.clear()
                    self.search_input.setEnabled(True)
                    self.search_input.setFocus()
                    return True
            elif et == QEvent.Type.MouseButtonPress:
                if not self.search_input.isEnabled():
                    navigator.clear()
                    self.search_input.setEnabled(True)
                    self.search_input.setFocus()
                    QTimer.singleShot(0, self.search_input.selectAll)
                    return True
        return super().eventFilter(obj, event)


class DisplayPreview(QFrame):
    """Shows what's currently on the congregation display.
    Compact design optimized for 250px height.
    Supports multi-translation overlay preview.
    """
    def __init__(self, display, parent=None):
        super().__init__(parent)
        self.display = display
        self.setProperty("preview", True)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Reference label (will include translation badge inline)
        self.ref_label = QLabel("Ready")
        self.ref_label.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        self.ref_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.ref_label.setStyleSheet("color: rgba(200,160,60,0.5); background: transparent; letter-spacing: 2px;")
        layout.addWidget(self.ref_label, 0)

        # Main verse text area (scrollable for multi-translation)
        self.verse_scroll = QScrollArea()
        self.verse_scroll.setWidgetResizable(True)
        self.verse_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.verse_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.verse_content = QWidget()
        self.verse_layout = QVBoxLayout(self.verse_content)
        self.verse_layout.setContentsMargins(0, 0, 0, 0)
        self.verse_layout.setSpacing(8)

        self.verse_scroll.setWidget(self.verse_content)
        layout.addWidget(self.verse_scroll, 1)  # Takes remaining space

        # Font fitting attributes (auto-shrink to fit viewport)
        self._fitting = False
        self._current_base_font = 16
        self._min_font = 8
        self._max_font = 24
        self._last_content_hash = None

        # Connect to display controller
        display.verse_changed.connect(self._on_verse_changed)
        display.translations_changed.connect(self._on_translations_changed)

    def _on_translations_changed(self, translations):
        """Update display when secondary translations change."""
        if self.display.current:
            self._update_verse_display()

    def _on_verse_changed(self, verse):
        if not verse:
            self.ref_label.setText("Ready")
            self.ref_label.setStyleSheet("color: rgba(200,160,60,0.5); background: transparent; letter-spacing: 2px;")
            self._clear_verse_display()
            return

        # Update reference
        ref = verse.get("reference", "")
        # Check overlays directly from display controller — not secondary_translations which may lag
        has_overlays = len(self.display.secondary_translations) > 0

        if has_overlays:
            # Overlay mode — reference only, no version
            display_ref = ref
        else:
            # Single translation — include version name
            trans = abbreviate_translation(verse.get("translation", ""))
            display_ref = f"{ref} — {trans}" if trans else ref
        self.ref_label.setText(display_ref)
        self.ref_label.setStyleSheet("color: #c8a03c; background: transparent; letter-spacing: 2px;")
        self._update_verse_display()

    def _update_verse_display(self):
        """Update verse display with current and secondary translations,
        then dynamically scale font to fit the viewport."""
        if self._fitting:
            return
        if not self.display.current:
            self._clear_verse_display()
            return
        
        self._fitting = True
        try:
            self._current_base_font = self._find_fitting_font_size()
            self._render_current(base_font=self._current_base_font)
        finally:
            self._fitting = False

    def _find_fitting_font_size(self):
        """Binary search for the largest font size that fits all content in the viewport."""
        logger.debug("[FONT_FIT] START")
        viewport = self.verse_scroll.viewport()
        if not viewport:
            logger.debug("[FONT_FIT] no viewport, returning 14")
            return 14

        # Derive available space from actual layout with fallbacks
        content_margins = self.verse_content.layout().contentsMargins() if self.verse_content.layout() else None
        if content_margins:
            horizontal_margin = content_margins.left() + content_margins.right()
            vertical_margin = content_margins.top() + content_margins.bottom()
        else:
            horizontal_margin = 0
            vertical_margin = 0

        SCROLLBAR_BUFFER = 10  # Conservative scrollbar width estimate
        SAFETY_MARGIN = 10     # Minimal padding for visual comfort

        available_width = viewport.width() - horizontal_margin - SCROLLBAR_BUFFER
        available_height = viewport.height() - vertical_margin - SAFETY_MARGIN

        if available_width <= 0 or available_height <= 30:
            logger.debug("[FONT_FIT] small viewport w=%d h=%d, returning 10", available_width, available_height)
            return 10

        primary = self.display.current
        if not primary:
            logger.debug("[FONT_FIT] no current verse, returning 14")
            return 14

        texts = [primary.get("text", "")]
        translations = [primary.get("translation", "")]
        for v in self.display.secondary_translations:
            texts.append(v.get("text", ""))
            translations.append(v.get("translation", ""))

        logger.debug("[FONT_FIT] avail=%dx%d blocks=%d", available_width, available_height, len(texts))

        low, high = 8, 24
        best_font = 8

        for _ in range(10):
            if low > high:
                break
            mid = (low + high) // 2
            if self._content_fits(mid, available_width, available_height, texts, translations):
                best_font = mid
                low = mid + 1
            else:
                high = mid - 1

        result = max(8, best_font)
        logger.debug("[FONT_FIT] result=%d", result)
        return result

    def _content_fits(self, font_size, max_width, max_height, texts, translations):
        """Return True if all text blocks fit within max_width x max_height at given font size."""
        try:
            font = QFont("Segoe UI", font_size)
            fm = QFontMetrics(font)
            total_height = 0

            for text, trans in zip(texts, translations):
                full_text = f"{trans}  {text}"
                total_height += self._measure_wrapped_text_height(full_text, font, max_width)

            if len(texts) > 1:
                overlay_gap = fm.height() // 4
                total_height += (len(texts) - 1) * overlay_gap

            total_height += 4  # safety margin

            return total_height <= max_height
        except Exception as e:
            logger.error("[FONT_FIT] _content_fits error: %s", e)
            return False

    def _measure_wrapped_text_height(self, text, font, max_width):
        """Measure wrapped text height using Qt's word-boundary-or-anywhere logic."""
        doc = QTextDocument()
        doc.setDefaultFont(font)
        opt = doc.defaultTextOption()
        opt.setWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
        doc.setDefaultTextOption(opt)
        doc.setPlainText(text or "")
        doc.setTextWidth(max(1, max_width))
        return int(doc.size().height() + 0.9999)

    def _render_current(self, base_font):
        """Render the appropriate view (single or overlay) with given base font."""
        if self.display.secondary_translations:
            self._render_overlay_view(base_font)
        else:
            self._render_single_view(base_font)

    def _render_single_view(self, base_font=16):
        """Render single verse view with calculated base_font size."""
        while self.verse_layout.count():
            item = self.verse_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        if not self.display.current:
            return
        verse_font = base_font
        padding = max(4, int(base_font * 0.25))
        main_verse_label = QLabel(self.display.current.get("text", ""))
        main_verse_label.setFont(QFont("Segoe UI", verse_font))
        main_verse_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        main_verse_label.setWordWrap(True)
        main_verse_label.setStyleSheet(f"color: #e8e2d8; background: transparent; padding: {padding}px;")
        self.verse_layout.addWidget(main_verse_label)
        self.verse_layout.addStretch()

    def _render_overlay_view(self, base_font=16):
        """Render overlay view using the already-calculated base_font (no extra caps)."""
        # Clear previous content
        while self.verse_layout.count():
            item = self.verse_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not self.display.current:
            return

        total = 1 + len(self.display.secondary_translations)
        verse_font = base_font
        trans_font = max(8, int(base_font * 0.7))
        padding = max(2, int(base_font * 0.15))

        # Helper to create a rich-text label
        def add_verse(verse, is_primary=False):
            trans = verse.get("translation", "")
            text = verse.get("text", "")
            color = "rgba(200,160,60,0.8)" if is_primary else "rgba(212,168,75,0.8)"
            label = QLabel(
                f'<span style="color: {color}; font-size: {trans_font}px; font-weight: 700;">{trans}</span> '
                f'<span style="color: {"#e8e2d8" if is_primary else "#d0c8b8"};">{text}</span>'
            )
            label.setFont(QFont("Segoe UI", verse_font))
            label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
            label.setWordWrap(True)
            label.setTextFormat(Qt.TextFormat.RichText)
            label.setStyleSheet(f"background: transparent; padding: {padding}px;")
            return label

        # Primary verse (top)
        self.verse_layout.addWidget(add_verse(self.display.current, is_primary=True))

        # Overlays (below primary)
        for v in self.display.secondary_translations:
            self.verse_layout.addWidget(add_verse(v, is_primary=False))

        self.verse_layout.addStretch()

    def resizeEvent(self, event):
        """Refit text and scale reference when preview panel is resized."""
        super().resizeEvent(event)
        
        # Proportional ref_label scaling (10pt-20pt range for compact preview)
        h = self.height()
        new_size = max(10, min(20, h // 18))
        font = self.ref_label.font()
        font.setPointSize(new_size)
        self.ref_label.setFont(font)
        
        # Trigger font fitting and re-render if we have content
        if self.display.current and not self._fitting:
            self._fitting = True
            try:
                self._current_base_font = self._find_fitting_font_size()
                self._render_current(base_font=self._current_base_font)
            finally:
                self._fitting = False
    
    def set_preview_verse(self, verse):
        """Show a verse in the preview panel without pushing it to live display.
        Used by the Queue Panel for preview-on-click interaction."""
        # DEFENSIVE: Allow None (clear preview) or require dict type
        if verse is None:
            self._on_verse_changed(None)
            return
        if not isinstance(verse, dict):
            logger.warning("set_preview_verse received non-dict type: %s", type(verse).__name__)
            self._on_verse_changed(None)
            return

        ref = verse.get("reference", "")
        trans = abbreviate_translation(verse.get("translation", ""))
        display_ref = f"{ref} — {trans}" if trans else ref
        self.ref_label.setText(display_ref)
        self.ref_label.setStyleSheet(
            "color: rgba(76,175,125,0.7); background: transparent; letter-spacing: 2px;"
        )

        # Clear and render basic preview (no overlays in quick preview)
        while self.verse_layout.count():
            item = self.verse_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        text = verse.get("text", "")
        label = QLabel(text)
        label.setFont(QFont("Segoe UI", 14))
        label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        label.setWordWrap(True)
        label.setProperty("preview-verse", True)
        self.verse_layout.addWidget(label)
        self.verse_layout.addStretch()

    def _clear_verse_display(self):
        """Clear verse display."""
        while self.verse_layout.count():
            item = self.verse_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        placeholder = QLabel("Push a verse to preview it.")
        placeholder.setFont(QFont("Segoe UI", 14))
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder.setProperty("hint", True)
        self.verse_layout.addWidget(placeholder)
        self.verse_layout.addStretch()

# ── Verse Live History Panel ───────────────────────────────────────────────

class VerseLiveHistoryPanel(QScrollArea):
    """Running log of every verse sent to the congregation screen during the current session.
    Each entry shows reference, translation, timestamp.
    Click any entry to restore that verse to display.
    """
    verse_clicked = pyqtSignal(dict)

    def __init__(self, display, parent=None):
        super().__init__(parent)
        self.display = display
        self.entries = []  # List of verse dicts with timestamp

        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._container = QWidget()
        self._layout = QVBoxLayout(self._container)
        self._layout.setContentsMargins(4, 4, 4, 4)
        self._layout.setSpacing(4)
        self._layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.setWidget(self._container)

        # Placeholder
        self._placeholder = QLabel("No verses sent to screen yet.")
        self._placeholder.setFont(QFont("Segoe UI", 8))
        self._placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._placeholder.setProperty("hint", True)
        self._placeholder.setContentsMargins(8, 8, 8, 8)
        self._layout.addWidget(self._placeholder)
        self._layout.addStretch()

    def add_verse(self, verse):
        """Add a verse to the history log."""
        if not verse or not verse.get("reference"):
            return

        # Hide placeholder
        if self._placeholder:
            self._placeholder.setVisible(False)

        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")

        entry = {
            "verse": verse,
            "timestamp": timestamp,
            "reference": verse.get("reference", ""),
            "translation": verse.get("translation", ""),
        }
        self.entries.append(entry)

        # Create clickable card
        card = HistoryEntryCard(entry)
        card.clicked.connect(lambda v=verse: self.verse_clicked.emit(v))

        # Insert before the stretch
        self._layout.insertWidget(self._layout.count() - 1, card)

        # Auto-scroll to bottom
        QTimer.singleShot(50, lambda: self.verticalScrollBar().setValue(
            self.verticalScrollBar().maximum()
        ))

    def clear(self):
        """Clear all history entries."""
        self.entries.clear()
        # Remove all cards
        for i in reversed(range(self._layout.count())):
            item = self._layout.itemAt(i)
            if item and item.widget() and isinstance(item.widget(), HistoryEntryCard):
                item.widget().deleteLater()
        # Show placeholder
        if self._placeholder:
            self._placeholder.setVisible(True)


class HistoryEntryCard(QFrame):
    """A single clickable entry in the verse live history."""
    clicked = pyqtSignal(dict)

    def __init__(self, entry, parent=None):
        super().__init__(parent)
        self.entry = entry
        self.setProperty("panel", True)
        self.setFixedHeight(22)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 2, 6, 2)
        layout.setSpacing(6)

        # Timestamp
        ts = QLabel(entry["timestamp"])
        ts.setFont(QFont("Segoe UI", 6, QFont.Weight.Bold))
        ts.setProperty("result", True)
        ts.setFixedWidth(45)
        layout.addWidget(ts)

        # Reference + translation
        ref = entry["reference"]
        book_match = re.match(r'^(.+?)\s+(\d+:\d+)$', ref)
        if book_match:
            book_name = book_match.group(1).strip()
            chap_verse = book_match.group(2)
            abbrev = BOOK_ABBREV_MAP.get(book_name, book_name)
            ref = f"{abbrev} {chap_verse}"

        trans = entry.get("translation", "")
        if trans:
            ref = f"{ref} ({trans})"
        ref_label = QLabel(ref)
        ref_label.setFont(QFont("Segoe UI", 7))
        ref_label.setWordWrap(False)
        layout.addWidget(ref_label, 1)

        # Restore icon
        restore_icon = QLabel()
        restore_icon.setPixmap(icons.get_return_icon(size=16).pixmap(16, 16))
        restore_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        restore_icon.setFixedWidth(16)
        layout.addWidget(restore_icon)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.entry["verse"])
        super().mousePressEvent(event)

