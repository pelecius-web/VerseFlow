"""channel_display_facade.py - DisplayController-compatible channel facade.

This lets legacy operator widgets keep using a display-like object while Main
output routes through ChannelManager, so selected display modes are honored.
"""

from PyQt6.QtCore import QObject, pyqtSignal


class ChannelDisplayFacade(QObject):
    """Compatibility wrapper for one ChannelManager channel."""

    verse_changed = pyqtSignal(dict)
    translations_changed = pyqtSignal(list)
    draft_changed = pyqtSignal(dict)
    layout_changed = pyqtSignal(str)
    display_opened = pyqtSignal()
    display_closed = pyqtSignal()
    fullscreen_toggled = pyqtSignal(bool)

    def __init__(self, channel_manager, channel_name: str, parent=None):
        super().__init__(parent)
        self._channel_manager = channel_manager
        self._channel_name = channel_name

        controller = self.controller
        for signal_name in (
            "verse_changed",
            "translations_changed",
            "draft_changed",
            "layout_changed",
            "display_opened",
            "display_closed",
            "fullscreen_toggled",
        ):
            source = getattr(controller, signal_name, None)
            target = getattr(self, signal_name)
            if source is not None and hasattr(source, "connect"):
                source.connect(target)

    @property
    def channel(self):
        return self._channel_manager.get_channel(self._channel_name)

    @property
    def controller(self):
        ch = self.channel
        if ch is None:
            raise RuntimeError(f"Display channel '{self._channel_name}' is not registered")
        return ch.controller

    def push_verse(self, verse: dict):
        if not verse:
            self.clear()
            return
        self._channel_manager.push_to_channel(self._channel_name, verse)

    def clear(self):
        self._channel_manager.clear_channel(self._channel_name)

    @property
    def current(self):
        return self.controller.current

    @property
    def secondary_translations(self):
        return self.controller.secondary_translations

    @property
    def history(self):
        return self.controller.history

    @property
    def draft(self):
        return self.controller.draft

    @property
    def edit_notes(self):
        return self.controller.edit_notes

    @property
    def layout_mode(self):
        return self.controller.layout_mode

    @property
    def display_window(self):
        return self.controller.display_window

    def __getattr__(self, name):
        return getattr(self.controller, name)
