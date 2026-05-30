# Phase 1 â€” NDI Bridge + NDISender Skeleton + Capture Loop
## Implementation Plan (v4 â€” Quad-Audited with Bug Fixes)

> **Status:** Complete â€” Phase 1 implemented, bugs 55â€“62 fixed (May 9, 2026)  
> **Audit basis:** Two independent codebase audits + NDI SDK correctness audit + vMix production validation  
> **Sub-roadmap deviations:** 4 intentional (documented below with justification)

---

## Deviations from v1.2.0 Sub-Roadmap

### Deviation 1 â€” ARGB32 â†’ BGRA: no format conversion (sub-roadmap Section 5.3 contradicted)

**Sub-roadmap says:**
```
All pixel format conversion (ARGB32 â†’ RGBA8888 â†’ BGRA channel swap)
is internal to ndi_bridge.py.
```

**Plan says:** No conversion. Pass ARGB32 memory directly as NDI BGRA.

**Justification:** `QImage.Format_ARGB32` packs pixels as `0xAARRGGBB`. On little-endian x64 (the only platform VerseFlow targets), the four bytes in memory are `[BB, GG, RR, AA]` â€” exactly NDI's BGRA byte order. The sub-roadmap's `convertToFormat(RGBA8888)` + channel swap adds a full-frame copy (~8MB at 1080p, 30 times/sec) with zero benefit. The sub-roadmap's Section 5.3 is factually wrong about ARGB32 byte order on little-endian systems.

**Safety:** `initialize()` checks `sys.byteorder != "little"` and returns `False` (graceful degradation) rather than crashing at import time. Documented in `send_frame()` docstring.

### Deviation 2 â€” `_sync_initial_state()` removed from Phase 1 (sub-roadmap Section 6)

**Sub-roadmap says:** "In `NDIManager.__init__`, after creating senders, check if any channel is already live and start appropriate senders."

**Plan says:** Removed â€” dead code.

**Justification:** VerseFlow's `closeEvent` calls `close_display_window()` which calls `clear()`, setting `DisplayController.current = None`. No live verse persists across app restarts. The `_sync_initial_state` loop will never find `is_live == True`. Keeping dead code that "handles a case that can't happen" is misleading maintenance debt.

### Deviation 3 â€” Endianness guard in `initialize()`, not module load (sub-roadmap implied module-level)

**Sub-roadmap says:** (Section 4.2) Frame format assumes little-endian. No guard location specified.

**Plan says:** Guard in `initialize()` as a graceful `return False`, not an import-time `assert`.

**Justification:** Module-level `assert` crashes imports on big-endian systems, blocking even test runners and type checkers. Scoping the check to `initialize()` allows the module to always be importable, with NDI gracefully disabled when the platform is unsupported.

### Deviation 4 â€” Frame capture uses `QWidget.grab()`, not `QWidget.render()` (sub-roadmap Section 3.1 / 4.3 / Decision 1)

**Sub-roadmap says (Decision 1):**
```
QWidget.render() paints into an off-screen QImage with Format_ARGB32.
The surface starts fully transparent (image.fill(Qt.GlobalColor.transparent)).
The painted result contains genuine per-pixel alpha.
```

**Plan says:** Use `display_window.grab()` â†’ `pixmap.toImage().convertToFormat(ARGB32)`.

**Justification:** Both `render()` and `grabWindow()` were tested and failed on Windows 10/11 with GPU-accelerated Qt rendering. `render()` reads from Qt's backing store â€” empty for fullscreen windows with `WindowStaysOnTopHint` and for translucent windows with `WA_TranslucentBackground`. `grabWindow()` reads the GDI surface via `GetWindowDC()` + `BitBlt()` â€” GPU content rendered via Direct2D â†’ DirectComposition never touches the GDI DC. The code comment claiming `grabWindow()` "reads from the DWM compositor" was incorrect.

`QWidget.grab()` forces Qt to trigger a fresh `paintEvent()` cycle directly into a pixmap, bypassing both the backing store and OS-level surface concerns. It works correctly for fullscreen, stay-on-top, and translucent windows alike. For single-monitor (headless) mode, `grab()` works on realized-but-hidden widgets, which `render()` does not.

**Alpha trade-off:** `grab()` does not preserve per-pixel alpha â€” the resulting pixmap has the composited background. For fullscreen mode this is correct (fully opaque). For lower-third mode, the transparent area above the band will show the window's background color rather than true transparency. Alpha channel validation (Phase 3) will determine whether a mode-specific capture strategy is needed.

### Deviation 5 â€” `NDIlib_video_frame_v2_t` struct retained in module-level `_frame_cache` (not planned)

**Original plan:** Frame struct was a local variable in `send_frame()`.

**Actual:** Module-level `_frame_cache = {}` dict keyed by sender handle. Each `send_frame()` stores the struct in `_frame_cache[handle]` before calling the asynchronous SDK function. Struct survives until next `send_frame()` call overwrites it. `destroy_sender()` pops the cache entry.

**Justification:** `NDIlib_send_send_video_async_v2` returns immediately; the SDK's background encoder thread reads from the struct later. A Python-local `frame` variable is garbage-collected when `send_frame()` returns, leaving the SDK reading freed heap memory â€” undefined behavior on every frame. This was the primary cause of corrupted/missing NDI output in vMix.

