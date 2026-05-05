"""settings.py - VerseFlow Settings Manager

Handles loading and saving application settings to JSON.
Includes display configuration, theme preferences, AI settings, and hotkeys.
"""

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from platformdirs import user_data_dir

logger = logging.getLogger("VerseFlow")

APP_NAME = "VerseFlow"
APP_AUTHOR = "VerseFlow"
SETTINGS_DIR = Path(user_data_dir(APP_NAME, APP_AUTHOR))
SETTINGS_FILE = SETTINGS_DIR / "settings.json"

HOTKEY_DEFAULTS = {
    "enabled": True,
    "focus_search": "Ctrl+Shift+L",
    "push_highlighted_verse": "Ctrl+Shift+V",
    "clear_live_display": "Ctrl+Shift+X",
    "add_highlighted_to_queue": "Ctrl+Shift+Q",
}

HOTKEY_ACTIONS = (
    "focus_search",
    "push_highlighted_verse",
    "clear_live_display",
    "add_highlighted_to_queue",
)

@dataclass
class ChannelSettings:
    """Per-channel display configuration.

    JSON shape follows sub-roadmap spec (nested lower_third, enabled flag).
    """
    enabled: bool = True
    mode: str = "fullscreen"  # "fullscreen" or "lower_third"
    theme_id: str = "default"  # stored as "theme" key in JSON
    monitor: Optional[int] = None  # None = auto-select
    logo_path: Optional[str] = None  # stored inside "lower_third" in JSON
    show_logo_placeholder: bool = True  # stored inside "lower_third" in JSON


HOTKEY_MODIFIERS = {"CTRL", "ALT", "SHIFT", "WIN"}
HOTKEY_SPECIAL_KEYS = {
    "SPACE",
    "TAB",
    "ENTER",
    "RETURN",
    "ESC",
    "ESCAPE",
    "UP",
    "DOWN",
    "LEFT",
    "RIGHT",
    "DELETE",
    "BACKSPACE",
}


