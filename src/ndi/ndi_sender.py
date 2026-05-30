"""ndi_sender.py — NDISender: read-only observer that captures frames and sends via NDI."""

import logging
import time

from PyQt6.QtCore import QObject, QTimer, pyqtSignal, Qt
from PyQt6.QtGui import QImage

logger = logging.getLogger("VerseFlow.NDI")

NDI_CAPTURE_FPS = 30
_FRAME_INTERVAL_MS = 1000 // NDI_CAPTURE_FPS
_WARNING_THRESHOLD_MS = _FRAME_INTERVAL_MS - 5
_ERROR_THROTTLE_S = 5.0
_NOSIGNAL_MISS_LIMIT = 3   # consecutive None frames before emitting no-signal status


class NDISender(QObject):
    """Captures DisplayWindow frames and transmits them via NDI.

    Connects to ChannelManager.channel_changed as a read-only observer.
    Never reads or writes DisplayController, HomePanel, or any operator widget.
    """

    frame_sent       = pyqtSignal(str, int)    # (channel_name, fps)
    sender_error     = pyqtSignal(str, str)    # (channel_name, error_message)
    sender_status_changed = pyqtSignal(str, dict)  # (channel_name, status_dict)

    def __init__(self, channel_name: str, channel_manager, ndi_bridge, parent=None):
        super().__init__(parent)
        self.channel_name = channel_name
        self._channel_manager = channel_manager
        self._bridge = ndi_bridge        # the ndi_bridge module
        self._handle = None              # NDI sender handle (int or None)
        self._timer = QTimer(self)       # parented to self — cleaned up on destroy
        self._timer.timeout.connect(self._on_timer)
        self._frame_buf = None           # retains QImage alive for async SDK
        self._was_live = False           # prevents double-start from signal amplification
        self._last_error_msg = None      # dedup for sender_error throttle
        self._last_error_time = None     # time-based throttle (monotonic seconds)
        self._last_width = None         # dimensions of last successful frame (for black-on-clear)
        self._last_height = None
        self._consecutive_miss_count = 0  # no-signal tracker per roadmap §Phase 2 step 4
        self._enabled = True             # NDI output enabled (toggled via settings)
        self._source_name = None         # set from settings on start/restart

        # Connect to the broadcast signal — filter by channel name inside handler
        channel_manager.channel_changed.connect(self._on_channel_state)

    # ── Signal handler ─────────────────────────────────────────────────────

    def _on_channel_state(self, name: str, state_dict: dict):
        """Handle channel state changes. Only acts on this sender's channel.

        Signal amplification: a single push_verse() fires verse_changed AND
        display_opened (if window is lazily created). ChannelManager connects
        both to _emit_channel_changed, so channel_changed fires twice per push.
        The _was_live guard prevents double-start from these duplicate emissions.
        """
        if name != self.channel_name:
            return

        if not self._enabled:
            return

        is_live = state_dict.get("is_live", False)
        logger.debug("[NDISender:%s] _on_channel_state is_live=%s _was_live=%s",
                     self.channel_name, is_live, self._was_live)

        if is_live and not self._was_live:
            if self.start():
                self._was_live = True
        elif not is_live and self._was_live:
            self.stop()
            self._was_live = False

    # ── Lifecycle ──────────────────────────────────────────────────────────

    def start(self) -> bool:
        """Acquire DisplayWindow reference and begin capture loop.

        Returns True if the sender was successfully created and the capture
        timer started. Returns False if any precondition fails (channel not
        found, window not ready, NDI SDK error) — see Bug 59. The caller
        should only commit _was_live on success so that retry is possible
        on the next channel_changed signal.
        """
        channel = self._channel_manager.get_channel(self.channel_name)
        if channel is None:
            return False

        display_window = channel.display_window
        if display_window is None:
            logger.warning(
                "[NDISender:%s] Cannot start — display_window is None (no monitor?)",
                self.channel_name)
            return False

        source_name = self._source_name or f"VerseFlow {self.channel_name.title()}"
        self._handle = self._bridge.create_sender(source_name)
        if self._handle is None:
            self._emit_error("Failed to create NDI sender")
            return False

        self._timer.start(_FRAME_INTERVAL_MS)
        self.sender_status_changed.emit(self.channel_name, {"active": True})
        logger.info("[NDISender:%s] Started — source='%s'", self.channel_name, source_name)
        return True

    def stop(self):
        """Stop capture loop and destroy NDI sender handle.

        Sends a final black frame before teardown so receivers clear
        immediately instead of freezing the last verse on screen.
        Idempotent — safe to call multiple times.
        """
        self._timer.stop()

        if self._handle is not None:
            if self._last_width and self._last_height:
                black = QImage(self._last_width, self._last_height,
                               QImage.Format.Format_ARGB32)
                black.fill(Qt.GlobalColor.transparent)
                try:
                    self._bridge.send_frame_sync(self._handle, black, fps=NDI_CAPTURE_FPS)
                    time.sleep(0.05)
                except Exception as exc:
                    logger.debug("[NDISender:%s] Black-frame send failed: %s",
                                 self.channel_name, exc)

            self._bridge.destroy_sender(self._handle)
            self._handle = None

        self._frame_buf = None
        self._consecutive_miss_count = 0
        self._last_width = None
        self._last_height = None
        self.sender_status_changed.emit(self.channel_name, {"active": False})
        logger.debug("[NDISender:%s] Stopped", self.channel_name)

    # ── Settings integration ───────────────────────────────────────────────

    def is_active(self) -> bool:
        """True when the sender handle exists and capture loop is running."""
        return self._handle is not None

    def is_enabled(self) -> bool:
        """True when NDI output is enabled for this channel."""
        return self._enabled

    def set_enabled(self, enabled: bool):
        """Enable/disable NDI output. Stop immediately with black frame when disabled."""
        if enabled == self._enabled:
            return
        self._enabled = enabled
        if not enabled:
            self.stop()
            self._was_live = False
        else:
            channel = self._channel_manager.get_channel(self.channel_name)
            if channel is not None:
                state = channel.get_state()
                if state.get("is_live"):
                    if self.start():
                        self._was_live = True

    def set_source_name(self, name: str):
        """Update NDI source name. Takes effect on next start/restart."""
        self._source_name = name

    # ── Capture loop ───────────────────────────────────────────────────────

    def _on_timer(self):
        """Capture and send one frame. Runs every ~33ms (30fps)."""
        t0 = time.perf_counter()
        image = self._capture_frame()

        if image is not None:
            self._consecutive_miss_count = 0
            self._send_frame(image)   # submit new frame before dropping old buffer
            self._frame_buf = image   # now safe — SDK is done with previous buffer

            duration_ms = (time.perf_counter() - t0) * 1000
            if duration_ms > _WARNING_THRESHOLD_MS:
                logger.warning(
                    "[NDISender:%s] Render took %.1fms (target: %dms)",
                    self.channel_name, duration_ms, _FRAME_INTERVAL_MS)
            else:
                logger.debug(
                    "[NDISender:%s] Render took %.1fms", self.channel_name, duration_ms)

            self.frame_sent.emit(self.channel_name, NDI_CAPTURE_FPS)
        else:
            self._consecutive_miss_count += 1
            if self._consecutive_miss_count == _NOSIGNAL_MISS_LIMIT:
                logger.warning("[NDISender:%s] No frame for %d consecutive ticks — emitting no-signal",
                               self.channel_name, _NOSIGNAL_MISS_LIMIT)
                self.sender_status_changed.emit(
                    self.channel_name, {"active": True, "signal": False})

    def _capture_frame(self):
        """Capture DisplayWindow into ARGB32 QImage via QWidget.grab().

        Uses QWidget.grab() which forces Qt to render the widget tree
        directly into a pixmap. Unlike screen-level capture (which reads
        the GDI surface — empty for GPU-accelerated windows) and
        QWidget.render() (which reads the backing store — empty for
        stay-on-top / translucent windows), grab() works for all window
        types because it triggers a fresh paint cycle.

        Returns None when:
          - DisplayWindow doesn't exist (between verses — normal)
          - DisplayWindow is not visible (minimized, monitor disconnected)
          - DisplayWindow has zero size (during initialization)
        """
        channel = self._channel_manager.get_channel(self.channel_name)
        if channel is None:
            return None

        display_window = channel.display_window
        if display_window is None:
            return None

        # Headless windows (single-monitor NDI) have valid geometry
        # but are never shown — skip visibility check for them.
        if not getattr(display_window, '_headless', False) and not display_window.isVisible():
            return None

        size = display_window.size()
        if size.isEmpty():
            return None

        pixmap = display_window.grab()
        if pixmap.isNull():
            return None

        image = pixmap.toImage().convertToFormat(QImage.Format.Format_ARGB32)
        # Format_ARGB32 (straight alpha) matches NDI BGRA requirement:
        # NDI SDK docs state BGRA data is "not pre-multiplied".
        # Format_ARGB32_Premultiplied would be incorrect for NDI output.
        return image

    def _send_frame(self, image: QImage):
        """Send QImage to NDI network via ndi_bridge.

        All format conversion is internal to ndi_bridge — NDISender never
        calls convertToFormat() or touches raw pixel bytes.
        """
        if self._handle is None:
            return

        try:
            self._bridge.send_frame(self._handle, image, fps=NDI_CAPTURE_FPS)
            self._last_width = image.width()
            self._last_height = image.height()
            # Clear error state on successful send (recovery from transient failure)
            self._last_error_msg = None
            self._last_error_time = None
        except Exception as exc:
            self._emit_error(str(exc))

    # ── Error handling ─────────────────────────────────────────────────────

    def _emit_error(self, message: str):
        """Emit sender_error with time-based throttle.

        Guards against log spam when the NDI SDK enters a persistent failure
        state (send_frame fires 30x/sec). Identical AND different messages
        are both limited to one emission per _ERROR_THROTTLE_S seconds.

        A successful send_frame() call resets both guards, allowing instant
        error visibility on the next failure.
        """
        now = time.monotonic()  # coarse clock for 5s throttle (perf_counter for sub-ms render timing)
        if self._last_error_time is not None and (now - self._last_error_time) < _ERROR_THROTTLE_S:
            return  # within throttle window — suppress
        self._last_error_msg = message
        self._last_error_time = now
        logger.error("[NDISender:%s] %s", self.channel_name, message)
        self.sender_error.emit(self.channel_name, message)
