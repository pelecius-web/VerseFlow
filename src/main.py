"""main.py — VerseFlow Stage 3: Dual-Monitor Display (v0.7.11 — Modularized)

Verse lookup opens full chapter navigator with highlight + arrow-key navigation.
Keyword search returns flat result list. Translation selector filters results.
Phase 2 additions: Dual-monitor presenter view, congregation display window,
operator control, monitor detection, fullscreen support.

v0.7.11: Modularized from 3,745 to 303 lines. Extracted modules:
    - constants.py (book mappings, aliases, resolver)
    - db_layer.py (VerseDB, regex constants)
    - display_core.py (DisplayController)
    - navigator.py (VerseNavigator, keyword search, cross-refs)
    - editors.py (DraftEditor, TranslationMenu)
    - home_panel.py (HomePanel, search UI, preview, history)

Audited v0.7.12: parent.parent() → signals, print() → logging, db encapsulation, state mutation → public API
"""

import logging
import sys
from pathlib import Path

# ── Path setup ──────────────────────────────────────────────────
# VerseFlow uses flat module names (e.g., "from theme import ...",
# "from db_layer import ...") even though modules live in subdirectories.
# Add all src/ subdirectories to sys.path so bare imports resolve.
_SRC_DIR = Path(__file__).parent.resolve()
for _sub in sorted(_SRC_DIR.iterdir()):
    if _sub.is_dir() and not _sub.name.startswith("_"):
        _p = str(_sub)
        if _p not in sys.path:
            sys.path.insert(0, _p)
# Also add src/ itself (some modules are flat)
_SRC_STR = str(_SRC_DIR)
if _SRC_STR not in sys.path:
    sys.path.insert(0, _SRC_STR)

from PyQt6.QtCore import Qt, QTimer

logger = logging.getLogger("VerseFlow")
from PyQt6.QtGui import QAction, QFont, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QStackedWidget, QLabel, QMessageBox, QFileDialog, QPushButton,
)

# ── Local modules ────────────────────────────────────────────────────────────
from theme import ThemeManager, DEFAULT_THEME
from hotkey_manager import HotkeyManager
from settings import SettingsManager
from db_layer import VerseDB
from display_core import DisplayController
from display_channel import DisplayChannel
from channel_manager import ChannelManager
from channel_display_facade import ChannelDisplayFacade
from home_panel import HomePanel
from settings_panel import SettingsPanel
from theme_designer import ThemeDesignerPanel


