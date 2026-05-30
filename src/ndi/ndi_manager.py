"""ndi_manager.py — Coordinates NDI SDK lifecycle and per-channel NDISender registry."""

import logging

from PyQt6.QtCore import QObject

logger = logging.getLogger("VerseFlow.NDI")


class NDIManager(QObject):
    """Manages NDI SDK initialization, sender creation, and teardown.

    Phase 1 scope: Main channel only. Create senders for channels listed
    in `channels` parameter (defaults to ["main"]).

    Use the `available` property to check whether NDI is functional before
    connecting any health widgets or settings UI.
    """

    def __init__(self, channel_manager, channels=None, parent=None):
        """Initialize NDI SDK and create senders.

        Args:
            channel_manager: ChannelManager instance.
            channels: List of channel names to create senders for.
                      Defaults to ["main"] for Phase 1.
                      Extended to ["main", "alt"] in Phase 2.
            parent: Parent QObject.
        """
        super().__init__(parent)
        self._channel_manager = channel_manager
        self._senders = {}  # channel_name -> NDISender
        self._bridge = None

        if channels is None:
            channels = ["main"]   # Phase 1: Main only

        # Initialize NDI SDK
        try:
            import ndi_bridge
            ok = ndi_bridge.initialize()
            if not ok:
                logger.warning("[NDIManager] NDI SDK failed to initialize. NDI disabled.")
                return
            self._bridge = ndi_bridge   # store module, not a function
            logger.info("[NDIManager] NDI SDK initialized")
        except Exception as exc:
            logger.warning("[NDIManager] NDI SDK not available: %s", exc)
            return

        # Create senders for requested channels
        for name in channels:
            self._create_sender(name)

    @property
    def available(self) -> bool:
        """True when NDI is initialized and functional.

        Use this instead of checking is not None — a partially-constructed
        NDIManager (SDK init failed) should be treated the same as no manager.
        """
        return self._bridge is not None

    def _create_sender(self, channel_name: str):
        """Create an NDISender for the named channel."""
        if self._bridge is None:
            return
        from ndi_sender import NDISender
        from settings import SettingsManager
        sender = NDISender(channel_name, self._channel_manager, self._bridge, parent=self)
        try:
            ch_settings = SettingsManager().get_channel_settings(channel_name)
            sender.set_source_name(ch_settings.ndi_source_name)
            sender.set_enabled(ch_settings.ndi_enabled)
        except Exception:
            sender.set_source_name(f"VerseFlow {channel_name.title()}")
        self._senders[channel_name] = sender
        logger.debug("[NDIManager] Created sender for '%s'", channel_name)

    def get_sender(self, channel_name: str):
        """Return the sender for a channel, or None."""
        return self._senders.get(channel_name)

    def set_channel_ndi_enabled(self, channel_name: str, enabled: bool):
        """Enable/disable NDI output for a channel. Stop immediately when disabled."""
        sender = self._senders.get(channel_name)
        if sender is not None:
            sender.set_enabled(enabled)

    def set_channel_source_name(self, channel_name: str, name: str):
        """Set the NDI source name for a channel. Applied on next start/restart."""
        sender = self._senders.get(channel_name)
        if sender is not None:
            sender.set_source_name(name)

    def stop_all(self):
        """Stop all active senders. Idempotent — safe to call multiple times.

        Call BEFORE display windows close so NDISender can still access
        DisplayWindow references during teardown.
        """
        for sender in self._senders.values():
            sender.stop()
        logger.debug("[NDIManager] All senders stopped")

    def destroy(self):
        """Stop senders and destroy NDI SDK. Call at app shutdown.

        stop_all() is called here too as a safety net, but the caller should
        have already called stop_all() before closing display windows.
        """
        self.stop_all()
        if self._bridge is not None:
            self._bridge.destroy()
            self._bridge = None
            logger.info("[NDIManager] NDI SDK destroyed")