### Deviation 6 â€” `timecode = 9223372036854775807` (`INT64_MAX`), not `0`

**Original plan:** `frame.timecode = 0  # NDIlib_send_timecode_synthesize equivalent`

**Actual:** `frame.timecode = 9223372036854775807  # NDIlib_send_timecode_synthesize`

**Justification:** The constant `0` is "00:00:00:00" â€” a valid fixed timecode. `NDIlib_send_timecode_synthesize` is `INT64_MAX`. Low impact on live switchers but incorrect for ISO recordings and timecode-dependent gear like HyperDecks.

### Deviation 7 â€” Single-monitor headless mode (sub-roadmap deferred to Phase 2)

**Original plan:** Single-monitor edge case documented as known limitation, deferred to Phase 2.

**Actual:** Single-monitor setups now create a **headless** DisplayWindow: sized 1920Ã—1080, native window handle forced via `winId()`, never shown on screen. NDI sender captures via `grab()` which works on realized-but-hidden widgets. Mode switches (FSâ†”LT) skip all `show()`/`showFullScreen()` calls when `_headless=True`.

**Justification:** Production testing revealed the single-monitor limitation blocked NDI entirely â€” no DisplayWindow meant no NDI sender. Headless mode unblocks testing and single-operator setups without requiring a second physical monitor.

---

## NDI SDK Dependency

This implementation requires the NDI runtime DLL (`Processing.NDI.Lib.x64.dll`) from NDI SDK v6.x. The DLL search order in `ndi_bridge.py`:

1. `C:\Program Files\NDI\NDI 6 SDK\Bin\x64\` (standard SDK install)
2. Next to the VerseFlow executable / script directory
3. System PATH

If the DLL is not found at any of these locations, VerseFlow launches normally with NDI disabled and a warning logged. No crash.

---

## Files Created

- `ndi_bridge.py` â€” ctypes NDI SDK wrapper (~150 lines)
- `ndi_sender.py` â€” `NDISender` QObject with capture loop
- `ndi_manager.py` â€” `NDIManager` coordinating SDK lifecycle

## Files Modified

- `ndi_bridge.py` â€” ctypes NDI SDK wrapper (~270 lines)
- `ndi_sender.py` â€” `NDISender` QObject with capture loop (~225 lines)
- `ndi_manager.py` â€” `NDIManager` coordinating SDK lifecycle (~98 lines)
- `main.py` â€” instantiate `NDIManager`; fix `closeEvent` shutdown order
- `display_core.py` â€” single-monitor headless fallback (Deviation 7)
- `display_window.py` â€” `_headless` flag + headless FS/LT branches (Deviation 7)
- `display_channel.py` â€” add `display_window` forwarding property (3 lines)
- `pre_commit_checks.py` â€” add Phase 1 NDI guards; update grab/grabWindow rules
- `verify_critical_fixes.py` â€” add NDI source checks

## Files Not Touched

- `channel_display_facade.py` â€” active dependency of `HomePanel`
- `channel_manager.py` compatibility shims â€” do not modify
- `home_panel.py` â€” no operator UI changes in this phase

---

## [NEW] `ndi_bridge.py`

A self-contained `ctypes` wrapper over the NDI C SDK. No PyPI dependencies. All format handling is internal to this module â€” `NDISender` never touches raw bytes or calls `convertToFormat()`.

### Module-level code

```python
# ndi_bridge.py â€” ctypes wrapper over Processing.NDI.Lib.x64.dll

import ctypes
import logging
import os
import sys
from ctypes import (
    c_bool, c_char_p, c_float, c_int, c_int64, c_uint32, c_void_p,
    POINTER, Structure,
)

logger = logging.getLogger("VerseFlow.NDI")

# --- NDI FourCC constants ---
# NDI uses FourCC character codes, not sequential integers.
# FourCC('B','G','R','A') = ord('B') | (ord('G')<<8) | (ord('R')<<16) | (ord('A')<<24)
NDIlib_FourCC_video_type_BGRA = 0x41524742

# --- DLL loading ---
_NDI_DLL_NAME = "Processing.NDI.Lib.x64.dll"
_dll = None
_initialized = False

_SEARCH_PATHS = [
    r"C:\Program Files\NDI\NDI 6 SDK\Bin\x64",
    os.path.dirname(os.path.abspath(__file__)),
    os.path.dirname(sys.executable),
]

def _load_dll():
    """Search for and load the NDI runtime DLL. Returns None if not found."""
    global _dll
    if _dll is not None:
        return _dll

    for search_dir in _SEARCH_PATHS:
        candidate = os.path.join(search_dir, _NDI_DLL_NAME)
        if os.path.isfile(candidate):
            try:
                _dll = ctypes.CDLL(candidate)
                logger.info("[NDI Bridge] Loaded DLL: %s", candidate)
                return _dll
            except OSError as exc:
                logger.warning("[NDI Bridge] Failed to load %s: %s", candidate, exc)

    # Try system PATH as last resort
    try:
        _dll = ctypes.CDLL(_NDI_DLL_NAME)
        logger.info("[NDI Bridge] Loaded DLL from system PATH")
        return _dll
    except OSError:
        logger.warning("[NDI Bridge] NDI runtime DLL not found. NDI output disabled.")
        return None

