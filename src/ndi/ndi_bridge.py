# ndi_bridge.py — ctypes wrapper over Processing.NDI.Lib.x64.dll
#
# Self-contained ctypes wrapper over the NDI C SDK. No PyPI dependencies.
# All format handling is internal to this module — NDISender never touches
# raw bytes or calls convertToFormat().

import ctypes
import logging
import os
import sys
from ctypes import (
    c_bool, c_char_p, c_float, c_int, c_int64, c_uint32, c_void_p,
    POINTER, Structure,
)

logger = logging.getLogger("VerseFlow.NDI")

# Per-sender frame struct retention — the NDI SDK is asynchronous and
# reads from the frame struct after send_frame() returns. Dropping the
# struct would free the C memory the SDK is actively reading. This dict
# keeps each sender's most-recent frame struct alive until its next call.
_frame_cache = {}

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


# --- NDI SDK struct definitions (module-level, not per-call) ---

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


# --- NDI SDK function signatures ---

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

    # NDIlib_send_send_video_v2(NDIlib_send_instance_t, NDIlib_video_frame_v2_t*)  — sync
    dll.NDIlib_send_send_video_v2.restype = None
    dll.NDIlib_send_send_video_v2.argtypes = [c_void_p, c_void_p]

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
        _frame_cache.pop(handle, None)  # release retained frame struct
        logger.debug("[NDI Bridge] Destroyed sender handle=%s", handle)
    except Exception as exc:
        logger.error("[NDI Bridge] destroy_sender exception: %s", exc)


def send_frame(handle: int, qimage, fps: int = 30) -> None:
    """Send a QImage as an NDI video frame.

    Preconditions:
        - handle is a valid sender handle from create_sender()
        - qimage is a QImage in Format_ARGB32
        - qimage is not null (size > 0)

    Postcondition:
        - Frame is transmitted asynchronously to the NDI network.
        - Format: NDIlib_FourCC_video_type_BGRA. ARGB32 on little-endian x64
          produces [B,G,R,A] byte order in memory — exact match, no swap.

    No format conversion is performed — ARGB32-LE = NDI BGRA.
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
    frame.timecode = 9223372036854775807  # NDIlib_send_timecode_synthesize
    # bits() returns a sip.voidptr — the QImage (held by NDISender._frame_buf)
    # owns the memory. The voidptr is a view, not an owner. Extracting the raw
    # integer address is safe as long as _frame_buf retains the QImage.
    frame.p_data = qimage.bits().__int__()
    frame.line_stride_in_bytes = stride
    frame.p_metadata = None
    frame.timestamp = 0

    # Retain frame struct so the NDI SDK's background encoder thread
    # doesn't read freed memory. Overwritten on the next send_frame()
    # call for the same handle — the SDK guarantees it's done with the
    # previous frame by then.
    _frame_cache[handle] = frame

    try:
        dll.NDIlib_send_send_video_async_v2(handle, ctypes.byref(frame))
    except Exception as exc:
        logger.error("[NDI Bridge] send_frame exception: %s", exc)
        raise


def send_frame_sync(handle: int, qimage, fps: int = 30) -> None:
    """Send a QImage as an NDI video frame synchronously.

    Blocks until the frame is fully transmitted. Use only for teardown
    frames (black frame on stop) where the sender handle is about to be
    destroyed — the sync call ensures the receiver sees the frame before
    the handle goes away.

    Preconditions:
        - handle is a valid sender handle from create_sender()
        - qimage is a QImage in Format_ARGB32
        - qimage is not null (size > 0)

    Postcondition:
        - Frame is transmitted synchronously to the NDI network.
        - Frame struct is NOT cached (sync call is blocking, no background thread).
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
    frame.timecode = 9223372036854775807  # NDIlib_send_timecode_synthesize
    frame.p_data = qimage.bits().__int__()
    frame.line_stride_in_bytes = stride
    frame.p_metadata = None
    frame.timestamp = 0

    try:
        dll.NDIlib_send_send_video_v2(handle, ctypes.byref(frame))
    except Exception as exc:
        logger.error("[NDI Bridge] send_frame_sync exception: %s", exc)
        raise
