"""Test NDISender state machine — Bug 59/63 structural fix.

Tests that _was_live is never committed on start() failure, retry happens
automatically on the next channel_changed signal, and the normal lifecycle
(start → stop) works correctly.
"""

import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import sys
from pathlib import Path

SRC = Path(__file__).parent.parent / "2. Source Code"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QObject
import pytest


# ═══════════════════════════════════════════════════════════════════════
# QApplication fixture (keeps Qt engine alive across tests)
# ═══════════════════════════════════════════════════════════════════════

@pytest.fixture(scope="session")
def _qt_app():
    existing = QApplication.instance()
    if existing is not None:
        return existing
    return QApplication([])


# ═══════════════════════════════════════════════════════════════════════
# Fake objects (project pattern: no mocking library, no pytest-qt)
# ═══════════════════════════════════════════════════════════════════════

class FakeSignal:
    """Drop-in for pyqtSignal that records connections and can emit."""
    def __init__(self):
        self._callbacks = []

    def connect(self, callback):
        self._callbacks.append(callback)

    def emit(self, *args, **kwargs):
        for cb in self._callbacks:
            cb(*args, **kwargs)


class FakeDisplayWindow:
    """Minimal stand-in that NDISender reads during capture."""
    def __init__(self, visible=True, width=1920, height=1080, headless=False):
        self._visible = visible
        self._width = width
        self._height = height
        self._headless = headless

    def isVisible(self):
        return self._visible

    def size(self):
        class Size:
            def __init__(self, w, h):
                self._w = w
                self._h = h
            def isEmpty(self):
                return self._w <= 0 or self._h <= 0
        return Size(self._width, self._height)

    def grab(self):
        from PyQt6.QtGui import QPixmap
        return QPixmap(self._width, self._height)


class FakeChannel:
    """Minimal channel that NDISender reads display_window from."""
    def __init__(self, display_window=None):
        self._display_window = display_window

    @property
    def display_window(self):
        return self._display_window


class FakeChannelManager:
    """Stand-in that emits channel_changed and returns channels by name."""
    def __init__(self):
        self.channel_changed = FakeSignal()
        self._channels = {}

    def register(self, name, channel):
        self._channels[name] = channel

    def get_channel(self, name):
        return self._channels.get(name)


class FakeBridge:
    """NDI bridge stand-in with configurable create_sender failure."""
    def __init__(self, create_sender_result=42):
        self.create_sender_result = create_sender_result
        self.create_sender_calls = []
        self.destroy_sender_calls = []

    def create_sender(self, name):
        self.create_sender_calls.append(name)
        return self.create_sender_result

    def destroy_sender(self, handle):
        self.destroy_sender_calls.append(handle)


# ═══════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════

@pytest.fixture
def components():
    """Build fresh wiring for each test — bridge, manager, channel, window."""
    bridge = FakeBridge()
    mgr = FakeChannelManager()
    win = FakeDisplayWindow(visible=True, headless=False)
    ch = FakeChannel(display_window=win)
    mgr.register("main", ch)
    return bridge, mgr, ch, win


# ═══════════════════════════════════════════════════════════════════════
# Bug 59/63: _was_live must never be committed on start() failure
# ═══════════════════════════════════════════════════════════════════════

class TestStartFailureRetry:
    """All three start() failure paths + retry behaviour."""

    def test_create_sender_fails(self, components):
        """create_sender() returns None → _was_live stays False."""
        from ndi_sender import NDISender

        bridge, mgr, ch, win = components
        bridge.create_sender_result = None

        sender = NDISender("main", mgr, bridge)
        mgr.channel_changed.emit("main", {"is_live": True})

        assert sender._was_live is False,  "_was_live must not be set on SDK failure"
        assert sender._handle is None,     "no handle created on SDK failure"
        assert bridge.create_sender_calls == ["VerseFlow Main"]

    def test_channel_not_found(self, components):
        """channel is None → start() returns False before creating sender."""
        from ndi_sender import NDISender

        bridge, mgr, ch, win = components

        sender = NDISender("alt", mgr, bridge)  # "alt" not registered
        mgr.channel_changed.emit("alt", {"is_live": True})

        assert sender._was_live is False, "_was_live must not be set when channel is None"
        assert sender._handle is None
        assert bridge.create_sender_calls == []  # never reached

    def test_display_window_none(self, components):
        """display_window is None → start() returns False before creating sender."""
        from ndi_sender import NDISender

        bridge, mgr, ch, win = components
        no_win_ch = FakeChannel(display_window=None)
        mgr.register("main", no_win_ch)

        sender = NDISender("main", mgr, bridge)
        mgr.channel_changed.emit("main", {"is_live": True})

        assert sender._was_live is False, \
            "_was_live must not be set when display_window is None"
        assert sender._handle is None
        assert bridge.create_sender_calls == []  # never reached

    def test_retry_on_next_signal(self, components):
        """Failed start → next channel_changed retries start()."""
        from ndi_sender import NDISender

        bridge, mgr, ch, win = components
        bridge.create_sender_result = None  # first call fails

        sender = NDISender("main", mgr, bridge)
        mgr.channel_changed.emit("main", {"is_live": True})
        assert sender._was_live is False
        assert len(bridge.create_sender_calls) == 1

        # Now make the SDK succeed
        bridge.create_sender_result = 99
        mgr.channel_changed.emit("main", {"is_live": True})

        assert sender._was_live is True, "retry must succeed on second attempt"
        assert sender._handle == 99
        assert len(bridge.create_sender_calls) == 2