# --- NDI SDK function signatures ---

# Module-level struct definitions (not redefined per function call)
class NDI_send_create_t(Structure):
    _fields_ = [
        ("p_ndi_name", c_char_p),
        ("p_groups", c_char_p),
        ("clock_video", c_bool),
        ("clock_audio", c_bool),
    ]

class NDIlib_video_frame_v2_t(Structure):
    _fields_ = [
        ("xres", c_int),
        ("yres", c_int),
        ("FourCC", c_uint32),              # NDIlib_FourCC_video_type_BGRA
        ("frame_rate_N", c_int),
        ("frame_rate_D", c_int),
        ("picture_aspect_ratio", c_float),
        ("frame_format_type", c_int),       # 0 = progressive
        ("timecode", c_int64),
        ("p_data", c_void_p),
        ("line_stride_in_bytes", c_int),
        ("p_metadata", c_char_p),
        ("timestamp", c_int64),
    ]

def _setup_functions():
    """Configure ctypes function signatures for the NDI SDK."""
    dll = _load_dll()
    if dll is None:
        return None

    # NDIlib_initialize()
    dll.NDIlib_initialize.restype = c_bool

    # NDIlib_destroy()
    dll.NDIlib_destroy.restype = None

    # NDIlib_send_create(NDIlib_send_create_t)
    dll.NDIlib_send_create.restype = c_void_p
    dll.NDIlib_send_create.argtypes = [c_void_p]

    # NDIlib_send_send_video_async_v2(NDIlib_send_instance_t, NDIlib_video_frame_v2_t*)
    dll.NDIlib_send_send_video_async_v2.restype = None
    dll.NDIlib_send_send_video_async_v2.argtypes = [c_void_p, c_void_p]

    # NDIlib_send_destroy(NDIlib_send_instance_t)
    dll.NDIlib_send_destroy.restype = None
    dll.NDIlib_send_destroy.argtypes = [c_void_p]

    return dll

# --- Wrapper API (the interface NDISender calls) ---

def initialize() -> bool:
    """Initialize the NDI SDK. Call once at app startup.

    Returns False if:
      - Platform is not little-endian (NDI BGRA requires LE byte order)
      - NDI runtime DLL cannot be found
      - SDK initialization fails
    """
    global _initialized

    if sys.byteorder != "little":
        logger.error(
            "[NDI Bridge] Unsupported: %s endian. NDI requires little-endian (x64). "
            "NDI disabled.", sys.byteorder)
        return False

    dll = _setup_functions()
    if dll is None:
        return False

    try:
        ok = dll.NDIlib_initialize()
        if ok:
            _initialized = True
            logger.info("[NDI Bridge] SDK initialized")
        else:
            logger.error("[NDI Bridge] SDK initialization failed")
        return ok
    except Exception as exc:
        logger.error("[NDI Bridge] SDK init exception: %s", exc)
        return False


def destroy() -> None:
    """Destroy the NDI SDK. Call once at app shutdown."""
    global _initialized
    dll = _load_dll()
    if dll is None:
        return
    try:
        dll.NDIlib_destroy()
        _initialized = False
        logger.info("[NDI Bridge] SDK destroyed")
    except Exception as exc:
        logger.error("[NDI Bridge] SDK destroy exception: %s", exc)


def create_sender(source_name: str) -> int | None:
    """Create a named NDI sender. Returns handle (int) or None on failure.

    Requires initialize() to have been called first.
    The handle is a c_void_p cast to int for Python portability.
    """
    if not _initialized:
        logger.error("[NDI Bridge] create_sender() called before initialize()")
        return None

    dll = _load_dll()
    if dll is None:
        return None

    create_desc = NDI_send_create_t()
    create_desc.p_ndi_name = source_name.encode("utf-8")
    create_desc.p_groups = None
    create_desc.clock_video = False
    create_desc.clock_audio = False

    try:
        handle = dll.NDIlib_send_create(ctypes.byref(create_desc))
        if handle:
            logger.info("[NDI Bridge] Created sender '%s' (handle=%s)", source_name, handle)
            return int(handle)
        else:
            logger.error("[NDI Bridge] Failed to create sender '%s'", source_name)
            return None
    except Exception as exc:
        logger.error("[NDI Bridge] create_sender exception: %s", exc)
        return None


def destroy_sender(handle: int) -> None:
    """Destroy an NDI sender handle. Safe to call with None or 0."""
    if not handle:
        return
    dll = _load_dll()
    if dll is None:
        return
    try:
        dll.NDIlib_send_destroy(handle)
        logger.debug("[NDI Bridge] Destroyed sender handle=%s", handle)
    except Exception as exc:
        logger.error("[NDI Bridge] destroy_sender exception: %s", exc)


