"""Regenerate all built-in thumbnails and produce a contact-sheet for review.

Copies built-in theme JSONs into a temp workspace so the live src/utils/themes/
directory is never touched. Generates thumbnails via ThemeDesignerPanel's
_generate_theme_thumbnail, then stitches them into a single contact-sheet PNG.

Usage:
    python scripts/regenerate_thumbs_contact_sheet.py

Output:
    logs/thumbnails_contact_sheet.png
"""

import sys
import os
import shutil
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

# Add source paths
SRC = Path(__file__).resolve().parent.parent / "src"
for subdir in ("", "ui", "core", "display", "db", "ndi", "utils"):
    p = str(SRC / subdir) if subdir else str(SRC)
    if p not in sys.path:
        sys.path.insert(0, p)

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QPainter, QFont, QColor, QFontDatabase

from theme import BUILTIN_THEME_IDS, THEMES_DIR, Theme, ThemeManager


def _load_windows_fonts_for_offscreen_rendering():
    """Register common Windows fonts when Qt's offscreen backend sees none."""
    font_dir = Path(r"C:\Windows\Fonts")
    if not font_dir.exists():
        return

    font_files = (
        "segoeui.ttf", "segoeuib.ttf",
        "times.ttf", "timesbd.ttf",
        "georgia.ttf", "georgiab.ttf",
        "trebuc.ttf", "trebucbd.ttf",
        "GARA.TTF", "GARABD.TTF",
        "pala.ttf", "palab.ttf",
        "BOOKOS.TTF", "BOOKOSB.TTF",
        "arial.ttf", "arialbd.ttf",
    )
    for name in font_files:
        path = font_dir / name
        if path.exists():
            QFontDatabase.addApplicationFont(str(path))


def main():
    app = QApplication(sys.argv)
    _load_windows_fonts_for_offscreen_rendering()

    # Copy all built-in JSONs into temp dir
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        for tid in sorted(BUILTIN_THEME_IDS):
            src_json = THEMES_DIR / f"{tid}.json"
            dst_json = tmp_path / f"{tid}.json"
            shutil.copy2(src_json, dst_json)

        # Build temp-backed ThemeManager
        class _TempThemeManager:
            def __init__(self, base):
                self._base = base
                self._cache: dict[str, Theme] = {}
                self.application_fonts: set = set()

            def themes_dir(self):
                return tmp_path

            def get_theme(self, tid):
                if tid in self._cache:
                    return self._cache[tid]
                path = tmp_path / f"{tid}.json"
                if path.exists():
                    import json
                    data = json.loads(path.read_text())
                    theme = Theme(data, source_path=path)
                    theme.id = tid  # ensure id matches
                    self._cache[tid] = theme
                    return theme
                return None

            def available_themes(self):
                result = []
                for tid in sorted(BUILTIN_THEME_IDS):
                    t = self.get_theme(tid)
                    if t:
                        result.append(t)
                return result

        mgr = _TempThemeManager(THEMES_DIR)

        from theme_designer import ThemeDesignerPanel

        panel = ThemeDesignerPanel.__new__(ThemeDesignerPanel)
        panel._theme_mgr = mgr

        thumbs: dict[str, QPixmap] = {}
        for tid in sorted(BUILTIN_THEME_IDS):
            panel._generate_theme_thumbnail(tid)
            thumb_path = tmp_path / f"{tid}.thumb.png"
            if thumb_path.exists():
                thumb_path.replace(tmp_path / f"{tid}_gen.png")
                thumbs[tid] = QPixmap(str(tmp_path / f"{tid}_gen.png"))

        if not thumbs:
            print("No thumbnails generated.")
            return

        # Stitch contact sheet
        cols = 2
        rows = (len(thumbs) + cols - 1) // cols
        card_w = 300
        card_h = 96
        spacing = 8
        header_h = 20
        sheet_w = cols * card_w + (cols + 1) * spacing
        sheet_h = rows * (card_h + header_h + 4) + spacing * 2

        sheet = QPixmap(sheet_w, sheet_h)
        sheet.fill(QColor(30, 30, 35))
        painter = QPainter(sheet)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        label_font = QFont("Segoe UI", 8)
        label_font.setBold(True)

        for idx, tid in enumerate(sorted(BUILTIN_THEME_IDS)):
            col = idx % cols
            row = idx // cols
            x = spacing + col * (card_w + spacing)
            y = spacing + row * (card_h + header_h + 4)

            # Theme name label
            painter.setFont(label_font)
            painter.setPen(QColor(200, 200, 210))
            theme = mgr.get_theme(tid)
            name = theme.name if theme else tid
            painter.drawText(x, y + 14, name)

            # Thumbnail
            if tid in thumbs and not thumbs[tid].isNull():
                pix = thumbs[tid].scaled(
                    card_w, card_h,
                    Qt.AspectRatioMode.IgnoreAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                painter.drawPixmap(x, y + header_h, pix)
            else:
                painter.fillRect(x, y + header_h, card_w, card_h, QColor(60, 60, 65))

        painter.end()

        logs_dir = Path(__file__).resolve().parent.parent / "logs"
        logs_dir.mkdir(exist_ok=True)
        out = logs_dir / "thumbnails_contact_sheet.png"
        sheet.save(str(out))
        print(f"Contact sheet saved to: {out}")


if __name__ == "__main__":
    main()