# ═══════════════════════════════════════════════════════════════════════
# Normal lifecycle (happy path)
# ═══════════════════════════════════════════════════════════════════════

class TestNormalLifecycle:
    """Start → stop cycle with _was_live tracking."""

    def test_normal_start(self, components):
        """Happy path: _was_live switches to True, handle stored."""
        from ndi_sender import NDISender

        bridge, mgr, ch, win = components
        sender = NDISender("main", mgr, bridge)

        mgr.channel_changed.emit("main", {"is_live": True})

        assert sender._was_live is True
        assert sender._handle == 42

    def test_normal_stop(self, components):
        """Clear: _was_live switches to False, sender destroyed."""
        from ndi_sender import NDISender

        bridge, mgr, ch, win = components
        sender = NDISender("main", mgr, bridge)
        mgr.channel_changed.emit("main", {"is_live": True})
        assert sender._was_live is True

        mgr.channel_changed.emit("main", {"is_live": False})

        assert sender._was_live is False
        assert sender._handle is None
        assert not sender._timer.isActive(), "capture timer must be stopped"
        assert bridge.destroy_sender_calls == [42]

    def test_stop_without_start_no_crash(self, components):
        """stop() is idempotent — safe to call when already stopped."""
        from ndi_sender import NDISender

        bridge, mgr, ch, win = components
        sender = NDISender("main", mgr, bridge)

        # Emit stop signal before any start
        mgr.channel_changed.emit("main", {"is_live": False})

        assert sender._was_live is False
        assert sender._handle is None
        assert bridge.destroy_sender_calls == []  # no handle to destroy

    def test_start_then_stop_then_start_again(self, components):
        """Full cycle: start, stop, start again works."""
        from ndi_sender import NDISender

        bridge, mgr, ch, win = components
        sender = NDISender("main", mgr, bridge)

        # Start
        mgr.channel_changed.emit("main", {"is_live": True})
        assert sender._was_live is True

        # Stop
        mgr.channel_changed.emit("main", {"is_live": False})
        assert sender._was_live is False

        # Start again
        mgr.channel_changed.emit("main", {"is_live": True})
        assert sender._was_live is True
        assert sender._handle == 42  # new handle from bridge
        assert len(bridge.create_sender_calls) == 2  # second call


# ═══════════════════════════════════════════════════════════════════════
# Signal filtering
# ═══════════════════════════════════════════════════════════════════════

class TestSignalFiltering:
    """Channel name filtering and amplification guards."""

    def test_other_channel_ignored(self, components):
        """Signals for other channels do not affect this sender."""
        from ndi_sender import NDISender

        bridge, mgr, ch, win = components
        sender = NDISender("main", mgr, bridge)

        mgr.channel_changed.emit("alt", {"is_live": True})

        assert sender._was_live is False
        assert sender._handle is None
        assert bridge.create_sender_calls == []

    def test_signal_amplification_guard(self, components):
        """Duplicate channel_changed does not double-start."""
        from ndi_sender import NDISender

        bridge, mgr, ch, win = components
        sender = NDISender("main", mgr, bridge)

        # Two identical signals — as emitted when verse_changed +
        # display_opened both trigger channel_changed
        mgr.channel_changed.emit("main", {"is_live": True})
        mgr.channel_changed.emit("main", {"is_live": True})

        assert bridge.create_sender_calls == ["VerseFlow Main"]
        assert sender._was_live is True

    def test_duplicate_stop_ignored(self, components):
        """Duplicate stop signals do not crash."""
        from ndi_sender import NDISender

        bridge, mgr, ch, win = components
        sender = NDISender("main", mgr, bridge)
        mgr.channel_changed.emit("main", {"is_live": True})

        # Two stop signals
        mgr.channel_changed.emit("main", {"is_live": False})
        mgr.channel_changed.emit("main", {"is_live": False})

        assert sender._was_live is False
        assert bridge.destroy_sender_calls == [42]  # only one destroy


# ═══════════════════════════════════════════════════════════════════════
# Self-run
# ═══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v", "--tb=short"]))
