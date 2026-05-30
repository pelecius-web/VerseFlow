"""Tests for Phase 1 Theme Engine v2 + DisplayWidget Extraction."""

import json
from pathlib import Path

import pytest

from theme import Theme, ThemeManager, KNOWN_SCHEMA_VERSIONS
from display_widget import DisplayWidget


class TestThemeEngine:
    """Schema v2 engine integrity."""

    def test_known_schema_versions(self):
        assert KNOWN_SCHEMA_VERSIONS == {"1.0", "2.0"}

    def test_theme_default_schema_version_gets_upgraded(self):
        """A theme with no schema_version defaults to 1.0 and is upgraded to 2.0."""
        theme = Theme({"id": "test", "name": "Test"})
        assert theme.schema_version == "2.0"

    def test_theme_v2_keeps_version(self):
        theme = Theme({"id": "test", "name": "Test", "schema_version": "2.0"})
        assert theme.schema_version == "2.0"

    def test_theme_unknown_version_resets_to_10_and_upgrades(self):
        """Unknown schema_version is treated as 1.0 and upgraded to 2.0."""
        theme = Theme({"id": "test", "name": "Test", "schema_version": "99.0"})
        assert theme.schema_version == "2.0"

    def test_theme_upgrade_adds_fullscreen(self):
        theme = Theme({"id": "test", "name": "Test", "colors": {"bg_secondary": "#abc"}})
        assert "background_color" in theme.fullscreen
        assert "ref_font_family" in theme.fullscreen
        assert len(theme.fullscreen) == 10

    def test_theme_upgrade_adds_lower_third_defaults(self):
        theme = Theme({"id": "test", "name": "Test"})
        assert "transition" in theme.lower_third
        assert theme.lower_third["transition"]["type"] == "none"
        assert theme.lower_third["transition"]["duration_ms"] == 200
        assert "logo_format" in theme.lower_third
        assert "church_name_color" in theme.lower_third
        assert "background_image" in theme.lower_third

    def test_theme_source_path_is_path(self):
        theme = Theme({"id": "test", "name": "Test"}, source_path=Path("/tmp/theme.json"))
        assert isinstance(theme.source_path, Path)


class TestThemeManager:
    """ThemeManager lifecycle."""

    def test_set_app_theme_exists(self):
        mgr = ThemeManager()
        assert hasattr(mgr, "set_app_theme")

    def test_get_theme_returns_none_for_missing(self):
        mgr = ThemeManager()
        assert mgr.get_theme("nonexistent") is None


class TestDisplayWidget:
    """DisplayWidget creation."""

    def test_widget_importable(self):
        assert DisplayWidget is not None