class SettingsManager:
    """Manages application settings persistence."""

    def __init__(self, settings_path=None):
        self.settings_path = settings_path or SETTINGS_FILE
        self._settings = {}
        self._migrate_from_old_location()
        self._load()

    def _migrate_from_old_location(self):
        """Migrate settings from old Source Code/data location to platformdirs."""
        old_path = Path(__file__).parent.parent / "data" / "settings.json"
        if old_path.exists() and not SETTINGS_FILE.exists():
            try:
                import shutil
                SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
                shutil.copy2(old_path, SETTINGS_FILE)
                logger.info("Migrated settings from %s to %s", old_path, SETTINGS_FILE)
            except Exception as e:
                logger.error("Migration failed: %s", e)

    def _load(self):
        """Load settings from JSON file."""
        if self.settings_path.exists():
            try:
                with open(self.settings_path, encoding="utf-8") as f:
                    self._settings = json.load(f)
            except (json.JSONDecodeError, IOError):
                self._settings = {}

        # Apply defaults for missing settings.
        self._apply_defaults()

    def _apply_defaults(self):
        """Set default values for missing settings."""
        defaults = {
            "display": {
                "auto_open_on_second_monitor": True,
                "display_monitor_index": 1,
                "fullscreen_on_open": False,
                "always_on_top": True,
            },
            "theme": {
                "active_theme": "dark_gold",
            },
            "general": {
                "default_translation": "NKJV",
                "auto_save_sessions": True,
            },
            "ai": {
                "speech_model": "faster-whisper-medium",
                "confidence_threshold_high": 0.85,
                "confidence_threshold_medium": 0.65,
                "auto_advance_on_high": True,
            },
            "hotkeys": HOTKEY_DEFAULTS,
            "channels": {
                "main": {
                    "enabled": True,
                    "mode": "fullscreen",
                    "theme": "default",
                    "monitor": None,
                    "lower_third": {"logo_path": None, "show_logo_placeholder": True},
                },
                "alt": {
                    "enabled": True,
                    "mode": "lower_third",
                    "theme": "default",
                    "monitor": None,
                    "lower_third": {"logo_path": None, "show_logo_placeholder": True},
                },
            },
        }

        for section, values in defaults.items():
            if section not in self._settings or not isinstance(self._settings.get(section), dict):
                self._settings[section] = {}
            for key, value in values.items():
                if key not in self._settings[section]:
                    self._settings[section][key] = value

        self._normalize_hotkeys_section()

    def _normalize_hotkeys_section(self):
        """Ensure the hotkeys section has the expected shape without hiding issues."""
        hotkeys = self._settings.get("hotkeys", {})
        if not isinstance(hotkeys, dict):
            hotkeys = {}

        normalized = {"enabled": self._coerce_bool(hotkeys.get("enabled", HOTKEY_DEFAULTS["enabled"]))}

        for action in HOTKEY_ACTIONS:
            if action not in hotkeys:
                normalized[action] = HOTKEY_DEFAULTS[action]
                continue

            raw_shortcut = hotkeys.get(action)
            normalized[action] = self._normalize_shortcut(raw_shortcut) if isinstance(raw_shortcut, str) else raw_shortcut

        self._settings["hotkeys"] = normalized

    def _coerce_bool(self, value):
        """Coerce common truthy and falsey representations into a bool."""
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return bool(value)
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"true", "1", "yes", "on"}:
                return True
            if normalized in {"false", "0", "no", "off"}:
                return False
        return bool(value)

    def _normalize_shortcut(self, value):
        """Return a cleaned shortcut string or an empty string."""
        if not isinstance(value, str):
            return ""
        return value.strip()

    def _is_valid_hotkey_shortcut(self, shortcut):
        """Validate the shortcut syntax used by the hotkey settings."""
        parts = [part.strip() for part in shortcut.split("+") if part.strip()]
        if len(parts) < 2:
            return False

        modifiers = set()
        key_token = parts[-1].upper()

        for modifier in parts[:-1]:
            mod_upper = modifier.upper()
            if mod_upper not in HOTKEY_MODIFIERS:
                return False
            modifiers.add(mod_upper)

        if not modifiers:
            return False

        if len(key_token) == 1 and key_token.isalpha():
            return True
        if len(key_token) == 1 and key_token.isdigit():
            return True
        if key_token.startswith("F") and key_token[1:].isdigit():
            fn_number = int(key_token[1:])
            return 1 <= fn_number <= 24
        return key_token in HOTKEY_SPECIAL_KEYS

    def get(self, section, key, default=None):
        """Get a setting value."""
        return self._settings.get(section, {}).get(key, default)

    def set(self, section, key, value):
        """Set a setting value."""
        if section not in self._settings or not isinstance(self._settings.get(section), dict):
            self._settings[section] = {}
        self._settings[section][key] = value
        if section == "hotkeys":
            self._normalize_hotkeys_section()

    def get_section(self, section):
        """Get all settings in a section."""
        if section == "hotkeys":
            self._normalize_hotkeys_section()
        return self._settings.get(section, {}).copy()

    def get_hotkeys(self):
        """Get validated hotkey settings using safe registration defaults."""
        raw_hotkeys = self.get_section("hotkeys")
        normalized, _issues = self.validate_hotkeys(raw_hotkeys)
        return normalized

    def get_hotkey_bindings(self):
        """Get the normalized action-to-shortcut mapping."""
        hotkeys = self.get_hotkeys()
        return {action: hotkeys[action] for action in HOTKEY_ACTIONS}

    def validate_hotkeys(self, hotkeys=None):
        """Validate a hotkey mapping and return normalized values plus issues."""
        source = hotkeys if isinstance(hotkeys, dict) else self.get_hotkeys()
        normalized = {"enabled": self._coerce_bool(source.get("enabled", HOTKEY_DEFAULTS["enabled"]))}
        issues = []
        seen_shortcuts = set()

        for action in HOTKEY_ACTIONS:
            had_value = action in source
            raw_shortcut = source.get(action, HOTKEY_DEFAULTS[action])
            shortcut = self._normalize_shortcut(raw_shortcut)

            if not shortcut:
                if had_value:
                    issues.append(f"{action}: invalid shortcut '{raw_shortcut}', skipped")
                    normalized[action] = ""
                else:
                    issues.append(f"{action}: missing shortcut, using default")
                    shortcut = HOTKEY_DEFAULTS[action]
                    normalized[action] = shortcut
                    seen_shortcuts.add(shortcut.strip().lower())
                continue
            elif not self._is_valid_hotkey_shortcut(shortcut):
                if had_value:
                    issues.append(f"{action}: invalid shortcut '{shortcut}', skipped")
                    normalized[action] = ""
                else:
                    issues.append(f"{action}: missing shortcut, using default")
                    normalized[action] = HOTKEY_DEFAULTS[action]
                    seen_shortcuts.add(HOTKEY_DEFAULTS[action].strip().lower())
                continue

            shortcut_key = shortcut.strip().lower()
            if shortcut_key in seen_shortcuts:
                issues.append(f"{action}: duplicate shortcut '{shortcut}', skipped")
                normalized[action] = ""
                continue

            seen_shortcuts.add(shortcut_key)
            normalized[action] = shortcut

        return normalized, issues

    def save(self):
        """Save settings to JSON file."""
        try:
            self._normalize_hotkeys_section()
            self.settings_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.settings_path, "w", encoding="utf-8") as f:
                json.dump(self._settings, f, indent=2, ensure_ascii=False)
            return True
        except IOError as e:
            logger.error("Failed to save settings: %s", e)
            return False

    # ── Per-channel settings ──────────────────────────────────────────────────

    def get_channel_settings(self, channel_name: str) -> ChannelSettings:
        """Load settings for a specific channel with defaults."""
        channels = self._settings.get("channels", {})
        ch = channels.get(channel_name, {})
        lt = ch.get("lower_third", {})

        # DEFENSIVE: Use `.get(key) or default` pattern for nullable values
        # (see SKILL in home_panel.py — handles missing keys AND None values)
        return ChannelSettings(
            enabled=ch.get("enabled", True),
            mode=(ch.get("mode") or "fullscreen"),
            theme_id=(ch.get("theme") or "default"),
            monitor=ch.get("monitor"),
            logo_path=lt.get("logo_path"),
            show_logo_placeholder=lt.get("show_logo_placeholder", True),
        )

    def set_channel_settings(self, channel_name: str, settings: ChannelSettings) -> None:
        """Save settings for a specific channel."""
        if "channels" not in self._settings:
            self._settings["channels"] = {}
        self._settings["channels"][channel_name] = {
            "enabled": settings.enabled,
            "mode": settings.mode,
            "theme": settings.theme_id,
            "monitor": settings.monitor,
            "lower_third": {
                "logo_path": settings.logo_path,
                "show_logo_placeholder": settings.show_logo_placeholder,
            },
        }
        self.save()

    def reset_to_defaults(self):
        """Reset all settings to default values."""
        self._settings = {}
        self._apply_defaults()
        self.save()
