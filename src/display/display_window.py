"""display_window.py — VerseFlow Congregation Display Window (Thin Shell)

Retains only window-management responsibilities: flags, fullscreen, headless,
resize debounce, NDI grab surface, and forwarding methods. All rendering logic
has been extracted to DisplayWidget (display_widget.py).
"""

import logging

from PyQt6.QtCore import Qt, QTimer

logger = logging.getLogger("VerseFlow")
from constants import (
    DISPLAY_MODE_FULLSCREEN, DISPLAY_MODE_LOWER_THIRD,
)
from display_widget import DisplayWidget
from PyQt6.QtWidgets import QMainWindow, QApplication


class DisplayWindow(QMainWindow):
    """Congregation display window for second monitor.
    Opens as a normal window initially. Goes frameless+fullscreen when a verse goes live.
    """

    RESIZE_DEBOUNCE_MS = 100

    def __init__(self, display_controller, theme_manager, screen=None, screen_index=-1,
                 parent=None, headless=False, church_name: str = ""):
        super().__init__(parent)
        logger.info("v0.7.2 — lazy fullscreen loaded")
        self.display = display_controller
        self.theme_mgr = theme_manager
        self._target_screen = screen_index
        self._is_fullscreen = False
        self._is_live = False
        self._display_mode = DISPLAY_MODE_FULLSCREEN
        self._headless = headless

        # Debounce expensive verse re-renders during window resize.
        self._resize_timer = QTimer()
        self._resize_timer.setSingleShot(True)
        self._resize_timer.timeout.connect(self._handle_resize_finished)

        # Start as a normal window (not frameless)
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setWindowTitle("VerseFlow — Congregation Display")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)

        # Create the rendering core widget
        self._display_widget = DisplayWidget(
            display_controller, theme_manager, church_name=church_name
        )
        self.setCentralWidget(self._display_widget)

        # Connect verse_changed signal (window lifecycle routing only)
        self.display.verse_changed.connect(self._on_verse_changed)

    def _resolve_target_screen(self):
        """Resolve stored screen index to a live QScreen, or None.

        Prevents crashes from stale C++ QScreen wrappers after monitor
        hotplug / sleep / resolution change.
        """
        if isinstance(self._target_screen, int) and self._target_screen >= 0:
            screens = QApplication.screens()
            if self._target_screen < len(screens):
                return screens[self._target_screen]
        return None

    def _on_verse_changed(self, verse):
        """Update display when verse changes.

        Handles window lifecycle (show/hide/fullscreen/headless). Delegates
        all rendering to self._display_widget._deferred_render().
        """
        if not verse:
            self._display_widget._clear_verse_content()
            self._display_widget.ref_label.setText("")
            self._is_live = False
            if self.isFullScreen() or self._is_fullscreen:
                self.showNormal()
            self._is_fullscreen = False
            self.close()
            return

        # Verse is going live — set up window based on display mode
        if not self._is_live:
            self._is_live = True
            if self._display_mode == DISPLAY_MODE_FULLSCREEN:
                self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
                self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.WindowStaysOnTopHint)
                if self._headless:
                    self.setGeometry(0, 0, 1920, 1080)
                    self.winId()
                else:
                    screen = self._resolve_target_screen() or self.screen()
                    geo = screen.geometry()
                    self.setGeometry(geo)
                    self.showFullScreen()
                    self._is_fullscreen = True
            else:
                self._apply_lower_third_window_state()

        # Reference label (fullscreen page only — lower-third has its own)
        self._display_widget.ref_label.setText(verse.get("reference", ""))

        # Defer render briefly so Windows/Qt has committed fullscreen/window
        # geometry before font-fit reads dimensions.
        QTimer.singleShot(50, lambda v=verse: self._display_widget._deferred_render(v))

    def _apply_lower_third_window_state(self):
        """Configure window for lower-third display mode.

        Sets frameless window + translucent background, positions at the
        target screen with full dimensions so the band sits at the bottom
        while the top remains transparent (desktop shows through).
        """
        if self._headless:
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
            self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
            self._display_widget.set_display_mode(DISPLAY_MODE_LOWER_THIRD)
            self.setGeometry(0, 0, 1920, 1080)
            self.update()
            return

        screen = self._resolve_target_screen() or self.screen()
        geo = screen.geometry()

        if self.isVisible() and (self.isFullScreen() or self._is_fullscreen):
            self.showNormal()
        self.hide()
        self._is_fullscreen = False

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self._display_widget.set_display_mode(DISPLAY_MODE_LOWER_THIRD)
        self.setGeometry(geo)

        self.show()
        self.update()

    def resizeEvent(self, event):
        """Recalculate font sizes proportionally when the window is resized."""
        super().resizeEvent(event)

        if self._display_mode == DISPLAY_MODE_FULLSCREEN:
            window_height = self.height()
            new_ref_size = max(24, min(60, window_height // 22))
            font = self._display_widget.ref_label.font()
            font.setPointSize(new_ref_size)
            self._display_widget.ref_label.setFont(font)

        if self._display_mode == DISPLAY_MODE_LOWER_THIRD:
            self._display_widget._update_lower_third_geometry()

        self._display_widget._fit_cache.clear()

        if self.display.current and self._is_live:
            self._resize_timer.start(self.RESIZE_DEBOUNCE_MS)

    def _handle_resize_finished(self):
        """Re-render verse content after the resize event stream settles."""
        if self.display.current and self._is_live:
            self._display_widget._render_verse_content(self.display.current)

    def set_display_mode(self, mode: str):
        """Set the rendering display mode.

        Window flags stay here. Rendering delegates to DisplayWidget.
        """
        valid = (DISPLAY_MODE_FULLSCREEN, DISPLAY_MODE_LOWER_THIRD)
        if mode not in valid:
            return
        if mode == self._display_mode:
            return
        if self._is_live:
            self._display_widget._clear_all_mode_content()
        self._display_mode = mode
        self._display_widget.set_display_mode(mode)

        # Switch window flags/attributes if live
        if self._is_live:
            if mode == DISPLAY_MODE_LOWER_THIRD:
                self._apply_lower_third_window_state()
            else:
                screen = self._resolve_target_screen() or self.screen()
                geo = screen.geometry()

                self.hide()

                self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
                self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.WindowStaysOnTopHint)

                if self._headless:
                    self.setGeometry(0, 0, 1920, 1080)
                else:
                    self.setGeometry(geo)
                    self.showFullScreen()
                    self._is_fullscreen = True

            if self.display.current:
                if mode == DISPLAY_MODE_FULLSCREEN:
                    QTimer.singleShot(50, lambda: self.display.current and
                                      self._display_widget._render_verse_content(self.display.current))
                else:
                    self._display_widget._render_verse_content(self.display.current)

    def toggle_fullscreen(self):
        """Toggle fullscreen mode."""
        if self._is_fullscreen:
            self.showNormal()
            self._is_fullscreen = False
        else:
            self.showFullScreen()
            self._is_fullscreen = True

    # ── Forwarding methods ───────────────────────────────────────────────────

    def set_theme(self, theme):
        """Forward per-channel theme to DisplayWidget."""
        self._display_widget.set_theme(theme)

    def set_logo_path(self, path: str | None) -> None:
        """Forward logo path override to DisplayWidget."""
        self._display_widget.set_logo_path(path)

    def set_church_name(self, church_name: str) -> None:
        """Forward church name to DisplayWidget."""
        self._display_widget.set_church_name(church_name)

    # ── Event handlers ───────────────────────────────────────────────────────

    def keyPressEvent(self, event):
        """Handle key events for display control."""
        if self._display_mode == DISPLAY_MODE_LOWER_THIRD:
            if event.key() == Qt.Key.Key_Escape:
                self.display.clear()
            return
        if event.key() == Qt.Key.Key_Escape:
            if self._is_fullscreen:
                self.showNormal()
                self._is_fullscreen = False
            else:
                self.close()
        elif event.key() == Qt.Key.Key_F11:
            self.toggle_fullscreen()
        super().keyPressEvent(event)

    def mouseDoubleClickEvent(self, event):
        """Double-click to toggle fullscreen (fullscreen mode only)."""
        if self._display_mode == DISPLAY_MODE_LOWER_THIRD:
            return
        self.toggle_fullscreen()
        super().mouseDoubleClickEvent(event)
