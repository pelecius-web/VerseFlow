"""channel_manager.py — VerseFlow v1.1.0 Channel Manager.

Phase 1: ChannelManager wraps the existing DisplayController as the Main
channel via a DisplayChannel adapter. All existing workflows continue to use
DisplayController directly; ChannelManager provides the future public output
API that new channel-aware UI and later NDI/API/theme integrations should use.

Compatibility layer: ChannelManager exposes push_verse(), clear(), current,
verse_changed, and translations_changed so it can be substituted for a raw
DisplayController once consumers are ready to migrate.

Architecture rule: Do NOT remove the compatibility methods until all consumers
(HomePanel, navigator, queue, playlist, hotkeys, history) have been migrated.

v1.1.0 Phase 1 — ChannelManager Wrapper Foundation.
"""

import logging
from PyQt6.QtCore import QObject, pyqtSignal

from display_channel import DisplayChannel

logger = logging.getLogger("VerseFlow")


class ChannelManager(QObject):
    """Coordinates all output channels.

    Phase 1 registers only the Main channel (backed by the existing
    DisplayController adapter). Alt channel is added in Phase 4.

    New output-control code should call the channel-aware methods
    (``push_to_channel``, ``clear_channel``, etc.) rather than the
    compatibility shims at the bottom of this class.
    """

    # Emitted whenever any channel's state changes: (channel_name, state_dict)
    channel_changed = pyqtSignal(str, dict)
    # Emitted after push_to_all or clear_all: {channel_name: state_dict, …}
    all_channels_changed = pyqtSignal(dict)

    def __init__(self, main_controller, parent=None):
        """Create a ChannelManager wrapping an existing display controller.

        Args:
            main_controller: A DisplayController-compatible object. It is
                             registered as the ``"main"`` channel immediately.
        """
        super().__init__(parent)
        self._channels: dict[str, DisplayChannel] = {}
        self._linked = False  # Link Channels: when True, Main push/clear mirrors to Alt

        # Register the existing controller as the Main channel adapter.
        main_channel = DisplayChannel("main", main_controller, parent=self)
        self._register_channel(main_channel)

        # Apply persisted settings to Main channel as well.
        self._apply_persisted_settings("main", main_channel)

        logger.info("[ChannelManager] Initialized with main channel (adapter over %s)",
                    type(main_controller).__name__)

    # ── Internal registration ─────────────────────────────────────────────────

    def add_channel(self, name: str, controller, parent=None):
        """Register a new output channel.

        Loads persisted settings for the channel if available.

        Public API for channel registration — use this instead of calling
        ``_register_channel`` from outside the class.

        Args:
            name:       Channel name, e.g. ``"alt"``.
            controller: A DisplayController-compatible object.
            parent:     Optional parent QObject for the DisplayChannel adapter.

        Returns:
            The newly created DisplayChannel.

        Raises:
            ValueError: If a channel with the same name already exists.
        """
        if name in self._channels:
            raise ValueError(f"Channel '{name}' already registered")
        channel = DisplayChannel(name, controller, parent=parent or self)
        self._register_channel(channel)

        # Apply persisted settings after registration so signals are connected.
        self._apply_persisted_settings(name, channel)

        logger.debug("[ChannelManager] Registered channel '%s'", name)
        return channel

    def _apply_persisted_settings(self, name: str, channel: DisplayChannel):
        """Load and apply saved settings for a channel."""
        try:
            from settings import SettingsManager
            settings = SettingsManager()
            ch_settings = settings.get_channel_settings(name)
            channel.apply_settings(ch_settings.__dict__)
        except Exception as exc:
            logger.warning("[ChannelManager] Failed to load settings for '%s': %s", name, exc)

    def _register_channel(self, channel: DisplayChannel):
        """Register a channel and wire its state-change signals."""
        self._channels[channel.name] = channel

        channel.verse_changed.connect(lambda verse, ch=channel: self._emit_channel_changed(ch))
        channel.translations_changed.connect(lambda translations, ch=channel: self._emit_channel_changed(ch))
        channel.display_opened.connect(lambda ch=channel: self._emit_channel_changed(ch))
        channel.display_closed.connect(lambda ch=channel: self._emit_channel_changed(ch))
        channel.fullscreen_toggled.connect(lambda is_fullscreen, ch=channel: self._emit_channel_changed(ch))
        channel.mode_changed.connect(lambda mode, ch=channel: self._emit_channel_changed(ch))
        logger.debug("[ChannelManager] Channel '%s' registered", channel.name)

    def _emit_channel_changed(self, channel: DisplayChannel):
        """Emit a normalized state snapshot for a channel update."""
        self.channel_changed.emit(channel.name, channel.get_state())

    # ── Public channel API (use this for all new features) ───────────────────

    def get_channel(self, name: str) -> DisplayChannel | None:
        """Return the named channel, or None if it does not exist."""
        return self._channels.get(name)

    def channel_names(self) -> list[str]:
        """Return a list of all registered channel names."""
        return list(self._channels.keys())

    def push_to_channel(self, name: str, verse: dict):
        """Push a verse to a specific channel by name.

        Args:
            name:  Channel name, e.g. ``"main"`` or ``"alt"``.
            verse: Verse dict with at least ``reference`` and ``text`` keys.
        """
        channel = self._channels.get(name)
        if channel is None:
            logger.warning("[ChannelManager] push_to_channel: unknown channel '%s'", name)
            return
        channel.push_verse(verse)
        logger.debug("[ChannelManager] Pushed verse to channel '%s'", name)

    def clear_channel(self, name: str):
        """Clear a specific channel by name.

        Args:
            name: Channel name, e.g. ``"main"`` or ``"alt"``.
        """
        channel = self._channels.get(name)
        if channel is None:
            logger.warning("[ChannelManager] clear_channel: unknown channel '%s'", name)
            return
        channel.clear()
        logger.debug("[ChannelManager] Cleared channel '%s'", name)

    def push_to_all(self, verse: dict):
        """Push a verse to every registered channel simultaneously."""
        for channel in self._channels.values():
            channel.push_verse(verse)
        self.all_channels_changed.emit(self.get_all_states())
        logger.debug("[ChannelManager] Pushed verse to all channels")

    def clear_all(self):
        """Clear every registered channel simultaneously."""
        for channel in self._channels.values():
            channel.clear()
        self.all_channels_changed.emit(self.get_all_states())
        logger.debug("[ChannelManager] Cleared all channels")

    def set_channel_mode(self, name: str, mode: str):
        """Set the display mode on a specific channel.

        Args:
            name: Channel name.
            mode: One of ``DisplayChannel.MODE_FULLSCREEN`` or
                  ``DisplayChannel.MODE_LOWER_THIRD``.
        """
        channel = self._channels.get(name)
        if channel is None:
            logger.warning("[ChannelManager] set_channel_mode: unknown channel '%s'", name)
            return
        channel.set_display_mode(mode)

    def get_all_states(self) -> dict:
        """Return a snapshot of every channel's state keyed by name."""
        return {name: ch.get_state() for name, ch in self._channels.items()}

    # ── Link Channels ─────────────────────────────────────────────────────────

    @property
    def linked(self) -> bool:
        """True when Main push/clear automatically mirrors to Alt."""
        return self._linked

    def set_linked(self, value: bool):
        """Enable or disable channel linking (Main → Alt mirror)."""
        self._linked = value
        logger.info("[ChannelManager] Channel link: %s", "ON" if value else "OFF")

    # ── Target reconciliation ─────────────────────────────────────────────────

    def _channels_for(self, target: str) -> set[str]:
        """Return the set of channel names represented by *target*."""
        return {"main", "alt"} if target == "all" else {target}

    def _resolve_last_live(self, previous_target: str) -> dict | None:
        """Return the current verse of the first live channel in *previous_target*."""
        for name in ("main", "alt"):
            if name not in self._channels_for(previous_target):
                continue
            ch = self._channels.get(name)
            if ch and ch.current:
                return ch.current
        return None

    def switch_target(self, new_target: str, previous_target: str):
        """Reconcile channel state when Output Target changes.

        Clears channels that are leaving the target. For channels entering
        the target, pushes the last-live verse from *previous_target*.
        """
        previous_channels = self._channels_for(previous_target)
        new_channels = self._channels_for(new_target)

        last_live = self._resolve_last_live(previous_target)

        for name in previous_channels - new_channels:
            self.clear_channel(name)
        if last_live:
            for name in new_channels - previous_channels:
                self.push_to_channel(name, last_live)

    # ── Compatibility layer (delegates to Main) ───────────────────────────────
    #
    # These methods exist so that new code which receives a ChannelManager
    # can still call the same interface as the old DisplayController. They
    # will be removed once all consumers have migrated to the channel API.

    def push_verse(self, verse: dict):
        """Compatibility: push to the Main channel (same as v1.0 behavior)."""
        self.push_to_channel("main", verse)

    def clear(self):
        """Compatibility: clear the Main channel (same as v1.0 behavior)."""
        self.clear_channel("main")

    def show(self):
        """Compatibility: open the Main channel's display window."""
        ch = self._channels.get("main")
        if ch:
            ch.show()

    def hide(self):
        """Compatibility: close the Main channel's display window."""
        ch = self._channels.get("main")
        if ch:
            ch.hide()

    @property
    def current(self):
        """Compatibility: the current verse on the Main channel."""
        ch = self._channels.get("main")
        return ch.current if ch else None

    @property
    def verse_changed(self):
        """Compatibility: the verse_changed signal of the Main channel.

        Existing code that does ``channel_manager.verse_changed.connect(...)``
        receives the Main channel's signal, preserving v1.0 behavior.
        """
        ch = self._channels.get("main")
        return ch.verse_changed if ch else None

    @property
    def translations_changed(self):
        """Compatibility: the translations_changed signal of the Main channel."""
        ch = self._channels.get("main")
        return ch.translations_changed if ch else None

    @property
    def secondary_translations(self):
        """Compatibility: secondary translations list from the Main channel."""
        ch = self._channels.get("main")
        return ch.secondary_translations if ch else []

    @property
    def history(self):
        """Compatibility: history list from the Main channel's controller."""
        ch = self._channels.get("main")
        if ch and hasattr(ch.controller, 'history'):
            return ch.controller.history
        return []

    @property
    def display_window(self):
        """Compatibility: display window from the Main channel's controller."""
        ch = self._channels.get("main")
        if ch and hasattr(ch.controller, 'display_window'):
            return ch.controller.display_window
        return None

    def toggle_fullscreen(self):
        """Compatibility: toggle fullscreen on the Main channel."""
        ch = self._channels.get("main")
        if ch:
            ch.toggle_fullscreen()

    def open_display_window(self, theme_mgr, screen=None):
        """Compatibility: open the Main channel's display window."""
        ch = self._channels.get("main")
        if ch and hasattr(ch.controller, 'open_display_window'):
            return ch.controller.open_display_window(theme_mgr, screen)
        return False

    def close_display_window(self):
        """Compatibility: close the Main channel's display window."""
        ch = self._channels.get("main")
        if ch and hasattr(ch.controller, 'close_display_window'):
            ch.controller.close_display_window()

    def add_translation(self, verse: dict):
        """Compatibility: add overlay translation to the Main channel."""
        ch = self._channels.get("main")
        if ch:
            ch.add_translation(verse)

    def remove_translation(self, index: int):
        """Compatibility: remove overlay translation from the Main channel."""
        ch = self._channels.get("main")
        if ch:
            ch.remove_translation(index)

    def clear_translations(self):
        """Compatibility: clear overlay translations from the Main channel."""
        ch = self._channels.get("main")
        if ch:
            ch.clear_translations()

    def __repr__(self):
        channels = ", ".join(
            f"{name}({'live' if ch.is_live else 'clear'})"
            for name, ch in self._channels.items()
        )
        return f"<ChannelManager [{channels}]>"
