"""settings.py — VerseFlow Settings Manager

Handles loading and saving application settings to JSON.
Includes display configuration, theme preferences, and AI settings.
"""

import json
from pathlib import Path
from typing import Optional

SETTINGS_FILE = Path(__file__).parent.parent / "data" / "settings.json"


class SettingsManager:
    """Manages application settings persistence."""

    def __init__(self, settings_path=None):
        self.settings_path = settings_path or SETTINGS_FILE
        self._settings = {}
        self._load()

    def _load(self):
        """Load settings from JSON file."""
        if self.settings_path.exists():
            try:
                with open(self.settings_path, encoding="utf-8") as f:
                    self._settings = json.load(f)
            except (json.JSONDecodeError, IOError):
                self._settings = {}
        
        # Apply defaults for missing settings
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
            }
        }
        
        for section, values in defaults.items():
            if section not in self._settings:
                self._settings[section] = {}
            for key, value in values.items():
                if key not in self._settings[section]:
                    self._settings[section][key] = value

    def get(self, section, key, default=None):
        """Get a setting value."""
        return self._settings.get(section, {}).get(key, default)

    def set(self, section, key, value):
        """Set a setting value."""
        if section not in self._settings:
            self._settings[section] = {}
        self._settings[section][key] = value

    def get_section(self, section):
        """Get all settings in a section."""
        return self._settings.get(section, {}).copy()

    def save(self):
        """Save settings to JSON file."""
        try:
            self.settings_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.settings_path, "w", encoding="utf-8") as f:
                json.dump(self._settings, f, indent=2, ensure_ascii=False)
            return True
        except IOError as e:
            print(f"Failed to save settings: {e}")
            return False

    def reset_to_defaults(self):
        """Reset all settings to default values."""
        self._settings = {}
        self._apply_defaults()
        self.save()
