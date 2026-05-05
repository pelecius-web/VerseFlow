"""settings_panel.py - VerseFlow Settings Panel (MVP)

MVP implementation with hotkey diagnostics and navigation back to Home.
Full settings UI (theme, display options) deferred to v1.1.
"""

import logging
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QFrame, QScrollArea, QTextEdit, QComboBox
)

from icons import get_chevron_left_icon

logger = logging.getLogger("VerseFlow")


class SettingsPanel(QWidget):
    """Settings panel with hotkey diagnostics and navigation back to Home."""

    back_requested = pyqtSignal()  # Signal to request navigation back to Home

    def __init__(self, hotkey_manager, channel_manager=None, theme_mgr=None, parent=None):
        super().__init__(parent)
        self.hotkey_manager = hotkey_manager
        self.channel_manager = channel_manager  # Required for mode changes
        self.theme_mgr = theme_mgr              # Required for theme dropdown
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
        back_btn.setStyleSheet("""
            QPushButton {
                background: rgba(200,160,60,0.15);
                color: #c8a03c;
                border: 1px solid rgba(200,160,60,0.3);
                border-radius: 4px;
                padding: 0 16px;
            }
            QPushButton:hover {
                background: rgba(200,160,60,0.25);
            }
            QPushButton:pressed {
                background: rgba(200,160,60,0.1);
            }
        """)
        back_btn.clicked.connect(self.back_requested.emit)
        header_layout.addWidget(back_btn)

        title = QLabel("Settings")
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        title.setStyleSheet("color: #e8e2d8;")
        header_layout.addWidget(title)
        header_layout.addStretch()

        main_layout.addWidget(header)

        # Content area
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(32, 32, 32, 32)
        content_layout.setSpacing(20)

        # Hotkey Diagnostics section
        diagnostics_frame = QFrame()
        diagnostics_frame.setProperty("card", True)
        diagnostics_layout = QVBoxLayout(diagnostics_frame)
        diagnostics_layout.setContentsMargins(20, 20, 20, 20)
        diagnostics_layout.setSpacing(12)

        diag_title = QLabel("Hotkey Diagnostics")
        diag_title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        diag_title.setStyleSheet("color: #e8e2d8;")
        diagnostics_layout.addWidget(diag_title)

        # Get diagnostics from hotkey manager
        diag = self.hotkey_manager.get_diagnostics()
        diag_text = QLabel()
        diag_text.setFont(QFont("Segoe UI", 10))
        diag_text.setStyleSheet("color: rgba(232,226,216,0.8);")
        diag_text.setText(
            f"Status: {'Fallback Active' if diag['using_fallback'] else 'Global Hotkeys'}\n"
            f"Backend: {diag['backend_type']}\n"
            f"Registered: {diag['registrations_count']}/{len(diag['registered_actions'])}\n"
            f"Actions: {', '.join(diag['registered_actions'])}\n"
            f"Failures: {len(diag['backend_failures'])}"
        )
        diagnostics_layout.addWidget(diag_text)

        # Test Hotkeys button
        test_btn = QPushButton("Test Hotkeys")
        test_btn.setFixedHeight(36)
        test_btn.setFont(QFont("Segoe UI", 10))
        test_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        test_btn.setStyleSheet("""
            QPushButton {
                background: rgba(76,175,125,0.15);
                color: #4caf7d;
                border: 1px solid rgba(76,175,125,0.3);
                border-radius: 4px;
                padding: 0 16px;
            }
            QPushButton:hover {
                background: rgba(76,175,125,0.25);
            }
        """)
        test_btn.clicked.connect(self._test_hotkeys)
        diagnostics_layout.addWidget(test_btn)

        # View Full Details button
        details_btn = QPushButton("View Full Details")
        details_btn.setFixedHeight(36)
        details_btn.setFont(QFont("Segoe UI", 10))
        details_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        details_btn.setStyleSheet("""
            QPushButton {
                background: rgba(20,20,36,0.5);
                color: rgba(200,160,60,0.4);
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 4px;
                padding: 0 16px;
            }
            QPushButton:hover {
                background: rgba(200,160,60,0.1);
                color: #c8a03c;
            }
        """)
        details_btn.clicked.connect(self._show_full_details)
        diagnostics_layout.addWidget(details_btn)

        content_layout.addWidget(diagnostics_frame)

        # Note about future features
        note = QLabel(
            "Note: Full settings UI (theme selector, display options)\n"
            "coming in v1.1. This MVP provides hotkey diagnostics."
        )
        note.setFont(QFont("Segoe UI", 10))
        note.setStyleSheet("color: rgba(200,160,60,0.5);")
        note.setWordWrap(True)
        content_layout.addWidget(note)

        # ── Per-Channel Settings section (Phase 6) ──────────────────────────────
        if self.channel_manager:
            channel_frame = QFrame()
            channel_frame.setProperty("card", True)
            channel_layout = QVBoxLayout(channel_frame)
            channel_layout.setContentsMargins(20, 20, 20, 20)
            channel_layout.setSpacing(12)

            ch_title = QLabel("Channel Settings")
            ch_title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
            ch_title.setStyleSheet("color: #e8e2d8;")
            channel_layout.addWidget(ch_title)

            for ch_name, ch_label in [("main", "Main Channel"), ("alt", "Alt Channel")]:
                section = self._create_channel_section(ch_name, ch_label)
                channel_layout.addWidget(section)

            content_layout.addWidget(channel_frame)

        content_layout.addStretch()

        # Add content to scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(content)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        main_layout.addWidget(scroll)

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
        instruction.setStyleSheet("color: #e8e2d8;")
        layout.addWidget(instruction)

        result = QLabel("Waiting for hotkey...")
        result.setFont(QFont("Segoe UI", 10))
        result.setStyleSheet("color: #c8a03c;")
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
        text_edit.setStyleSheet("background: rgba(20,20,36,0.8); color: #e8e2d8; border: 1px solid rgba(255,255,255,0.08);")
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
        name_label.setStyleSheet("color: #e8e2d8;")
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
