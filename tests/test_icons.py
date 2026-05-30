"""test_icons.py — SVG icon rendering validation (Phase 2)."""

from PyQt6.QtWidgets import QApplication
import pytest

from icons import (
    get_keyboard_icon,
    get_settings_gear_icon,
    get_layers_icon,
    get_broadcast_icon,
    get_palette_icon,
)


@pytest.fixture(scope="module")
def app():
    existing = QApplication.instance()
    if existing is not None:
        return existing
    return QApplication([])


ICON_FUNCTIONS = [
    ("keyboard", get_keyboard_icon),
    ("settings_gear", get_settings_gear_icon),
    ("layers", get_layers_icon),
    ("broadcast", get_broadcast_icon),
    ("palette", get_palette_icon),
]


class TestIconRendering:
    """Verify every SVG factory produces a renderable, non-null icon."""

    def test_all_icons_render_non_null(self, app):
        for name, fn in ICON_FUNCTIONS:
            icon = fn()
            assert not icon.isNull(), f"{name}_icon.isNull() — SVG malformed or renderer failed"

    def test_all_icons_have_non_null_pixmap_at_16px(self, app):
        for name, fn in ICON_FUNCTIONS:
            icon = fn()
            pixmap = icon.pixmap(16, 16)
            assert not pixmap.isNull(), f"{name}_icon 16px pixmap is null — render failure"

    def test_all_icons_accept_custom_color(self, app):
        for name, fn in ICON_FUNCTIONS:
            icon = fn(color="#ff0000", size=16)
            pixmap = icon.pixmap(16, 16)
            assert not pixmap.isNull(), f"{name}_icon with custom color failed to render"

    def test_default_size_is_16(self, app):
        for name, fn in ICON_FUNCTIONS:
            icon = fn()
            pixmap = icon.pixmap(16, 16)
            assert pixmap.width() == 16
            assert pixmap.height() == 16
