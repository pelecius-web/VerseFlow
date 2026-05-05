"""hotkey_manager.py - Global hotkey coordination for VerseFlow.

Stage 2 introduces the public manager facade and backend contract without
binding any native OS hotkey APIs yet. The module is intentionally safe to
import on every platform so the app can wire it in gradually.
"""

import logging
import sys
import ctypes
from dataclasses import dataclass
from ctypes import wintypes
from typing import Callable, Dict, Optional, Tuple

from PyQt6.QtCore import QObject, pyqtSignal, QAbstractNativeEventFilter
from PyQt6.QtWidgets import QApplication

logger = logging.getLogger("VerseFlow")


Callback = Callable[[], None]


@dataclass
class HotkeyBinding:
    """In-memory description of a registered hotkey action."""

    action_name: str
    shortcut: str
    callback: Callback
    backend_id: Optional[int] = None


class HotkeyBackendBase:
    """Common backend interface used by the hotkey manager."""

    def available(self) -> bool:
        return False

    def start(self) -> bool:
        return False

    def stop(self) -> None:
        return None

    def register_hotkey(self, action_name: str, shortcut: str) -> bool:
        return False

    def unregister_all(self) -> None:
        return None

    def status_summary(self) -> str:
        return "Unavailable"


class NullHotkeyBackend(HotkeyBackendBase):
    """Safe no-op backend used on unsupported platforms."""

    def available(self) -> bool:
        return False

    def start(self) -> bool:
        return False

    def register_hotkey(self, action_name: str, shortcut: str) -> bool:
        return False

    def status_summary(self) -> str:
        return "Global hotkeys are unavailable on this platform"


class _WindowsHotkeyEventFilter(QAbstractNativeEventFilter):
    """Native event bridge that listens for WM_HOTKEY."""

    WM_HOTKEY = 0x0312

    def __init__(self, on_hotkey_id: Callable[[int], None]):
        super().__init__()
        self._on_hotkey_id = on_hotkey_id

    def nativeEventFilter(self, event_type, message):
        # Handle QByteArray from PyQt6 - convert to bytes then decode
        if hasattr(event_type, "data"):
            # QByteArray has data() method
            event_name = event_type.data().decode("utf-8", errors="ignore")
        elif isinstance(event_type, (bytes, bytearray)):
            event_name = event_type.decode("utf-8", errors="ignore")
        else:
            event_name = str(event_type)

        if event_name not in ("windows_generic_MSG", "windows_dispatcher_MSG"):
            return False, 0

        msg = wintypes.MSG.from_address(int(message))
        if msg.message != self.WM_HOTKEY:
            return False, 0

        hotkey_id = int(msg.wParam)
        self._on_hotkey_id(hotkey_id)
        return True, 0


