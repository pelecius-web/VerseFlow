"""settings_panel.py - VerseFlow Settings Panel

Settings panel with hotkey diagnostics, general settings,
per-channel configuration, and NDI output controls.
"""

import logging
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QIcon
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QFrame, QScrollArea, QTextEdit, QComboBox, QLineEdit, QCheckBox,
)

from icons import get_chevron_left_icon, get_keyboard_icon, get_settings_gear_icon, get_layers_icon, get_broadcast_icon, get_palette_icon

logger = logging.getLogger("VerseFlow")


class SettingsPanel(QWidget):
    """Settings panel with hotkey diagnostics and navigation back to Home."""

    back_requested = pyqtSignal()  # Signal to request navigation back to Home
    theme_designer_requested = pyqtSignal()  # NEW: open theme designer

    def __init__(self, hotkey_manager, channel_manager=None, theme_mgr=None, parent=None, ndi_manager=None):
        super().__init__(parent)
        self.hotkey_manager = hotkey_manager
        self.channel_manager = channel_manager  # Required for mode changes
        self.theme_mgr = theme_mgr              # Required for theme dropdown
        self.ndi_manager = ndi_manager
        self._setup_ui()

    def _setup_ui(self):
        """Setup the MVP settings UI."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Header with Back button
        header = QFrame()
        header.setProperty("header", True)
        header.setFixedHeight(50)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 8, 16, 8)
        header_layout.setSpacing(12)

        back_btn = QPushButton("  Back to Home")
        back_btn.setIcon(get_chevron_left_icon(size=16))
        back_btn.setFixedHeight(32)
        back_btn.setFont(QFont("Segoe UI", 10))
        back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        back_btn.setProperty("accent", "gold")
        back_btn.clicked.connect(self.back_requested.emit)
        header_layout.addWidget(back_btn)

        title = QLabel("Settings")
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        header_layout.addWidget(title)
        header_layout.addStretch()

        main_layout.addWidget(header)

        # Content area
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(32, 32, 32, 32)
        content_layout.setSpacing(20)

        # Phase 2: icon tracking and gold color resolution
        self._section_header_icon_labels = []
        _theme = self.theme_mgr.current if self.theme_mgr else None
        _gold = _theme.c("gold") if _theme else "#c8a03c"

        # Hotkey Diagnostics section
        content_layout.addWidget(self._make_section_header("Hotkey Diagnostics", variant="standard",
            icon=get_keyboard_icon(color=_gold, size=16)))
        content_layout.addWidget(self._make_separator())

        diagnostics_frame = QFrame()
        diagnostics_frame.setProperty("card", True)
        diagnostics_layout = QVBoxLayout(diagnostics_frame)
        diagnostics_layout.setContentsMargins(20, 20, 20, 20)
        diagnostics_layout.setSpacing(12)

        # Get diagnostics from hotkey manager
        diag = self.hotkey_manager.get_diagnostics()
        diag_text = QLabel()
        diag_text.setFont(QFont("Segoe UI", 10))
        diag_text.setText(
            f"Status: {'Fallback Active' if diag['using_fallback'] else 'Global Hotkeys'}\n"
            f"Backend: {diag['backend_type']}\n"
            f"Registered: {diag['registrations_count']}/{len(diag['registered_actions'])}\n"
            f"Actions: {', '.join(diag['registered_actions'])}\n"
            f"Failures: {len(diag['backend_failures'])}"
        )
        diagnostics_layout.addWidget(diag_text)

        # Button row — side by side
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        test_btn = QPushButton("Test Hotkeys")
        test_btn.setFixedHeight(36)
        test_btn.setFont(QFont("Segoe UI", 10))
        test_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        test_btn.setProperty("accent", "green")
        test_btn.clicked.connect(self._test_hotkeys)
        btn_row.addWidget(test_btn)

        details_btn = QPushButton("View Full Details")
        details_btn.setFixedHeight(36)
        details_btn.setFont(QFont("Segoe UI", 10))
        details_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        details_btn.setProperty("accent", "subtle")
        details_btn.clicked.connect(self._show_full_details)
        btn_row.addWidget(details_btn)

        diagnostics_layout.addLayout(btn_row)

        content_layout.addWidget(diagnostics_frame)

        # ── General Settings section ────────────────────────────────────────
        content_layout.addWidget(self._make_section_header("General", variant="standard",
            icon=get_settings_gear_icon(color=_gold, size=16)))
        content_layout.addWidget(self._make_separator())

        general_frame = QFrame()
        general_frame.setProperty("card", True)
        general_layout = QVBoxLayout(general_frame)
        general_layout.setContentsMargins(20, 20, 20, 20)
        general_layout.setSpacing(12)

        # Church name row
        church_row = QHBoxLayout()
        church_row.setSpacing(12)

        church_label = QLabel("Church Alias:")
        church_label.setFont(QFont("Segoe UI", 10))
        church_label.setToolTip(
            "Abbreviation or short name shown below the logo\n"
            "in lower-third mode. E.g. \"G A Zone\" or \"Grace CC\""
        )
        church_row.addWidget(church_label)

        self._church_name_input = QLineEdit()
        self._church_name_input.setPlaceholderText("e.g. G A Zone")
        self._church_name_input.setMaxLength(30)
        self._church_name_input.setFixedHeight(32)
        self._church_name_input.setFont(QFont("Segoe UI", 10))
        # Load saved value
        from settings import SettingsManager
        saved_name = SettingsManager().get("general", "church_name", "")
        self._church_name_input.setText(saved_name)
        self._church_name_input.editingFinished.connect(self._on_church_name_changed)
        church_row.addWidget(self._church_name_input, 1)

        general_layout.addLayout(church_row)

        # Hint text
        church_hint = QLabel(
            "Shown below the logo in lower-third mode. "
            "Use a short abbreviation for best results."
        )
        church_hint.setFont(QFont("Segoe UI", 9))
        church_hint.setProperty("hint", True)
        church_hint.setWordWrap(True)
        general_layout.addWidget(church_hint)

        content_layout.addWidget(general_frame)

        # ── Per-Channel Settings section (Phase 6) ──────────────────────────────
        if self.channel_manager:
            content_layout.addWidget(self._make_section_header("Channel Settings", variant="standard",
            icon=get_layers_icon(color=_gold, size=16)))
            content_layout.addWidget(self._make_separator())

            channel_frame = QFrame()
            channel_frame.setProperty("card", True)
            channel_layout = QVBoxLayout(channel_frame)
            channel_layout.setContentsMargins(20, 20, 20, 20)
            channel_layout.setSpacing(12)

            for ch_name, ch_label in [("main", "Main Channel"), ("alt", "Alt Channel")]:
                section = self._create_channel_section(ch_name, ch_label)
                channel_layout.addWidget(section)

            # Separator before secondary action (Deviation 3: visual group boundary)
            channel_layout.addWidget(self._make_separator())

            # Theme Designer button — demoted to secondary action
            designer_btn = QPushButton("Open Theme Designer")
            designer_btn.setIcon(get_palette_icon(color=_gold, size=16))
            designer_btn.setFixedHeight(36)
            designer_btn.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            designer_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            designer_btn.setProperty("accent", "gold")
            designer_btn.clicked.connect(self.theme_designer_requested.emit)
            channel_layout.addWidget(designer_btn)

            # Hint label for the designer button
            designer_hint = QLabel(
                "Edit themes used by Main and Alt channels. "
                "Changes apply only after Save and Apply."
            )
            designer_hint.setFont(QFont("Segoe UI", 9))
            designer_hint.setProperty("hint", True)
            designer_hint.setWordWrap(True)
            channel_layout.addWidget(designer_hint)

            content_layout.addWidget(channel_frame)

        # ── NDI Output section (Phase 4) ─────────────────────────────────────
        if self.ndi_manager is not None and self.ndi_manager.available:
            content_layout.addWidget(self._make_section_header("NDI Output", variant="standard",
                icon=get_broadcast_icon(color=_gold, size=16)))
            content_layout.addWidget(self._make_separator())

            ndi_frame = QFrame()
            ndi_frame.setProperty("card", True)
            ndi_layout = QVBoxLayout(ndi_frame)
            ndi_layout.setContentsMargins(20, 20, 20, 20)
            ndi_layout.setSpacing(12)

            for ch_name, ch_label in [("main", "Main Channel"), ("alt", "Alt Channel")]:
                section = self._create_ndi_section(ch_name, ch_label)
                ndi_layout.addWidget(section)

            content_layout.addWidget(ndi_frame)
        elif self.ndi_manager is not None and not self.ndi_manager.available:
            content_layout.addWidget(self._make_section_header("NDI Output", variant="standard",
                icon=get_broadcast_icon(color=_gold, size=16)))
            content_layout.addWidget(self._make_separator())

            ndi_unavail = QLabel("NDI Output: SDK initialized but not available")
            ndi_unavail.setFont(QFont("Segoe UI", 10))
            ndi_unavail.setProperty("hint", True)
            content_layout.addWidget(ndi_unavail)

        content_layout.addStretch()

        # Add content to scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(content)
        main_layout.addWidget(scroll)

    def _make_section_header(self, title: str, variant: str = "compact", icon: QIcon = None) -> QWidget:
        """Gold dot + typography-sized label, wrapped in a QWidget for use with addWidget().

        Args:
            title: Section header text (auto-uppercased).
            variant: Typography scale name ("compact" or "standard").
            icon: Optional 16px QIcon rendered left of the gold dot.
        """
        from PyQt6.QtWidgets import QWidget as _QWidget, QHBoxLayout, QFrame, QLabel
        from PyQt6.QtGui import QFont
        container = _QWidget()
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
        dot.setProperty("gold-dot", True)
        header.addWidget(dot)
        label = QLabel(title.upper())
        label.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        label.setProperty("section-header", variant)
        header.addWidget(label)
        header.addStretch()
        return container

    def _refresh_section_header_icons(self):
        """Rebuild section header icons using the current theme's gold color.

        Call this when the active theme changes to retint icons.
        Currently NOT wired to any signal — provided for Phase 4+ integration.
        """
        theme = self.theme_mgr.current if self.theme_mgr else None
        gold = theme.c("gold") if theme else "#c8a03c"
        factories = {
            "Hotkey Diagnostics": lambda: get_keyboard_icon(color=gold, size=16),
            "General":            lambda: get_settings_gear_icon(color=gold, size=16),
            "Channel Settings":   lambda: get_layers_icon(color=gold, size=16),
            "NDI Output":         lambda: get_broadcast_icon(color=gold, size=16),
        }
        for icon_label, title in self._section_header_icon_labels:
            fn = factories.get(title)
            if fn:
                icon_label.setPixmap(fn().pixmap(16, 16))

    def _make_separator(self) -> QFrame:
        """Gold separator line."""
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setProperty("separator", True)
        sep.setFixedHeight(1)
        return sep

    def _test_hotkeys(self):
        """Test hotkey functionality by showing a dialog."""
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton
        from PyQt6.QtCore import QTimer

        dialog = QDialog(self)
        dialog.setWindowTitle("Test Hotkeys")
        dialog.setFixedSize(400, 200)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(20, 20, 20, 20)

        instruction = QLabel(
            "Press a hotkey now to test:\n\n"
            "Ctrl+Shift+L - Focus Search\n"
            "Ctrl+Shift+V - Push Verse\n"
            "Ctrl+Shift+X - Clear Display\n"
            "Ctrl+Shift+Q - Add to Queue"
        )
        instruction.setFont(QFont("Segoe UI", 10))
        layout.addWidget(instruction)

        result = QLabel("Waiting for hotkey...")
        result.setFont(QFont("Segoe UI", 10))
        result.setProperty("result", True)
        layout.addWidget(result)

        close_btn = QPushButton("Close")
        close_btn.setFixedHeight(32)
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)

        # Track if a hotkey was triggered
        hotkey_triggered = [False]

        def on_hotkey_triggered(action_name):
            result.setText(f"Hotkey triggered: {action_name}")
            hotkey_triggered[0] = True

        # Connect to hotkey manager signal
        self.hotkey_manager.hotkey_triggered.connect(on_hotkey_triggered)

        # Auto-close after 5 seconds
        def check_timeout():
            if not hotkey_triggered[0]:
                result.setText("No hotkey detected (timeout)")
            QTimer.singleShot(1000, dialog.accept)

        QTimer.singleShot(5000, check_timeout)
        dialog.exec()

        # Disconnect after test
        self.hotkey_manager.hotkey_triggered.disconnect(on_hotkey_triggered)

    def _show_full_details(self):
        """Show full diagnostics in a scrollable dialog."""
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QPushButton

        dialog = QDialog(self)
        dialog.setWindowTitle("Hotkey Diagnostics - Full Details")
        dialog.resize(600, 400)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(20, 20, 20, 20)

        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setFont(QFont("Segoe UI", 9))

        # Get detailed diagnostics
        diag = self.hotkey_manager.get_diagnostics()
        details = f"""Hotkey Diagnostics Report
{'=' * 40}