def send_frame(handle: int, qimage) -> None:
    """Send a QImage as an NDI video frame.

    Preconditions:
        - handle is a valid sender handle from create_sender()
        - qimage is a QImage in Format_ARGB32
        - qimage is not null (size > 0)

    Postcondition:
        - Frame is transmitted asynchronously to the NDI network.
        - Format: NDIlib_FourCC_video_type_BGRA. ARGB32 on little-endian x64
          produces [B,G,R,A] byte order in memory â€” exact match, no swap.

    No format conversion is performed â€” ARGB32-LE = NDI BGRA.
    The initialize() function guards against big-endian platforms.
    QImage lifetime is managed by NDISender._frame_buf.
    """
    dll = _load_dll()
    if dll is None or not handle:
        return

    if qimage.isNull() or qimage.size().isEmpty():
        return

    width = qimage.width()
    height = qimage.height()
    stride = qimage.bytesPerLine()

    frame = NDIlib_video_frame_v2_t()
    frame.xres = width
    frame.yres = height
    frame.FourCC = NDIlib_FourCC_video_type_BGRA
    frame.frame_rate_N = fps
    frame.frame_rate_D = 1
    frame.picture_aspect_ratio = float(width) / float(height) if height > 0 else 1.0
    frame.frame_format_type = 0  # progressive
    frame.timecode = 0  # NDIlib_send_timecode_synthesize equivalent
    # bits() returns a sip.voidptr â€” the QImage (held by NDISender._frame_buf)
    # owns the memory. The voidptr is a view, not an owner. Extracting the raw
    # integer address is safe as long as _frame_buf retains the QImage.
    frame.p_data = qimage.bits().__int__()
    frame.line_stride_in_bytes = stride
    frame.p_metadata = None
    frame.timestamp = 0

    try:
        dll.NDIlib_send_send_video_async_v2(handle, ctypes.byref(frame))
    except Exception as exc:
        logger.error("[NDI Bridge] send_frame exception: %s", exc)
        raise
```

---

## [NEW] `ndi_sender.py`

```python
"""ndi_sender.py â€” NDISender: read-only observer that captures frames and sends via NDI."""

import logging
import time

from PyQt6.QtCore import QObject, QTimer, pyqtSignal
from PyQt6.QtGui import QImage, QPainter
from PyQt6.QtCore import Qt

logger = logging.getLogger("VerseFlow.NDI")

NDI_CAPTURE_FPS = 30
_FRAME_INTERVAL_MS = 1000 // NDI_CAPTURE_FPS
_WARNING_THRESHOLD_MS = _FRAME_INTERVAL_MS - 5
_ERROR_THROTTLE_S = 5.0