class WindowsHotkeyBackend(HotkeyBackendBase):
    """Windows backend using native RegisterHotKey / UnregisterHotKey."""

    MOD_ALT = 0x0001
    MOD_CONTROL = 0x0002
    MOD_SHIFT = 0x0004
    MOD_WIN = 0x0008

    # Windows error codes for hotkey registration
    ERROR_HOTKEY_ALREADY_REGISTERED = 1409
    ERROR_HOTKEY_NOT_REGISTERED = 1419

    def __init__(self, on_hotkey_action: Callable[[str], None]):
        self._started = False
        self._on_hotkey_action = on_hotkey_action
        self._registrations: Dict[str, str] = {}
        self._action_to_id: Dict[str, int] = {}
        self._id_to_action: Dict[int, str] = {}
        self._next_hotkey_id = 1
        self._failures = []
        self._event_filter = None
        self._app = None
        self._user32 = None
        self._kernel32 = None

        if self.available():
            self._user32 = ctypes.windll.user32
            self._user32.RegisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT]
            self._user32.RegisterHotKey.restype = wintypes.BOOL
            self._user32.UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]
            self._user32.UnregisterHotKey.restype = wintypes.BOOL
            self._kernel32 = ctypes.windll.kernel32
            self._kernel32.GetLastError.argtypes = []
            self._kernel32.GetLastError.restype = wintypes.DWORD

    def available(self) -> bool:
        return sys.platform.startswith("win")

    def start(self) -> bool:
        if not self.available() or self._user32 is None:
            self._started = False
            return False

        self._failures.clear()
        self._app = QApplication.instance()
        if self._app is None:
            self._started = False
            self._failures.append("No QApplication instance is running")
            return False

        if self._event_filter is None:
            self._event_filter = _WindowsHotkeyEventFilter(self._on_hotkey_id)
            self._app.installNativeEventFilter(self._event_filter)

        self._started = True
        return True

    def stop(self) -> None:
        if self._started:
            self.unregister_all()
        if self._app is not None and self._event_filter is not None:
            self._app.removeNativeEventFilter(self._event_filter)
        self._event_filter = None
        self._app = None
        self._started = False

    def register_hotkey(self, action_name: str, shortcut: str) -> bool:
        if not self._started:
            return False
        parsed = self._parse_shortcut(shortcut)
        if parsed is None:
            self._failures.append(f"Invalid hotkey '{shortcut}' for action '{action_name}'")
            return False

        # Rebind existing actions in place so reconfiguration does not leave
        # stale global registrations behind.
        if action_name in self._action_to_id:
            old_id = self._action_to_id[action_name]
            if self._user32 is not None:
                self._user32.UnregisterHotKey(None, old_id)
            self._action_to_id.pop(action_name, None)
            self._id_to_action.pop(old_id, None)
            self._registrations.pop(action_name, None)

        modifiers, vk_code = parsed
        hotkey_id = self._next_hotkey_id
        self._next_hotkey_id += 1

        ok = bool(self._user32.RegisterHotKey(None, hotkey_id, modifiers, vk_code))
        if not ok:
            error_code = self._kernel32.GetLastError() if self._kernel32 else 0
            error_msg = self._format_error_code(error_code)
            self._failures.append(f"RegisterHotKey failed for '{action_name}' ({shortcut}): {error_msg}")
            logger.warning("[HOTKEYS] RegisterHotKey failed for '%s' (0x%X): %s", action_name, error_code, error_msg)
            return False

        self._registrations[action_name] = shortcut
        self._action_to_id[action_name] = hotkey_id
        self._id_to_action[hotkey_id] = action_name
        logger.info("[HOTKEYS] Registered hotkey '%s' (%s) with ID %d", action_name, shortcut, hotkey_id)
        return True

    def _format_error_code(self, error_code: int) -> str:
        """Format Windows error code to human-readable message."""
        if error_code == 0:
            return "No error information available"
        if error_code == self.ERROR_HOTKEY_ALREADY_REGISTERED:
            return f"Hotkey already registered by another application (error {error_code})"
        if error_code == self.ERROR_HOTKEY_NOT_REGISTERED:
            return f"Hotkey not registered (error {error_code})"
        return f"Windows error code {error_code}"

    def unregister_all(self) -> None:
        if self._user32 is not None:
            for hotkey_id in list(self._id_to_action.keys()):
                self._user32.UnregisterHotKey(None, hotkey_id)
        self._registrations.clear()
        self._action_to_id.clear()
        self._id_to_action.clear()

    def status_summary(self) -> str:
        if not self._started:
            if self._failures:
                return self._failures[-1]
            return "Windows global hotkeys are not started"
        if self._failures:
            return self._failures[-1]
        return f"Windows global hotkeys active ({len(self._registrations)} registered)"

    def _parse_shortcut(self, shortcut: str) -> Optional[Tuple[int, int]]:
        parts = [part.strip() for part in shortcut.split("+") if part.strip()]
        if len(parts) < 2:
            return None

        modifiers = 0
        key_token = parts[-1].upper()

        for mod in parts[:-1]:
            mod_upper = mod.upper()
            if mod_upper in ("CTRL", "CONTROL"):
                modifiers |= self.MOD_CONTROL
            elif mod_upper == "ALT":
                modifiers |= self.MOD_ALT
            elif mod_upper == "SHIFT":
                modifiers |= self.MOD_SHIFT
            elif mod_upper in ("WIN", "META"):
                modifiers |= self.MOD_WIN
            else:
                return None

        if modifiers == 0:
            return None

        vk_code = self._parse_vk_code(key_token)
        if vk_code is None:
            return None
        return modifiers, vk_code

    def _parse_vk_code(self, key_token: str) -> Optional[int]:
        if len(key_token) == 1 and key_token.isalpha():
            return ord(key_token)
        if len(key_token) == 1 and key_token.isdigit():
            return ord(key_token)
        if key_token.startswith("F") and key_token[1:].isdigit():
            fn = int(key_token[1:])
            if 1 <= fn <= 24:
                return 0x70 + fn - 1

        special = {
            "SPACE": 0x20,
            "TAB": 0x09,
            "ENTER": 0x0D,
            "RETURN": 0x0D,
            "ESC": 0x1B,
            "ESCAPE": 0x1B,
            "UP": 0x26,
            "DOWN": 0x28,
            "LEFT": 0x25,
            "RIGHT": 0x27,
            "DELETE": 0x2E,
            "BACKSPACE": 0x08,
        }
        return special.get(key_token)

    def _on_hotkey_id(self, hotkey_id: int) -> None:
        action_name = self._id_to_action.get(hotkey_id)
        if action_name:
            self._on_hotkey_action(action_name)