Backend Status:
  Started: {diag['started']}
  Available: {diag['backend_available']}
  Type: {diag['backend_type']}
  Using Fallback: {diag['using_fallback']}

Registration:
  Total Actions: {diag['registrations_count']}
  Registered Actions: {', '.join(diag['registered_actions'])}
  Fallback Shortcuts: {diag['fallback_count']}

Failures:
  {diag['backend_failures'] if diag['backend_failures'] else 'None'}
"""
        text_edit.setText(details)
        layout.addWidget(text_edit)

        close_btn = QPushButton("Close")
        close_btn.setFixedHeight(32)
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)

        dialog.exec()

    # ── Per-Channel Settings helpers (Phase 6) ──────────────────────────────────

    def _create_channel_section(self, channel_name: str, label: str):
        """Create settings controls for a single channel."""
        section = QFrame()
        layout = QHBoxLayout(section)
        layout.setContentsMargins(0, 4, 0, 4)

        name_label = QLabel(label)
        name_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        layout.addWidget(name_label)

        layout.addStretch()

        # Mode dropdown
        mode_combo = QComboBox()
        mode_combo.addItems(["Fullscreen", "Lower Third"])
        mode_combo.setCurrentText(self._get_saved_mode(channel_name))
        mode_combo.setFixedWidth(130)
        mode_combo.currentTextChanged.connect(
            lambda text: self._on_mode_changed(channel_name, text.lower().replace(" ", "_"))
        )
        layout.addWidget(mode_combo)

        # Theme dropdown
        theme_combo = QComboBox()
        self._populate_themes(theme_combo)
        theme_combo.setCurrentText(self._get_saved_theme(channel_name))
        theme_combo.setFixedWidth(130)
        theme_combo.currentTextChanged.connect(
            lambda text: self._on_theme_changed(channel_name, text)
        )
        layout.addWidget(theme_combo)

        return section

    def _get_saved_mode(self, channel_name: str) -> str:
        """Return the persisted display mode for a channel, human-readable."""
        from settings import SettingsManager
        ch = SettingsManager().get_channel_settings(channel_name)
        return "Lower Third" if ch.mode == "lower_third" else "Fullscreen"

    def _get_saved_theme(self, channel_name: str) -> str:
        """Return the persisted theme id for a channel."""
        from settings import SettingsManager
        return SettingsManager().get_channel_settings(channel_name).theme_id

    def _populate_themes(self, combo):
        """Populate a QComboBox with available theme names from ThemeManager."""
        if self.theme_mgr is None:
            combo.addItem("default")
            return
        for theme in self.theme_mgr.available_themes():
            combo.addItem(theme.id)

    def _on_mode_changed(self, channel_name: str, mode: str):
        """Handle mode change — apply immediately and persist."""
        if self.channel_manager:
            self.channel_manager.set_channel_mode(channel_name, mode)
        from settings import SettingsManager, ChannelSettings
        sm = SettingsManager()
        ch_settings = sm.get_channel_settings(channel_name)
        ch_settings.mode = mode
        sm.set_channel_settings(channel_name, ch_settings)

    def _on_theme_changed(self, channel_name: str, theme_id: str):
        """Handle theme change — persist only (theme designer is v1.3.0 scope)."""
        from settings import SettingsManager
        sm = SettingsManager()
        ch_settings = sm.get_channel_settings(channel_name)
        ch_settings.theme_id = theme_id
        sm.set_channel_settings(channel_name, ch_settings)

    # ── NDI Output helpers (Phase 4) ───────────────────────────────────────────

    def _create_ndi_section(self, channel_name: str, label: str):
        """Create NDI settings controls for a single channel."""
        from settings import SettingsManager

        section = QFrame()
        outer_layout = QVBoxLayout(section)
        outer_layout.setContentsMargins(0, 4, 0, 4)
        outer_layout.setSpacing(4)

        # Top row: controls
        controls_row = QHBoxLayout()
        controls_row.setSpacing(8)

        name_label = QLabel(label)
        name_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        name_label.setFixedWidth(120)
        controls_row.addWidget(name_label)

        ch_settings = SettingsManager().get_channel_settings(channel_name)
        enable_cb = QCheckBox("Enabled")
        enable_cb.setChecked(ch_settings.ndi_enabled)
        enable_cb.setFont(QFont("Segoe UI", 9))
        enable_cb.toggled.connect(lambda checked, n=channel_name: self._on_ndi_enabled_toggled(n, checked))
        controls_row.addWidget(enable_cb)

        source_input = QLineEdit()
        source_input.setText(ch_settings.ndi_source_name)
        source_input.setPlaceholderText("NDI source name")
        source_input.setFixedWidth(180)
        source_input.setFixedHeight(28)
        source_input.setFont(QFont("Segoe UI", 9))
        source_input.editingFinished.connect(lambda n=channel_name, w=source_input: self._on_ndi_source_name_changed(n, w.text()))
        controls_row.addWidget(source_input)

        fps_label = QLabel("-- fps")
        fps_label.setFont(QFont("Segoe UI", 9))
        fps_label.setProperty("hint", True)
        fps_label.setFixedWidth(50)
        controls_row.addWidget(fps_label)

        outer_layout.addLayout(controls_row)

        # Bottom row: error text (wraps independently — eliminates 480px clip)
        error_label = QLabel("")
        error_label.setFont(QFont("Segoe UI", 9))
        error_label.setProperty("error", True)
        error_label.setWordWrap(True)
        outer_layout.addWidget(error_label)

        # Wire live FPS/error updates from sender signals
        sender = self.ndi_manager.get_sender(channel_name) if self.ndi_manager else None
        if sender is not None:
            sender.frame_sent.connect(lambda _ch, _fps, lbl=fps_label: lbl.setText(f"{_fps} fps"))
            sender.sender_error.connect(lambda _ch, err, lbl=error_label: lbl.setText(err))
            sender.frame_sent.connect(lambda _ch, _fps, lbl=error_label: lbl.setText(""))

        return section

    def _on_ndi_enabled_toggled(self, channel_name: str, enabled: bool):
        """Handle NDI enable toggle — apply immediately and persist."""
        if self.ndi_manager:
            self.ndi_manager.set_channel_ndi_enabled(channel_name, enabled)
        from settings import SettingsManager
        sm = SettingsManager()
        ch_settings = sm.get_channel_settings(channel_name)
        ch_settings.ndi_enabled = enabled
        sm.set_channel_settings(channel_name, ch_settings)

    def _on_ndi_source_name_changed(self, channel_name: str, name: str):
        """Handle NDI source name change — persist and apply on next start."""
        if self.ndi_manager:
            self.ndi_manager.set_channel_source_name(channel_name, name)
        from settings import SettingsManager
        sm = SettingsManager()
        ch_settings = sm.get_channel_settings(channel_name)
        ch_settings.ndi_source_name = name
        sm.set_channel_settings(channel_name, ch_settings)

    def _on_church_name_changed(self):
        """Persist the church alias to settings when the user finishes editing."""
        from settings import SettingsManager
        sm = SettingsManager()
        sm.set("general", "church_name", self._church_name_input.text().strip())
        sm.save()