# ── Main Window ──────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    def __init__(self, theme_mgr):
        super().__init__()
        self.setWindowTitle("VerseFlow — Operator Control")
        self.resize(1280, 800)
        self.setMinimumSize(900, 600)
        
        # Store theme manager reference
        self._theme_mgr = theme_mgr
        
        # Load settings
        self._settings = SettingsManager()

        self.db = VerseDB()
        self.display = DisplayController(db=self.db, theme_mgr=self._theme_mgr)
        self.display.allow_physical_window = True
        # Main targets the external congregation monitor explicitly
        from PyQt6.QtWidgets import QApplication
        _screens = QApplication.screens()
        if len(_screens) >= 2:
            self.display._preferred_screen = 1

        # v1.1.0 Phase 4: Alt channel DisplayController.
        # ThemeManager is shared — safe under Qt's single-threaded event loop.
        self.alt_display = DisplayController(db=self.db, theme_mgr=self._theme_mgr)
        self.alt_display.allow_physical_window = True   # Phase 2: NDI requires a window (headless on single-monitor)

        # v1.1.0 Phase 1: ChannelManager wraps the existing DisplayController as
        # the Main channel. HomePanel still receives self.display for backward
        # compatibility; ChannelManager is passed for new channel-aware UI.
        self.channel_manager = ChannelManager(main_controller=self.display, parent=self)

        # v1.1.0 Phase 4: Register Alt channel.
        # Mode is auto-applied from persisted settings via add_channel → _apply_persisted_settings.
        self.channel_manager.add_channel("alt", self.alt_display)

        # Per-channel theme assignment (Phase 1 v1.3.0)
        # Each channel gets its own Theme object from ChannelSettings.theme_id.
        # DisplayChannel.set_theme() forwards to DisplayWindow → DisplayWidget.
        _ch_settings = SettingsManager()
        for ch_name in ("main", "alt"):
            ch = self.channel_manager.get_channel(ch_name)
            if ch is not None:
                cs = _ch_settings.get_channel_settings(ch_name)
                theme = self._theme_mgr.get_theme(cs.theme_id)
                if theme is not None:
                    ch.set_theme(theme)

        # v1.2.0 Phase 2: NDI Manager (Main + Alt channels)
        # Placed after ChannelManager is fully initialized.
        try:
            from ndi_manager import NDIManager
            self.ndi_manager = NDIManager(
                self.channel_manager,
                channels=["main", "alt"],  # Phase 2: Both channels
                parent=self,
            )
            if not self.ndi_manager.available:
                self.ndi_manager = None  # makes is not None reliably mean "NDI functional"
        except Exception as exc:
            logger.warning("[MainWindow] NDI not available: %s", exc)
            self.ndi_manager = None

        self.main_display = ChannelDisplayFacade(self.channel_manager, "main", parent=self)

        # Alt is logical output by default; physical preview is a future explicit action.
        self.alt_display._preferred_screen = self._get_alt_screen()

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.stack = QStackedWidget()
        layout.addWidget(self.stack)

        # HomePanel now contains everything (search, preview, navigator)
        self.home_panel = HomePanel(
            self.db, self.main_display,
            channel_manager=self.channel_manager,
            ndi_manager=self.ndi_manager,
            theme_mgr=self._theme_mgr,
        )

        # HotkeyManager must be created before SettingsPanel (it needs it for diagnostics)
        self._hotkey_manager = HotkeyManager(self)
        self._hotkey_manager.status.connect(lambda msg: self.statusBar().showMessage(msg, 5000))

        self.settings_panel = SettingsPanel(
            self._hotkey_manager,
            channel_manager=self.channel_manager,
            theme_mgr=self._theme_mgr,
            ndi_manager=self.ndi_manager,
        )

        # Phase 2 v1.3.0: Theme Designer panel (stack index 2)
        self.theme_designer = ThemeDesignerPanel(
            theme_mgr=self._theme_mgr,
            channel_manager=self.channel_manager,
        )

        # Phase 4: Wire NDI sender status changes to refresh the preview status row
        if self.ndi_manager is not None:
            for ch in ("main", "alt"):
                sender = self.ndi_manager.get_sender(ch)
                if sender is not None:
                    sender.sender_status_changed.connect(
                        lambda _name, _state: self.home_panel._update_preview_status_row()
                    )

        self.stack.addWidget(self.home_panel)  # Index 0: Home
        self.stack.addWidget(self.settings_panel)  # Index 1: Settings
        self.stack.addWidget(self.theme_designer)  # Index 2: Theme Designer

        # Connect SettingsPanel back button to navigate to Home (via _switch_tab for style updates)
        self.settings_panel.back_requested.connect(lambda: self._switch_tab(0))

        # Connect SettingsPanel Theme Designer button to navigate to Theme Designer
        self.settings_panel.theme_designer_requested.connect(lambda: self._switch_tab(2))

        # Connect ThemeDesignerPanel back button to navigate to Settings
        self.theme_designer.back_requested.connect(lambda: self._switch_tab(1))

        # Connect HomePanel sidebar tab buttons to stack navigation
        self.home_panel.stack_nav_requested.connect(self._switch_tab)

        # Phase 2: Add display window management to status bar
        self.statusBar().showMessage("Ready — VerseFlow v1.3.0")
        
        raw_hotkeys = self._settings.get_section("hotkeys")
        hotkeys, hotkey_issues = self._settings.validate_hotkeys(raw_hotkeys)
        if hotkey_issues:
            issue_msg = "; ".join(hotkey_issues[:2])
            if len(hotkey_issues) > 2:
                issue_msg += "; more issues in config"
            logger.warning("[HOTKEYS] %s", issue_msg)
            self.statusBar().showMessage(f"Hotkey config issues: {issue_msg}", 7000)
        for action_name, shortcut, callback in [
            ("focus_search", hotkeys["focus_search"], self.home_panel._focus_search),
            ("push_highlighted_verse", hotkeys["push_highlighted_verse"], self.home_panel._on_show),
            ("clear_live_display", hotkeys["clear_live_display"], self.home_panel._on_hide),
            ("add_highlighted_to_queue", hotkeys["add_highlighted_to_queue"], self.home_panel._add_highlighted_to_queue),
        ]:
            if shortcut:
                self._hotkey_manager.register_action(action_name, shortcut, callback)
        if hotkeys.get("enabled", True):
            self._hotkey_manager.start(self)

        # Phase 2: Add display controls to main window menu
        self._setup_display_controls()

        # Phase 2 v1.3.0: Ctrl+Shift+T global shortcut to open Theme Designer
        designer_shortcut = QShortcut(QKeySequence("Ctrl+Shift+T"), self)
        designer_shortcut.activated.connect(lambda: self._switch_tab(2))

        # Phase 2: Auto-open display window if configured
        QTimer.singleShot(500, self._auto_open_display)

        # Stage 4: Sync window title with playlist current file and dirty state
        self.home_panel.doc_manager.dirty_changed.connect(self._update_window_title)
        self.home_panel.doc_manager.file_path_changed.connect(self._update_window_title)
        self.home_panel.doc_manager.title_changed.connect(self._update_window_title)
        self._update_window_title()
        # Surface non-fatal backup warnings to the operator via the status bar
        self.home_panel.doc_manager.backup_warning.connect(
            lambda msg: self.statusBar().showMessage(f"⚠ {msg}", 6000)
        )

    def _switch_tab(self, index):
        """Switch to the specified tab and update button styles."""
        self.stack.setCurrentIndex(index)

        _active_style = """
            QPushButton {
                background: rgba(200,160,60,0.15);
                color: #c8a03c;
                border: 1px solid rgba(200,160,60,0.3);
                border-radius: 4px;
                padding: 0 16px;
            }
        """
        _inactive_style = """
            QPushButton {
                background: rgba(20,20,36,0.5);
                color: rgba(200,160,60,0.4);
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 4px;
                padding: 0 16px;
            }
        """

        if index == 0:
            self.home_panel.btn_tab_home.setStyleSheet(_active_style)
            self.home_panel.btn_tab_settings.setStyleSheet(_inactive_style)
        elif index == 1:
            self.home_panel.btn_tab_home.setStyleSheet(_inactive_style)
            self.home_panel.btn_tab_settings.setStyleSheet(_active_style)
        elif index == 2:
            # Theme Designer — no sidebar button to highlight.
            # Both Home and Settings buttons revert to inactive style.
            self.home_panel.btn_tab_home.setStyleSheet(_inactive_style)
            self.home_panel.btn_tab_settings.setStyleSheet(_inactive_style)

    def _update_window_title(self):
        """Update window title to show current file, title and dirty state."""
        doc = self.home_panel.doc_manager
        title = doc.display_name()
        dirty = "*" if doc.is_dirty else ""
        self.setWindowTitle(f"VerseFlow — {title}{dirty} — Operator Control")
    
    def _auto_open_display(self):
        """No longer auto-opens display window on launch.
        Display window is now created lazily when first verse goes live.
        """
        pass
    
    def _setup_display_controls(self):
        """Phase 2: Setup display window controls + Edit menu for Undo/Redo."""

        # ── View menu (Panel navigation) ────────────────────────────────────────
        view_menu = self.menuBar().addMenu("&View")

        home_action = QAction("&Home", self)
        home_action.setShortcut(QKeySequence("Ctrl+1"))
        home_action.setStatusTip("Switch to Home panel")
        home_action.triggered.connect(lambda: self._switch_tab(0))
        view_menu.addAction(home_action)

        settings_action = QAction("&Settings", self)
        settings_action.setShortcut(QKeySequence("Ctrl+2"))
        settings_action.setStatusTip("Switch to Settings panel")
        settings_action.triggered.connect(lambda: self._switch_tab(1))
        view_menu.addAction(settings_action)

        # Phase 2 v1.3.0: Theme Designer menu action
        designer_action = QAction("Theme &Designer", self)
        designer_action.setShortcut(QKeySequence("Ctrl+3"))
        designer_action.setStatusTip("Open the Theme Designer")
        designer_action.triggered.connect(lambda: self._switch_tab(2))
        view_menu.addAction(designer_action)

        view_menu.addSeparator()

        # ── Edit menu (Undo / Redo) ──────────────────────────────────────────────
        edit_menu = self.menuBar().addMenu("&Edit")

        undo_action = QAction("&Undo", self)
        undo_action.setShortcut(QKeySequence.StandardKey.Undo)
        undo_action.setStatusTip("Undo the last playlist/queue change")
        undo_action.triggered.connect(self.home_panel.doc_manager.undo)
        undo_action.setEnabled(self.home_panel.doc_manager.undo_stack.canUndo())
        edit_menu.addAction(undo_action)

        redo_action = QAction("&Redo", self)
        redo_action.setShortcut(QKeySequence.StandardKey.Redo)
        redo_action.setStatusTip("Redo the last undone change")
        redo_action.triggered.connect(self.home_panel.doc_manager.redo)
        redo_action.setEnabled(self.home_panel.doc_manager.undo_stack.canRedo())
        edit_menu.addAction(redo_action)

        # Connect undo stack signals to update action enabled states
        self.home_panel.doc_manager.undo_stack.canUndoChanged.connect(undo_action.setEnabled)
        self.home_panel.doc_manager.undo_stack.canRedoChanged.connect(redo_action.setEnabled)

        edit_menu.addSeparator()

        save_action = QAction("&Save Playlist", self)
        save_action.setShortcut(QKeySequence.StandardKey.Save)
        save_action.setStatusTip("Save the current playlist")
        save_action.triggered.connect(self._save_playlist)
        edit_menu.addAction(save_action)

        # ── Display menu ────────────────────────────────────────────────────────
        # Create menu for display controls
        display_menu = self.menuBar().addMenu("&Display")

        # Open Main display window action
        open_display_action = QAction("Open &Main Display Window", self)
        open_display_action.setShortcut("Ctrl+D")
        open_display_action.triggered.connect(self._open_display)
        display_menu.addAction(open_display_action)

        # Close Main display window action
        close_display_action = QAction("Close Ma&in Display Window", self)
        close_display_action.setShortcut("Ctrl+Shift+D")
        close_display_action.triggered.connect(self._close_display)
        display_menu.addAction(close_display_action)

        display_menu.addSeparator()

        # Open Alt display window action
        open_alt_action = QAction("Open &Alt Display Window", self)
        open_alt_action.triggered.connect(self._open_alt_display)
        display_menu.addAction(open_alt_action)

        # Close Alt display window action
        close_alt_action = QAction("Close Al&t Display Window", self)
        close_alt_action.triggered.connect(self._close_alt_display)
        display_menu.addAction(close_alt_action)
        
        # Toggle fullscreen action
        toggle_fs_action = QAction("Toggle &Fullscreen", self)
        toggle_fs_action.setShortcut("F11")
        toggle_fs_action.triggered.connect(self._toggle_display_fullscreen)
        display_menu.addAction(toggle_fs_action)
        
        display_menu.addSeparator()
        
        # Detect monitors action
        detect_monitors_action = QAction("&Detect Monitors", self)
        detect_monitors_action.triggered.connect(self._detect_monitors)
        display_menu.addAction(detect_monitors_action)
    
    def _open_display(self):
        """Open the congregation display window."""
        from PyQt6.QtWidgets import QApplication, QMessageBox
        screens = QApplication.screens()
        if len(screens) < 2:
            QMessageBox.information(
                self, "No Monitor Detected",
                "Only one monitor detected. The display window requires an external monitor to be connected."
            )
            return
        
        success = self.display.open_display_window(self._theme_mgr)
        if success:
            self.statusBar().showMessage("Display window opened", 3000)
        else:
            self.statusBar().showMessage("Failed to open display window", 3000)
    
    def _close_display(self):
        """Close the congregation display window."""
        self.display.close_display_window()
        self.statusBar().showMessage("Display window closed", 3000)
    
    def _toggle_display_fullscreen(self):
        """Toggle fullscreen on the display window."""
        self.display.toggle_fullscreen()
    
    def _detect_monitors(self):
        """Detect and display information about connected monitors."""
        from PyQt6.QtWidgets import QApplication, QMessageBox
        screens = QApplication.screens()
        info = f"Detected {len(screens)} monitor(s):\n\n"
        for i, screen in enumerate(screens):
            geo = screen.geometry()
            info += f"Monitor {i+1}: {screen.name()}\n"
            info += f"  Resolution: {geo.width()}x{geo.height()}\n"
            info += f"  Position: ({geo.x()}, {geo.y()})\n\n"

    def _get_alt_screen(self):
        """Return the screen index for Alt output, or -1 if unavailable.

        Strategy:
          - 3+ monitors: Alt goes to screen[2] (dedicated third monitor)
          - 1-2 monitors: Alt is logical-only (no physical window by default)
        Alt physical output requires explicit future enablement.
        """
        screens = QApplication.screens()
        if len(screens) >= 3:
            return 2
        return -1

    def _open_alt_display(self):
        """Open the Alt display window on the appropriate screen.

        Alt physical output is disabled by default. It only opens on 3+ monitors
        where a dedicated third screen is available.
        """
        if not self.alt_display.allow_physical_window:
            self.statusBar().showMessage(
                "Alt physical preview is disabled by default. "
                "Enable via Settings or connect a third monitor.", 5000)
            return
        screen = self._get_alt_screen()
        if screen < 0:
            self.statusBar().showMessage(
                "No dedicated Alt monitor (requires 3+ monitors).", 4000)
            return
        success = self.alt_display.open_display_window(self._theme_mgr, screen=screen)
        if success:
            self.statusBar().showMessage("Alt display window opened", 3000)

    def _close_alt_display(self):
        """Close the Alt display window."""
        self.alt_display.close_display_window()
        self.statusBar().showMessage("Alt display window closed", 3000)

    def _save_playlist(self):
        """Save current playlist — prompts for path if file is new."""
        from PyQt6.QtWidgets import QFileDialog, QMessageBox
        from pathlib import Path
        doc = self.home_panel.doc_manager
        if doc.current_file:
            ok, msg = doc.save()
            if ok:
                self.statusBar().showMessage(f"Saved '{doc.display_name()}'.", 3000)
            else:
                err = f"Failed to save '{doc.display_name()}'.\n\n{msg}" if msg else \
                      "Save failed — check file permissions."
                QMessageBox.critical(self, "Save Failed", err)
                self.statusBar().showMessage("Save failed.", 4000)
        else:
            path, _ = QFileDialog.getSaveFileName(
                self, "Save Playlist", "", "VerseFlow Playlists (*.verseplaylist)"
            )
            if path:
                ok, msg = doc.save_as(Path(path))
                if ok:
                    self.statusBar().showMessage(f"Saved '{Path(path).stem}'.", 3000)
                else:
                    err = f"Failed to save to:\n{path}\n\n{msg}" if msg else \
                          f"Failed to save to:\n{path}"
                    QMessageBox.critical(self, "Save Failed", err)

    def closeEvent(self, event):
        """Prompt to save if there are unsaved changes before closing."""
        if not self.home_panel._maybe_save_changes():
            event.ignore()
            return

        self._hotkey_manager.stop()

        # v1.2.0: Stop NDI senders BEFORE display windows close.
        # NDISender._capture_frame() accesses DisplayWindow via
        # channel.display_window. If the window is destroyed first,
        # render() crashes on a deleted C++ object.
        if self.ndi_manager is not None:
            self.ndi_manager.stop_all()

        # Close display windows (NDI senders no longer hold references)
        self.display.close_display_window()
        self.alt_display.close_display_window()

        # Destroy NDI SDK after all senders are stopped and windows closed
        if self.ndi_manager is not None:
            self.ndi_manager.destroy()

        event.accept()



# ── Entry point ──────────────────────────────────────────────────────────────

def main():
    import traceback
    logging.basicConfig(level=logging.DEBUG, format="%(levelname)s [%(name)s] %(message)s")
    try:
        app = QApplication(sys.argv)
        app.setApplicationName("VerseFlow")
        app.setStyle("Fusion")

        # Apply theme via theme engine
        theme_mgr = ThemeManager()
        settings = SettingsManager()
        active_theme = settings.get("theme", "active_theme", DEFAULT_THEME)
        theme_mgr.set_app_theme(active_theme, app=app)

        window = MainWindow(theme_mgr)
        window.show()
        logger.info("VerseFlow window created successfully")
        sys.exit(app.exec())
    except Exception as e:
        logger.error("ERROR: %s", e, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
