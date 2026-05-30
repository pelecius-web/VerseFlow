"""display_core.py — VerseFlow display controller.

Central IPC bus for operator/display communication. Manages what is shown on
the congregation display, draft/publish state, layout modes, and the display
window lifecycle.

Extracted from main.py in v0.7.11 modularization.
Audited v0.7.12
"""

import logging
import re

from PyQt6.QtCore import QObject, pyqtSignal

logger = logging.getLogger("VerseFlow")

from constants import resolve_book
from display_window import DisplayWindow


class DisplayController(QObject):
    """Manages what's shown on the congregation display.
    Phase 1: Added draft/publish (real-time editing) and layout modes.
    Phase 2: Central IPC bus for operator/display communication.
    """
    verse_changed = pyqtSignal(dict)
    layout_changed = pyqtSignal(str)
    draft_changed = pyqtSignal(dict)
    # Phase 2: Additional signals for display window management
    display_opened = pyqtSignal()
    display_closed = pyqtSignal()
    fullscreen_toggled = pyqtSignal(bool)
    # Multi-translation overlay support
    translations_changed = pyqtSignal(list)  # List of verse dicts for overlay

    LAYOUTS = ("single", "overlay", "chapter")

    def __init__(self, parent=None, db=None, theme_mgr=None):
        super().__init__(parent)
        self.db = db  # Database reference for overlay verse lookups
        self.theme_mgr = theme_mgr  # Theme manager for display window creation
        self.current = None      # Primary verse
        self.next = None
        self.history = []
        # Phase 1: draft/publish
        self.draft = None       # unpublished verse being edited
        self.edit_notes = ""    # operator notes for current verse
        # Phase 1: layout
        self.layout_mode = "single"
        # Phase 2: display window reference (lazily created)
        self.display_window = None
        self.allow_physical_window = True
        # Phase 4: preferred screen for lazy window creation (set externally for Alt channel)
        self._preferred_screen = -1
        self._pending_display_mode = None
        # Multi-translation support
        self.secondary_translations = []  # List of additional verses for overlay
        self._overlay_translations = []   # List of translation names for overlays

    def _ensure_display_window(self):
        """Lazily create the congregation display window when first verse goes live."""
        try:
            if self.display_window is None and self.theme_mgr:
                logger.info("Lazily creating display window")
                self.open_display_window(
                    self.theme_mgr,
                    screen=self._preferred_screen,
                    show_immediately=False,
                )
        except Exception as e:
            logger.error("ERROR creating window: %s", e, exc_info=True)

    def push_verse(self, verse):
        """Push a verse to the display — becomes the new current.
        Lazily creates the congregation display window on first use.
        If overlays are active, automatically updates them to match the new verse."""
        if not verse:
            self.clear()
            return

        # Save previous for history before overwriting.
        previous_current = self.current
        self.current = verse

        # Lazily create display window when first verse goes live.
        # Must come AFTER setting current so that display_opened carries
        # the correct verse; otherwise _sync_navigator_state receives
        # {current: None} and resets the navigator to State 1.
        self._ensure_display_window()

        if previous_current:
            self.history.append(previous_current)
        if self.next:
            self.next = None
        self.draft = None

        # If empty verse — clear verse overlays but preserve checked translation names
        # Update overlay translations to match new verse reference
        if self._overlay_translations and self.db:
            ref = verse.get("reference", "")
            ref_match = re.match(r'(.+?)\s+(\d+):(\d+)', ref)
            if ref_match:
                book_name = ref_match.group(1).strip()
                chapter = int(ref_match.group(2))
                verse_num = int(ref_match.group(3))
                book = resolve_book(book_name)

                if book:
                    new_overlays = []
                    for trans_name in self._overlay_translations:
                        overlay_verse = self.db.get_verse(f"{book} {chapter}:{verse_num}", trans_name)
                        if overlay_verse:
                            new_overlays.append(overlay_verse)
                    self.secondary_translations = new_overlays

        self.verse_changed.emit(verse)

    def set_next(self, verse):
        """Queue a verse as upcoming (preview)."""
        self.next = verse

    # ── Phase 1: Draft/Publish ────────────────────────────────────────────────

    def set_draft(self, verse):
        """Set a draft verse (operator editing live). Not yet published."""
        self.draft = verse
        self.draft_changed.emit(verse)

    def publish_draft(self):
        """Publish the current draft — becomes the current display verse."""
        if self.draft:
            self.push_verse(self.draft)
            self.draft = None

    def set_edit_notes(self, notes):
        self.edit_notes = notes

    # ── Phase 1: Layout Modes ─────────────────────────────────────────────────

    def set_layout(self, mode):
        if mode in self.LAYOUTS:
            self.layout_mode = mode
            self.layout_changed.emit(mode)

    def clear(self):
        self.current = None
        self.next = None
        self.draft = None
        self.edit_notes = ""
        self.secondary_translations = []
        self._overlay_translations = []

        # Emit verse_changed BEFORE closing the window so that
        # DisplayWindow._on_verse_changed({}) handles the close itself
        # from inside the live window (safe — object is still alive).
        self.verse_changed.emit({})

        # The window may have already closed itself via _on_verse_changed({}).
        # If it's still around, close and clean up explicitly.
        if self.display_window:
            try:
                self.display_window.destroyed.disconnect(self._on_display_destroyed)
            except (TypeError, RuntimeError):
                pass
            self.display_window.close()
            self.display_window = None
            self.display_closed.emit()

    # ── Phase 2: Display Window Management ────────────────────────────────────

    def open_display_window(self, theme_mgr, screen=None, show_immediately=True):
        """Open the congregation display window on specified screen."""
        if not self.allow_physical_window:
            logger.info("Physical display window disabled for this controller.")
            return False

        if self.display_window is not None:
            try:
                self.display_window.destroyed.disconnect(self._on_display_destroyed)
            except (TypeError, RuntimeError):
                pass
            self.display_window.close()

        from PyQt6.QtWidgets import QApplication
        screens = QApplication.screens()

        # Resolve integer screen index to live QScreen (prevents stale C++ wrapper crashes)
        screen_index = screen if isinstance(screen, int) else -1
        if isinstance(screen, int):
            screen = screens[screen] if 0 <= screen < len(screens) else None

        if len(screens) < 2:
            logger.info("Single monitor detected — creating headless window for NDI capture")
            headless = True
            if screen is None:
                screen = screens[0]
        elif screen is None:
            logger.info("No dedicated screen assigned — creating headless window for NDI capture")
            headless = True
            screen = screens[0]
        else:
            headless = False

        if screen:
            # Read church_name from settings for DisplayWidget (I7 fix)
            from settings import SettingsManager
            _settings = SettingsManager()
            church_name = _settings.get("general", "church_name", "")

            self.display_window = DisplayWindow(self, theme_mgr, screen=screen,
                                                screen_index=screen_index,
                                                headless=headless, church_name=church_name)
            if self._pending_display_mode and hasattr(self.display_window, "set_display_mode"):
                self.display_window.set_display_mode(self._pending_display_mode)
                self._pending_display_mode = None
            # Handle window closing itself (e.g., when verse is cleared)
            self.display_window.destroyed.connect(self._on_display_destroyed)
            if headless:
                # Headless — no geometry or show; window sizes itself at 1920x1080
                pass
            else:
                geo = screen.geometry()
                self.display_window.move(geo.x(), geo.y())
                self.display_window.resize(geo.width(), geo.height())
            if show_immediately and not headless:
                self.display_window.show()
            self.display_opened.emit()
            return True
        return False

    def _on_display_destroyed(self):
        """Handle display window being closed/destroyed.

        Only acts if display_window is still set — clear() and
        close_display_window() disconnect this signal before closing,
        so this only fires for unexpected closures (e.g. user closes
        the window manually).
        """
        if self.display_window is not None:
            self.display_window = None
            self.display_closed.emit()

    def close_display_window(self):
        """Close the congregation display window."""
        if self.display_window:
            try:
                self.display_window.destroyed.disconnect(self._on_display_destroyed)
            except (TypeError, RuntimeError):
                pass
            self.display_window.close()
            self.display_window = None
            self.display_closed.emit()

    def recreate_display_window_for_mode(self, mode):
        """Recreate the live display window in a new display mode."""
        current = self.current

        # Resolve stored index to live QScreen (prevents stale C++ wrapper crashes)
        from PyQt6.QtWidgets import QApplication
        _screens = QApplication.screens()
        preferred = self._preferred_screen
        if isinstance(preferred, int) and preferred >= 0:
            preferred = _screens[preferred] if preferred < len(_screens) else None
        else:
            preferred = None

        screen = preferred

        if self.display_window:
            _ts = getattr(self.display_window, "_target_screen", None)
            if isinstance(_ts, int) and _ts >= 0:
                _ts = _screens[_ts] if _ts < len(_screens) else None
            else:
                _ts = None
            screen = _ts or self.display_window.screen() or screen
            try:
                self.display_window.destroyed.disconnect(self._on_display_destroyed)
            except (TypeError, RuntimeError):
                pass
            self.display_window.close()
            self.display_window = None
            self.display_closed.emit()

        self._pending_display_mode = mode
        opened = self.open_display_window(
            self.theme_mgr,
            screen=screen,
            show_immediately=False,
        )
        if opened and current:
            self.verse_changed.emit(current)

    def toggle_fullscreen(self):
        """Toggle fullscreen on display window."""
        if self.display_window:
            self.display_window.toggle_fullscreen()
            self.fullscreen_toggled.emit(self.display_window._is_fullscreen)

    # ── Per-channel theme forwarding stubs (D11) ─────────────────────────────

    def set_logo_path(self, path: str | None) -> None:
        """Forward logo path to DisplayWindow → DisplayWidget.

        Fixes silent hasattr suppression in display_channel.py:211.
        """
        if self.display_window:
            self.display_window.set_logo_path(path)

    def set_church_name(self, church_name: str) -> None:
        """Forward church name to DisplayWindow → DisplayWidget."""
        if self.display_window:
            self.display_window.set_church_name(church_name)

    # ── Multi-Translation Overlay Support ─────────────────────────────────────

    def add_translation(self, verse):
        """Add a verse in another translation to the overlay."""
        if verse and verse not in self.secondary_translations:
            self.secondary_translations.append(verse)
            trans_name = verse.get("translation", "")
            if trans_name and trans_name not in self._overlay_translations:
                self._overlay_translations.append(trans_name)
            self.translations_changed.emit(self.secondary_translations)

    def remove_translation(self, index):
        """Remove a translation from overlay by index."""
        if 0 <= index < len(self.secondary_translations):
            removed = self.secondary_translations.pop(index)
            trans_name = removed.get("translation", "")
            if trans_name in self._overlay_translations:
                self._overlay_translations.remove(trans_name)
            self.translations_changed.emit(self.secondary_translations)

    def clear_translations(self):
        """Clear all secondary translations."""
        self.secondary_translations = []
        self._overlay_translations = []
        self.translations_changed.emit([])