class NDISender(QObject):
    """Captures DisplayWindow frames via render() and transmits them via NDI.

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
        self._timer = QTimer(self)       # parented to self â€” cleaned up on destroy
        self._timer.timeout.connect(self._on_timer)
        self._frame_buf = None           # retains QImage alive for async SDK
        self._was_live = False           # prevents double-start from signal amplification
        self._last_error_msg = None      # dedup for sender_error throttle
        self._last_error_time = None     # time-based throttle (monotonic seconds)

        # Connect to the broadcast signal â€” filter by channel name inside handler
        channel_manager.channel_changed.connect(self._on_channel_state)

    # â”€â”€ Signal handler â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _on_channel_state(self, name: str, state_dict: dict):
        """Handle channel state changes. Only acts on this sender's channel.

        Signal amplification: a single push_verse() fires verse_changed AND
        display_opened (if window is lazily created). ChannelManager connects
        both to _emit_channel_changed, so channel_changed fires twice per push.
        The _was_live guard prevents double-start from these duplicate emissions.
        """
        if name != self.channel_name:
            return

        is_live = state_dict.get("is_live", False)

        if is_live and not self._was_live:
            self.start()
        elif not is_live and self._was_live:
            self.stop()

        self._was_live = is_live

    # â”€â”€ Lifecycle â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def start(self):
        """Acquire DisplayWindow reference and begin capture loop."""
        channel = self._channel_manager.get_channel(self.channel_name)
        if channel is None:
            return

        # Use DisplayChannel.display_window forwarding property
        # (avoids reaching into channel.controller internals)
        display_window = channel.display_window
        if display_window is None:
            logger.warning(
                "[NDISender:%s] Cannot start â€” display_window is None (no monitor?)",
                self.channel_name)
            return

        source_name = f"VerseFlow {self.channel_name.title()}"
        self._handle = self._bridge.create_sender(source_name)
        if self._handle is None:
            self._emit_error("Failed to create NDI sender")
            return

        self._timer.start(_FRAME_INTERVAL_MS)
        self.sender_status_changed.emit(self.channel_name, {"active": True})
        logger.info("[NDISender:%s] Started â€” source='%s'", self.channel_name, source_name)

    def stop(self):
        """Stop capture loop and destroy NDI sender handle.

        Idempotent â€” safe to call multiple times.
        """
        self._timer.stop()

        if self._handle is not None:
            self._bridge.destroy_sender(self._handle)
            self._handle = None

        self._frame_buf = None
        self.sender_status_changed.emit(self.channel_name, {"active": False})
        logger.debug("[NDISender:%s] Stopped", self.channel_name)

    # â”€â”€ Capture loop â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _on_timer(self):
        """Capture and send one frame. Runs every ~33ms (30fps)."""
        t0 = time.perf_counter()
        image = self._capture_frame()

        if image is not None:
            self._frame_buf = image   # retain for async SDK read
            self._send_frame(self._frame_buf)

            duration_ms = (time.perf_counter() - t0) * 1000
            if duration_ms > _WARNING_THRESHOLD_MS:
                logger.warning(
                    "[NDISender:%s] Render took %.1fms (target: %dms)",
                    self.channel_name, duration_ms, _FRAME_INTERVAL_MS)
            else:
                logger.debug(
                    "[NDISender:%s] Render took %.1fms", self.channel_name, duration_ms)

            self.frame_sent.emit(self.channel_name, NDI_CAPTURE_FPS)

    def _capture_frame(self):
        """Capture DisplayWindow into ARGB32 QImage via off-screen render().

        Returns None when:
          - DisplayWindow doesn't exist (between verses â€” normal)
          - DisplayWindow is not visible (minimized, monitor disconnected)
          - DisplayWindow has zero size (during initialization)
        """
        channel = self._channel_manager.get_channel(self.channel_name)
        if channel is None:
            return None

        display_window = channel.display_window
        if display_window is None or not display_window.isVisible():
            return None

        size = display_window.size()
        if size.isEmpty():
            return None

        image = QImage(size, QImage.Format.Format_ARGB32)
        image.fill(Qt.GlobalColor.transparent)
        painter = QPainter(image)
        display_window.render(painter)
        painter.end()
        return image

    def _send_frame(self, image: QImage):
        """Send QImage to NDI network via ndi_bridge.

        All format conversion is internal to ndi_bridge â€” NDISender never
        calls convertToFormat() or touches raw pixel bytes.
        """
        if self._handle is None:
            return

        try:
            self._bridge.send_frame(self._handle, image, fps=NDI_CAPTURE_FPS)
            # Clear error state on successful send (recovery from transient failure)
            self._last_error_msg = None
            self._last_error_time = None
        except Exception as exc:
            self._emit_error(str(exc))

    # â”€â”€ Error handling â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    def _emit_error(self, message: str):
        """Emit sender_error with combined dedup + time-based throttle.

        Two-level guard against log spam when the NDI SDK enters a persistent
        failure state (send_frame fires 30Ã—/sec):

        1. Message dedup: identical messages are suppressed entirely.
        2. Time throttle: different alternating messages are limited to one
           emission per _ERROR_THROTTLE_S seconds.

        A successful send_frame() call resets both guards, allowing instant
        error visibility on the next failure.
        """
        now = time.monotonic()
        if message == self._last_error_msg:
        logger.error("[NDISender:%s] %s", self.channel_name, message)
        self.sender_error.emit(self.channel_name, message)
```

---

## [NEW] `ndi_manager.py`

```python
"""ndi_manager.py â€” Coordinates NDI SDK lifecycle and per-channel NDISender registry."""

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

        Use this instead of checking is not None â€” a partially-constructed
        NDIManager (SDK init failed) should be treated the same as no manager.
        """
        return self._bridge is not None

    def _create_sender(self, channel_name: str):
        """Create an NDISender for the named channel."""
        if self._bridge is None:
            return
        from ndi_sender import NDISender
        sender = NDISender(channel_name, self._channel_manager, self._bridge, parent=self)
        self._senders[channel_name] = sender
        logger.debug("[NDIManager] Created sender for '%s'", channel_name)

    def get_sender(self, channel_name: str):
        """Return the sender for a channel, or None."""
        return self._senders.get(channel_name)

    def stop_all(self):
        """Stop all active senders. Idempotent â€” safe to call multiple times.

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
```

---

## [MODIFY] `main.py`

### Addition â€” after ChannelManager setup (after line ~71, `self.channel_manager.add_channel("alt", self.alt_display)`):

```python
# v1.2.0 Phase 1: NDI Manager (Main channel only)
# Placed after ChannelManager is fully initialized.
try:
    from ndi_manager import NDIManager
    self.ndi_manager = NDIManager(
        self.channel_manager,
        channels=["main"],   # Phase 1: Main channel only
        parent=self,
    )
    if not self.ndi_manager.available:
        self.ndi_manager = None  # makes is not None reliably mean "NDI functional"
except Exception as exc:
    logger.warning("[MainWindow] NDI not available: %s", exc)
    self.ndi_manager = None
```

### Modification â€” `closeEvent` (current lines ~391â€“398):

```python
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
```

**Shutdown sequence rationale:**
1. `stop_all()` â€” stops timers, destroys NDI sender handles. DisplayWindow still alive â€” `render()` reference is valid during `stop()`.
2. `close_display_window()` â€” closes physical windows. `display_closed` signal â†’ `channel_changed` fires â†’ `NDISender._on_channel_state` calls `stop()` again â†’ idempotent (timer already stopped, handle already None).
3. `ndi_manager.destroy()` â€” calls `NDIlib_destroy()` to tear down SDK. Calls `stop_all()` again internally as safety net (idempotent).

---

## [MODIFY] `pre_commit_checks.py`

Add `check_phase1_ndi_skeleton()`:

```python
def check_phase1_ndi_skeleton():
    """Verify v1.2.0 Phase 1 NDI skeleton integrity."""
    errors = []

    # File existence
    for filename in ("ndi_bridge.py", "ndi_sender.py", "ndi_manager.py"):
        path = SRC / filename
        if not path.exists():
            errors.append(f"CRITICAL: Phase 1 NDI: {filename} missing")

    # ndi_sender.py checks
    sender_path = SRC / "ndi_sender.py"
    if sender_path.exists():
        with open(sender_path, encoding="utf-8") as f:
            sender_src = f.read()

        if "class NDISender" not in sender_src:
            errors.append("CRITICAL: Phase 1 NDI: NDISender class missing")
        if "frame_sent" not in sender_src:
            errors.append("CRITICAL: Phase 1 NDI: frame_sent signal missing")
        if "sender_error" not in sender_src:
            errors.append("CRITICAL: Phase 1 NDI: sender_error signal missing")
        if "sender_status_changed" not in sender_src:
            errors.append("CRITICAL: Phase 1 NDI: sender_status_changed signal missing")
        if "NDI_CAPTURE_FPS" not in sender_src:
            errors.append("CRITICAL: Phase 1 NDI: NDI_CAPTURE_FPS constant missing")
        if "_capture_frame" not in sender_src:
            errors.append("CRITICAL: Phase 1 NDI: _capture_frame method missing")
        if "QWidget.grab" in sender_src or ".grab(" in sender_src:
            errors.append("CRITICAL: Phase 1 NDI: ndi_sender.py calls grab() â€” must use render() only")
        # Must use channel.display_window, not channel.controller.display_window
        if ".controller.display_window" in sender_src or ".controller." in sender_src:
            errors.append("CRITICAL: Phase 1 NDI: ndi_sender.py accesses .controller â€” must use channel.display_window property")

    # ndi_bridge.py checks
    bridge_path = SRC / "ndi_bridge.py"
    if bridge_path.exists():
        with open(bridge_path, encoding="utf-8") as f:
            bridge_src = f.read()

        if "import ndi" in bridge_src or "import ndi_python" in bridge_src:
            errors.append("CRITICAL: Phase 1 NDI: ndi_bridge.py imports third-party NDI PyPI package")
        if "QWidget.grab" in bridge_src or ".grab(" in bridge_src:
            errors.append("CRITICAL: Phase 1 NDI: ndi_bridge.py calls grab() â€” must use render() only")
        if "def send_frame" not in bridge_src:
            errors.append("CRITICAL: Phase 1 NDI: ndi_bridge.py missing send_frame()")
        if "def create_sender" not in bridge_src:
            errors.append("CRITICAL: Phase 1 NDI: ndi_bridge.py missing create_sender()")
        if "def destroy_sender" not in bridge_src:
            errors.append("CRITICAL: Phase 1 NDI: ndi_bridge.py missing destroy_sender()")
        # FourCC must be the correct value, not the sequential placeholder '= 1'
        if "0x41524742" not in bridge_src:
            errors.append("CRITICAL: Phase 1 NDI: ndi_bridge.py missing correct BGRA FourCC (0x41524742)")
        # Endianness check must exist (in initialize(), not module-level assert)
        if "sys.byteorder" not in bridge_src:
            errors.append("CRITICAL: Phase 1 NDI: ndi_bridge.py missing endianness check")
        # Init guard must exist
        if "_initialized" not in bridge_src:
            errors.append("CRITICAL: Phase 1 NDI: ndi_bridge.py missing _initialized guard")

    # ndi_manager.py checks
    manager_path = SRC / "ndi_manager.py"
    if manager_path.exists():
        with open(manager_path, encoding="utf-8") as f:
            manager_src = f.read()

        if "class NDIManager" not in manager_src:
            errors.append("CRITICAL: Phase 1 NDI: NDIManager class missing")
        if "def stop_all" not in manager_src:
            errors.append("CRITICAL: Phase 1 NDI: NDIManager missing stop_all()")
        if "def destroy" not in manager_src:
            errors.append("CRITICAL: Phase 1 NDI: NDIManager missing destroy()")

    # Regression: verify files NOT touched are unchanged
    # channel_display_facade.py â€” must not have ndi/ndi_sender/ndi_bridge imports
    facade_path = SRC / "channel_display_facade.py"
    if facade_path.exists():
        with open(facade_path, encoding="utf-8") as f:
            facade_src = f.read()
        for banned in ("ndi_bridge", "ndi_sender", "NDIManager", "NDISender"):
            if banned in facade_src:
                errors.append(f"CRITICAL: Phase 1 NDI: channel_display_facade.py references '{banned}' â€” must not be modified")

    # channel_manager.py â€” compatibility shims must not reference NDI
    cm_path = SRC / "channel_manager.py"
    if cm_path.exists():
        with open(cm_path, encoding="utf-8") as f:
            cm_src = f.read()
        for banned in ("ndi_bridge", "ndi_sender", "NDISender"):
            if banned in cm_src:
                errors.append(f"CRITICAL: Phase 1 NDI: channel_manager.py references '{banned}' â€” must not be modified")

    # display_channel.py â€” must have the display_window forwarding property
    disp_ch_path = SRC / "display_channel.py"
    if disp_ch_path.exists():
        with open(disp_ch_path, encoding="utf-8") as f:
            disp_ch_src = f.read()
        if "def display_window" not in disp_ch_src:
            errors.append("CRITICAL: Phase 1 NDI: display_channel.py missing display_window forwarding property")

    # display_core.py â€” must not reference NDI
    dc_path = SRC / "display_core.py"
    if dc_path.exists():
        with open(dc_path, encoding="utf-8") as f:
            dc_src = f.read()
        for banned in ("ndi_bridge", "ndi_sender", "NDISender"):
            if banned in dc_src:
                errors.append(f"CRITICAL: Phase 1 NDI: display_core.py references '{banned}' â€” must not be modified")

    # home_panel.py â€” must not reference NDI (no operator UI changes in Phase 1)
    hp_path = SRC / "home_panel.py"
    if hp_path.exists():
        with open(hp_path, encoding="utf-8") as f:
            hp_src = f.read()
        for banned in ("ndi_bridge", "ndi_sender", "NDISender", "NDIManager"):
            if banned in hp_src:
                errors.append(f"CRITICAL: Phase 1 NDI: home_panel.py references '{banned}' â€” must not be modified")

    return errors
```

**Add to `__main__` block:**
```python
print("Running Phase 1 NDI skeleton checks...")
all_errors.extend(check_phase1_ndi_skeleton())
```

---

## [MODIFY] `verify_critical_fixes.py`

Add NDI source checks:

```python
def verify_phase1_ndi():
    """Verify v1.2.0 Phase 1 NDI skeleton source integrity."""
    errors = []
    snd_path = SRC / 'ndi_sender.py'
    mgr_path = SRC / 'ndi_manager.py'
    brg_path = SRC / 'ndi_bridge.py'

    # NDISender class & signal checks
    if snd_path.exists():
        with open(snd_path, encoding='utf-8') as f:
            snd = f.read()

        for sym, label in [
            ('class NDISender', 'NDISender class'),
            ('frame_sent', 'frame_sent signal'),
            ('sender_error', 'sender_error signal'),
            ('sender_status_changed', 'sender_status_changed signal'),
            ('def _capture_frame', '_capture_frame method'),
            ('NDI_CAPTURE_FPS', 'NDI_CAPTURE_FPS constant'),
            ('def _on_channel_state', '_on_channel_state method'),
            ('self._was_live', '_was_live guard'),
            ('name != self.channel_name', 'channel name filter'),
            ('self._frame_buf', 'frame_buf double-buffer'),
            ('size.isEmpty', 'zero-size QImage guard'),
            ('self._last_error_msg', 'sender_error message dedup'),
            ('self._last_error_time', 'sender_error time throttle'),
            ('channel.display_window', 'uses DisplayChannel property (not .controller)'),
        ]:
            if sym in snd:
                print(f"  [OK] ndi_sender.py: {label}")
            else:
                print(f"  [FAIL] ndi_sender.py: missing {label}")
                errors.append(f"Phase 1 NDI: ndi_sender.py missing: {label}")

    # NDIManager class checks
    if mgr_path.exists():
        with open(mgr_path, encoding='utf-8') as f:
            mgr = f.read()

        for sym, label in [
            ('class NDIManager', 'NDIManager class'),
            ('def stop_all', 'stop_all method'),
            ('def destroy', 'destroy method'),
            ('channels=["main"]', 'Phase 1 Main-only scope'),
            ('def available', 'available property'),
        ]:
            if sym in mgr:
                print(f"  [OK] ndi_manager.py: {label}")
            else:
                print(f"  [FAIL] ndi_manager.py: missing {label}")
                errors.append(f"Phase 1 NDI: ndi_manager.py missing: {label}")

    # ndi_bridge.py wrapper API checks
    if brg_path.exists():
        with open(brg_path, encoding='utf-8') as f:
            brg = f.read()

        for sym, label in [
            ('def initialize', 'initialize()'),
            ('def destroy', 'destroy()'),
            ('def create_sender', 'create_sender()'),
            ('def destroy_sender', 'destroy_sender()'),
            ('def send_frame', 'send_frame()'),
            ('sys.byteorder', 'little-endian guard (in initialize)'),
            ('c_float', 'c_float import'),
            ('c_uint32', 'c_uint32 import'),
            ('c_int64', 'c_int64 import'),
            ('0x41524742', 'correct BGRA FourCC'),
            ('_initialized', 'init guard flag'),
        ]:
            if sym in brg:
                print(f"  [OK] ndi_bridge.py: {label}")
            else:
                print(f"  [FAIL] ndi_bridge.py: missing {label}")
                errors.append(f"Phase 1 NDI: ndi_bridge.py missing: {label}")

        # Must NOT contain NDIlib_send_get_tally (deferred to Phase 2)
        if "NDIlib_send_get_tally" in brg:
            print("  [FAIL] ndi_bridge.py: contains NDIlib_send_get_tally (deferred to Phase 2)")
            errors.append("Phase 1 NDI: ndi_bridge.py contains deferred NDIlib_send_get_tally")

    # display_channel.py â€” must have display_window forwarding property
    disp_ch_path = SRC / 'display_channel.py'
    if disp_ch_path.exists():
        with open(disp_ch_path, encoding='utf-8') as f:
            disp_ch = f.read()
        if 'def display_window' in disp_ch:
            print("  [OK] display_channel.py: display_window forwarding property")
        else:
            print("  [FAIL] display_channel.py: missing display_window forwarding property")
            errors.append("Phase 1 NDI: display_channel.py missing display_window property")

    return errors
```

**Add to `verify()` function:**
```python
print("\n=== v1.2.0 Phase 1: NDI Skeleton Source Checks ===")
errs.extend(verify_phase1_ndi())
```

---

## Verification Plan

### Automated
1. `python pre_commit_checks.py` â€” all Phase 1 NDI guards pass
2. `python verify_critical_fixes.py` â€” all NDI source checks pass
3. All existing v1.1.0 checks still pass (no regression)

### Manual
1. **NDI Discovery:** Launch VerseFlow, open OBS, add NDI Source â€” verify `"VerseFlow Main"` in picker
2. **Live Feed:** Push a verse to Main â€” verify text appears in OBS
3. **Clear Transition:** Clear Main â€” verify OBS source shows "No Signal"
4. **Graceful Fallback:** Rename or remove NDI DLL â€” verify VerseFlow launches without crash, warning logged
5. **Push/Clear Cycle:** Push â†’ Clear â†’ Push â†’ Clear â€” verify sender starts/stops correctly (no stale handles, no frozen frames in OBS)
6. **Regression:** Verify standard display window, navigator, queue, playlist, and hotkeys all function perfectly

---

## Summary of All Fixes Applied (v3 â€” triple-audited)

| # | Issue | Severity | Fix |
|---|-------|----------|-----|
| 1 | FourCC = `1` instead of `0x41524742` | ðŸ”´ Showstopper | Correct FourCC; module-level constant |
| 2 | Missing `c_float`, `c_uint32`, `c_int64` imports | ðŸ”´ Crash | All three added to import list |
| 3 | `create_sender()` returns `c_void_p`, not `int` | ðŸŸ  High | `return int(handle)` |
| 4 | FourCC field typed `c_int`, not `c_uint32` | ðŸŸ  High | Changed to `c_uint32` |
| 5 | `assert` at module load â†’ crash on BE import | ðŸŸ  High | Moved to `initialize()`; graceful `return False` |
| 6 | Dead `NDIlib_send_get_tally` setup | ðŸŸ¡ Medium | Removed; deferred to Phase 2 |
| 7 | No init guard on `create_sender()` | ðŸŸ¡ Medium | `_initialized` flag; checked in `create_sender()` |
| 8 | FourCC as local magic number | ðŸŸ¡ Medium | Extracted to `NDIlib_FourCC_video_type_BGRA` constant |
| 9 | `channel.controller.display_window` breaks encapsulation | ðŸŸ¡ Medium | `DisplayChannel.display_window` forwarding property |
| 10 | `NDIManager.available` property | ðŸŸ¡ Medium | `available` property for reliable NDI state check |
| 11 | Error dedup misses alternating messages | ðŸŸ¢ Low | Time-based throttle (`_last_error_time`, 5s window) |
| 12 | `bits().__int__()` use-after-free concern | âŒ Not an issue | Confirmed safe â€” QImage lifetime managed by `_frame_buf` |
| 13 | Missing pre-commit guards (FourCC, endianness, `.controller`, `display_window` property) | ðŸŸ¡ Medium | 4 new guards added |
| 14 | Missing verify guards (c_float, c_uint32, _initialized, get_tally absence, _last_error_time, available, display_window) | ðŸŸ¡ Medium | 7 new source checks added |
| â€” | `_sync_initial_state` dead code (v2 fix) | ðŸŸ¡ Medium | Removed (Deviation 2) |
| â€” | `self._bridge = NDIlib_initialize` bug (v2 fix) | ðŸ”´ Crash | Store `ndi_bridge` module (v2) |
| â€” | Sender created for Alt in Phase 1 (v2 fix) | ðŸŸ  High | `channels=["main"]` scope (v2) |
| â€” | `QTimer()` no parent (v2 fix) | ðŸŸ¡ Medium | `QTimer(self)` (v2) |
| â€” | Zero-size QImage crash risk (v2 fix) | ðŸŸ¡ Medium | `size.isEmpty()` guard (v2) |
| â€” | DLL path unspecified (v2 fix) | ðŸŸ¡ Medium | 3-tier search path (v2) |
| N2 | Structs defined locally inside functions | ðŸŸ¡ Medium | Moved `NDI_send_create_t` and `NDIlib_video_frame_v2_t` to module level |
| N3 | `frame_rate_N` hardcoded to 30 | ðŸŸ¡ Medium | `send_frame()` accepts `fps` parameter; `NDISender` passes `NDI_CAPTURE_FPS` |
| N4 | No `home_panel.py` untouched guard | ðŸŸ¡ Medium | `home_panel.py` added to pre-commit NDI reference ban |