class HotkeyManager(QObject):
    """Owns hotkey bindings and dispatches triggers to app callbacks."""

    hotkey_triggered = pyqtSignal(str)
    status = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._bindings: Dict[str, HotkeyBinding] = {}
        self._backend = self._select_backend()
        self._started = False
        self._using_fallback = False
        self._fallback_shortcuts: Dict[str, object] = {}

    def _select_backend(self) -> HotkeyBackendBase:
        if sys.platform.startswith("win"):
            return WindowsHotkeyBackend(self._on_backend_hotkey)
        return NullHotkeyBackend()

    def register_action(self, action_name: str, shortcut: str, callback: Callback) -> bool:
        """Register an action and remember its callback.

        Stage 2 only stores the binding and delegates registration to the
        selected backend when it becomes available.
        """

        action_name = (action_name or "").strip()
        shortcut = (shortcut or "").strip()
        if not action_name or not shortcut or not callable(callback):
            return False

        self._bindings[action_name] = HotkeyBinding(
            action_name=action_name,
            shortcut=shortcut,
            callback=callback,
        )

        if self._started:
            ok = self._backend.register_hotkey(action_name, shortcut)
            if not ok:
                logger.warning("[HOTKEYS] Action '%s' could not be registered", action_name)
                self.status.emit(f"Hotkey '{action_name}' could not be registered yet")
            return ok
        return True

    def trigger_action(self, action_name: str) -> bool:
        """Invoke a registered callback directly.

        This is useful for future backend event dispatch and for unit-level
        verification of the manager contract.
        """

        binding = self._bindings.get(action_name)
        if binding is None:
            return False

        try:
            binding.callback()
            self.hotkey_triggered.emit(action_name)
            return True
        except Exception as exc:
            self.status.emit(f"Hotkey action '{action_name}' failed: {exc}")
            return False

    def _on_backend_hotkey(self, action_name: str) -> None:
        self.trigger_action(action_name)

    def start(self, parent_widget=None) -> bool:
        if self._started:
            return True
        started = self._backend.start()
        self._started = started
        if started:
            failed = []
            for binding in self._bindings.values():
                ok = self._backend.register_hotkey(binding.action_name, binding.shortcut)
                if not ok:
                    failed.append(f"{binding.action_name} ({binding.shortcut})")
            if failed:
                # Roll back any partial registration so the next start attempt can retry cleanly.
                self._backend.stop()
                self._started = False
                details = ", ".join(failed)
                logger.warning("[HOTKEYS] Global hotkey registration failed for: %s", details)
                self.status.emit(f"Global hotkey registration failed for: {details}")
                # Enable fallback QShortcuts if global hotkeys fail
                if parent_widget:
                    self._enable_fallback_shortcuts(parent_widget)
                    self.status.emit("Using fallback hotkeys (app must be focused)")
                    return True
                return False
        if not started:
            self.status.emit(self._backend.status_summary())
            # Enable fallback if backend is not available
            if parent_widget and not self._backend.available():
                self._enable_fallback_shortcuts(parent_widget)
                self.status.emit("Using fallback hotkeys (app must be focused)")
                return True
        return started

    def stop(self) -> None:
        self._backend.stop()
        self._started = False

    def available(self) -> bool:
        return self._backend.available()

    def status_summary(self) -> str:
        return self._backend.status_summary()

    def unregister_all(self) -> None:
        self._backend.unregister_all()
        self._bindings.clear()
        self._fallback_shortcuts.clear()
        self._using_fallback = False

    def _enable_fallback_shortcuts(self, parent_widget):
        """Register QShortcuts as fallback if global hotkeys fail."""
        from PyQt6.QtGui import QShortcut, QKeySequence

        self._fallback_shortcuts = {}
        for action_name, binding in self._bindings.items():
            sc = QShortcut(QKeySequence(binding.shortcut), parent_widget)
            sc.activated.connect(binding.callback)
            self._fallback_shortcuts[action_name] = sc
        self._using_fallback = True
        logger.info("[HOTKEYS] Fallback QShortcuts enabled for %d actions", len(self._bindings))

    def get_diagnostics(self) -> dict:
        """Return current hotkey state for debugging."""
        backend_failures = getattr(self._backend, '_failures', [])
        return {
            "started": self._started,
            "backend_available": self._backend.available(),
            "backend_type": type(self._backend).__name__,
            "registrations_count": len(self._bindings),
            "registered_actions": list(self._bindings.keys()),
            "using_fallback": self._using_fallback,
            "fallback_count": len(self._fallback_shortcuts),
            "backend_failures": backend_failures.copy(),
        }

    def trigger_action_by_name(self, action_name: str) -> bool:
        """Manually trigger an action (for testing without hotkey)."""
        return self.trigger_action(action_name)
