"""display_channel.py — VerseFlow v1.1.0 Display Channel Adapter.

Phase 1: DisplayChannel is a thin adapter over an existing display-like object
(currently DisplayController). It does not replace DisplayController; it wraps
it so the rest of the codebase can be migrated to the channel API gradually.

Architecture rule: DisplayController remains the working Main channel
implementation during Phase 1. This adapter is the bridge.

v1.1.0 Phase 1 — ChannelManager Wrapper Foundation.
"""

import logging
from PyQt6.QtCore import QObject, pyqtSignal

from constants import DISPLAY_MODE_FULLSCREEN, DISPLAY_MODE_LOWER_THIRD

logger = logging.getLogger("VerseFlow")


class DisplayChannel(QObject):
    """Thin adapter over an existing display-like object.

    In Phase 1, this wraps an existing DisplayController so ChannelManager
    can register it as the Main channel. No display logic is duplicated here;
    all state and signals come from the wrapped controller.

    Later phases may replace the wrapped controller with a native channel
    implementation while keeping this interface stable.
    """

    # Re-expose the wrapped controller's key signals as channel-level signals.
    # Consumers that already connect to display.verse_changed are unaffected
    # because they still hold the original DisplayController reference.
    # These signals are provided here for new channel-aware code that obtains
    # a channel from ChannelManager rather than the raw controller.
    verse_changed = pyqtSignal(dict)
    translations_changed = pyqtSignal(list)
    display_opened = pyqtSignal()
    display_closed = pyqtSignal()
    fullscreen_toggled = pyqtSignal(bool)
    mode_changed = pyqtSignal(str)

    MODE_FULLSCREEN = DISPLAY_MODE_FULLSCREEN
    MODE_LOWER_THIRD = DISPLAY_MODE_LOWER_THIRD

    def __init__(self, name: str, controller, parent=None):
        """Create a DisplayChannel wrapping an existing controller.

        Args:
            name:       Channel identifier, e.g. ``"main"`` or ``"alt"``.
            controller: A DisplayController-compatible object whose signals
                        and methods are forwarded through this adapter.
        """
        super().__init__(parent)
        self.name = name
        self._controller = controller
        self._display_mode = self.MODE_FULLSCREEN

        self._connect_controller_signal("verse_changed", self.verse_changed)
        self._connect_controller_signal("translations_changed", self.translations_changed)
        self._connect_controller_signal("display_opened", self.display_opened)
        self._connect_controller_signal("display_closed", self.display_closed)
        self._connect_controller_signal("fullscreen_toggled", self.fullscreen_toggled)

        logger.debug("[DisplayChannel] '%s' adapter created over %s", name, type(controller).__name__)

    def _connect_controller_signal(self, signal_name: str, target_signal):
        """Forward a controller signal when the wrapped object exposes it."""
        source_signal = getattr(self._controller, signal_name, None)
        if source_signal is None or not hasattr(source_signal, "connect"):
            logger.warning("[DisplayChannel] '%s' controller missing signal '%s'", self.name, signal_name)
            return
        source_signal.connect(target_signal)

    # ── Current state passthrough ─────────────────────────────────────────────

    @property
    def current(self):
        """The verse currently live on this channel, or None if clear."""
        return getattr(self._controller, 'current', None)

    @property
    def is_live(self) -> bool:
        """True when the channel has a verse actively displayed."""
        return bool(self.current)

    @property
    def display_mode(self) -> str:
        """Current display mode string (``"fullscreen"`` or ``"lower_third"``)."""
        return self._display_mode

    @property
    def secondary_translations(self):
        """List of overlay verse dicts from the wrapped controller."""
        return getattr(self._controller, 'secondary_translations', [])

    # ── Core output actions ───────────────────────────────────────────────────

    def push_verse(self, verse: dict):
        """Push a verse to this channel's output."""
        if hasattr(self._controller, 'push_verse'):
            # Sync the channel's stored mode so the new window doesn't
            # default to fullscreen when the user selected lower-third.
            self._sync_mode_to_window()
            self._controller.push_verse(verse)

    def clear(self):
        """Clear this channel's output."""
        if hasattr(self._controller, 'clear'):
            self._controller.clear()

    def show(self):
        """Open / bring forward this channel's display window."""
        if not hasattr(self._controller, 'open_display_window'):
            return
        # Get theme_mgr from controller if available, otherwise None
        theme_mgr = getattr(self._controller, 'theme_mgr', None)
        self._controller.open_display_window(theme_mgr)

    def hide(self):
        """Close this channel's display window."""
        if hasattr(self._controller, 'close_display_window'):
            self._controller.close_display_window()

    # ── Display mode ─────────────────────────────────────────────────────────

    def set_display_mode(self, mode: str):
        """Set the display mode for this channel.

        Stores the mode, emits mode_changed, and forwards the mode to the
        underlying DisplayWindow if one is available (tolerates None when no
        display window exists yet, e.g. single-monitor setups).

        Args:
            mode: One of ``DisplayChannel.MODE_FULLSCREEN`` or
                  ``DisplayChannel.MODE_LOWER_THIRD``.
        """
        valid = (self.MODE_FULLSCREEN, self.MODE_LOWER_THIRD)
        if mode not in valid:
            logger.warning("[DisplayChannel] '%s' Unknown mode '%s'; ignoring", self.name, mode)
            return
        if mode == self._display_mode:
            return
        self._display_mode = mode
        self.mode_changed.emit(mode)

        # Forward mode to the underlying DisplayWindow if available.
        # display_window can be None when no second monitor is connected,
        # so this tolerates the missing window gracefully.
        display_window = getattr(self._controller, "display_window", None)
        if display_window is not None and hasattr(display_window, "set_display_mode"):
            display_window.set_display_mode(mode)

        logger.debug("[DisplayChannel] '%s' mode set to '%s'", self.name, mode)

    def _sync_mode_to_window(self):
        """Ensure the display window's mode matches the channel's stored mode.

        When a DisplayWindow is destroyed (clear/hide) and lazily recreated
        on the next push, it defaults to fullscreen. This method forwards the
        channel's stored mode so the new window opens in the correct mode.
        """
        dw = getattr(self._controller, "display_window", None)
        if dw is not None and hasattr(dw, "set_display_mode"):
            if getattr(dw, "_display_mode", None) != self._display_mode:
                logger.debug("[DisplayChannel] '%s' syncing mode '%s' to recreated window",
                             self.name, self._display_mode)
                dw.set_display_mode(self._display_mode)

    # ── Persisted settings application ────────────────────────────────────────

    def apply_settings(self, settings: dict):
        """Apply persisted settings to this channel.

        Called by ChannelManager after channel registration.
        Settings dict is a ChannelSettings.__dict__ from
        SettingsManager.get_channel_settings().
        """
        mode = settings.get("mode")
        if mode in (self.MODE_FULLSCREEN, self.MODE_LOWER_THIRD):
            self.set_display_mode(mode)
        else:
            logger.warning("[DisplayChannel] '%s': invalid mode '%s', using fullscreen",
                           self.name, mode)

        theme_id = settings.get("theme_id")
        if theme_id and getattr(self._controller, 'theme_mgr', None) is not None:
            # ThemeManager.set_theme() returns False for unknown ids — safe fallback.
            ok = self._controller.theme_mgr.set_theme(theme_id)
            if not ok:
                logger.warning("[DisplayChannel] '%s': unknown theme_id '%s', keeping current",
                               self.name, theme_id)

        logo_path = settings.get("logo_path")
        if logo_path and hasattr(self._controller, 'set_logo_path'):
            self._controller.set_logo_path(logo_path)

    # ── State snapshot ────────────────────────────────────────────────────────

    def get_state(self) -> dict:
        """Return a snapshot of this channel's current state.

        Used by ChannelManager and preview widgets to query state without
        holding a direct reference to DisplayController.
        """
        return {
            "name": self.name,
            "is_live": self.is_live,
            "current": self.current,
            "display_mode": self._display_mode,
            "secondary_translations": self.secondary_translations,
        }

    # ── Delegation passthrough for less-common controller methods ─────────────

    def toggle_fullscreen(self):
        """Toggle fullscreen on the underlying display window."""
        if hasattr(self._controller, 'toggle_fullscreen'):
            self._controller.toggle_fullscreen()

    def add_translation(self, verse: dict):
        """Add an overlay translation to the underlying controller."""
        if hasattr(self._controller, 'add_translation'):
            self._controller.add_translation(verse)

    def remove_translation(self, index: int):
        """Remove an overlay translation from the underlying controller."""
        if hasattr(self._controller, 'remove_translation'):
            self._controller.remove_translation(index)

    def clear_translations(self):
        """Clear all overlay translations from the underlying controller."""
        if hasattr(self._controller, 'clear_translations'):
            self._controller.clear_translations()

    # ── Internal access (for ChannelManager compatibility layer) ──────────────

    @property
    def controller(self):
        """Direct access to the wrapped controller.

        Used by ChannelManager compatibility methods to satisfy existing
        code that expects a raw DisplayController. Do not use this in new
        channel-aware code.
        """
        return self._controller

    def __repr__(self):
        return f"<DisplayChannel name={self.name!r} mode={self._display_mode!r} live={self.is_live}>"
