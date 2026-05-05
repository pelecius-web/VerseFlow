"""display_window.py — VerseFlow Congregation Display Window

Separate QMainWindow for second monitor display.
Shows ONLY the current verse with theme styling, animations, and optional reference overlay.
No controls visible to audience.
"""

from PyQt6.QtCore import Qt, QTimer, QRectF
from PyQt6.QtGui import QFont, QColor, QPainter, QPen, QLinearGradient, QFontMetrics
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QFrame, QSizePolicy, QApplication, QScrollArea,
)


class DisplayWindow(QMainWindow):
    """Congregation display window for second monitor.
    Opens as a normal window initially. Goes frameless+fullscreen when a verse goes live.
    """

    def __init__(self, display_controller, theme_manager, parent=None):
        super().__init__(parent)
        print("[DISPLAY_WINDOW] v0.7.2 — lazy fullscreen loaded", flush=True)
        self.display = display_controller
        self.theme_mgr = theme_manager
        self._is_fullscreen = False
        self._is_live = False  # Only fullscreen when verse goes live
        self._layout_mode = "single"
        self._overlay_labels = []  # Track overlay labels for cleanup

        # Start as a normal window (not frameless)
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setWindowTitle("VerseFlow — Congregation Display")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)

        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Verse reference label
        self.ref_label = QLabel("")
        self.ref_label.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        self.ref_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.ref_label.setWordWrap(False)
        self.ref_label.setFixedHeight(36)
        layout.addWidget(self.ref_label)

        # Verse text scroll area
        self.verse_scroll = QScrollArea()
        self.verse_scroll.setWidgetResizable(True)
        self.verse_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.verse_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.verse_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.verse_content = QWidget()
        self.verse_layout = QVBoxLayout(self.verse_content)
        self.verse_layout.setContentsMargins(0, 0, 0, 0)
        self.verse_layout.setSpacing(16)

        self.verse_scroll.setWidget(self.verse_content)
        layout.addWidget(self.verse_scroll, 1)  # Expanding

        # Bottom bar (subtle)
        self.bottom_bar = QLabel("VerseFlow — v0.7.2")
        self.bottom_bar.setFont(QFont("Segoe UI", 9, QFont.Weight.Light))
        self.bottom_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.bottom_bar.setFixedHeight(18)
        layout.addWidget(self.bottom_bar)

        # Connect to display controller
        self.display.verse_changed.connect(self._on_verse_changed)
        self.display.layout_changed.connect(self._on_layout_changed)
        self.display.translations_changed.connect(self._on_translations_changed)

        # Animation timer for verse transitions
        self._fade_timer = QTimer()
        self._fade_timer.setSingleShot(True)
        self._fade_timer.timeout.connect(self._finish_fade)
        self._opacity = 1.0

        # Apply initial styling
        self._apply_theme_styling()

    def _on_verse_changed(self, verse):
        """Update display when verse changes."""
        if not verse:
            self._clear_verse_content()
            self.ref_label.setText("")
            self._is_live = False
            # Close window entirely — BibleShow behavior for extended display
            self.close()
            return

        # Verse is going live — go fullscreen on first verse
        if not self._is_live:
            self._is_live = True
            self.showFullScreen()
            self._is_fullscreen = True

        # Reference label
        self.ref_label.setText(verse.get("reference", ""))

        # Render verse content
        try:
            self._render_verse_content(verse)
        except Exception as e:
            print(f"[DISPLAY] ERROR rendering verse: {e}", flush=True)
            import traceback
            traceback.print_exc()
            return

        # Instant display — no fade to avoid desktop flash
        self._start_fade()

    def _on_translations_changed(self, translations):
        """Update display when overlay translations change."""
        if self.display.current:
            self._render_verse_content(self.display.current)
            self._start_fade()

    def _clear_verse_content(self):
        """Clear all verse content from the verse layout."""
        while self.verse_layout.count():
            item = self.verse_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _calc_single_font_size(self, text, min_font=32, max_font=96):
        """Binary search for single verse font size that fills the screen."""
        viewport = self.verse_scroll.viewport()
        if not viewport:
            return 64

        # ref_label (36) + bottom_bar (18) + layout margins already excluded by scroll
        available_height = viewport.height() - 70

        low, high = min_font, max_font
        best = min_font

        for _ in range(15):
            if low > high:
                break
            mid = (low + high) // 2
            font = QFont("Segoe UI", mid)
            fm = QFontMetrics(font)
            padding = max(8, int(mid * 0.25))
            # Deduct CSS padding from both sides to get true text area width
            text_width = viewport.width() - (padding * 2)
            lines = self._count_wrapped_lines(text, text_width, fm)
            # 2 stretches + 1 label = 2 gaps at setSpacing(16) each
            total_height = (lines * fm.lineSpacing()) + (padding * 2) + 32
            if total_height <= available_height:
                best = mid
                low = mid + 1
            else:
                high = mid - 1
        return best

    def _calc_overlay_font_sizes(self, verses, min_font=14, max_font=80):
        """Binary search for largest verse_font that fits all overlay blocks."""
        viewport = self.verse_scroll.viewport()
        if not viewport:
            return 48, 28

        # Subtract fixed chrome: layout contentsMargins(12,10,12,10) = 20px vertical
        available_height = viewport.height() - 20

        if viewport.width() <= 0 or available_height <= 0:
            return min_font, int(min_font * 0.75)

        low, high = min_font, max_font
        best = min_font

        for _ in range(15):
            if low > high:
                break
            mid = (low + high) // 2
            trans_font = max(10, int(mid * 0.75))
            if self._overlay_content_fits(mid, trans_font, viewport.width(), available_height, verses):
                best = mid
                low = mid + 1
            else:
                high = mid - 1

        return best, max(10, int(best * 0.75))

    def _overlay_content_fits(self, verse_font, trans_font, max_width, max_height, verses):
        """Simulate rendering of all overlay blocks with inline translation name."""
        v_font = QFont("Segoe UI", verse_font)
        v_fm = QFontMetrics(v_font)

        padding = max(8, int(verse_font * 0.25))
        # Deduct CSS padding from both sides to get true text area width
        text_width = max_width - (padding * 2)

        total_height = 0
        for verse in verses:
            text = verse.get("text", "")
            trans = verse.get("translation", "")
            full_text = f"{trans}  {text}"
            lines = self._count_wrapped_lines(full_text, text_width, v_fm)
            block_height = (lines * v_fm.lineSpacing()) + (padding * 2)
            total_height += block_height

        # Layout gap overhead: setSpacing(16) applies between every adjacent item.
        # Items in order: stretch | label | sep | label | sep | label | stretch
        # For N verses, that's: 1 stretch + N labels + (N-1) seps + 1 stretch = 2N+1 items
        # Number of 16px gaps between them = 2N items
        num_items = 2 * len(verses)      # gaps between the 2N+1 items
        total_height += num_items * 16

        # Separator widget heights (1px each)
        total_height += (len(verses) - 1) * 1

        return total_height <= max_height

    def _count_wrapped_lines(self, text, max_width, fm):
        """Return number of lines needed to display text with given font metrics."""
        if not text:
            return 1
        words = text.split()
        if not words:
            return 1

        lines = 1
        current_width = 0
        space_width = fm.horizontalAdvance(' ')

        for word in words:
            word_width = fm.horizontalAdvance(word)
            if current_width == 0:
                current_width = word_width
            else:
                if current_width + space_width + word_width <= max_width:
                    current_width += space_width + word_width
                else:
                    lines += 1
                    current_width = word_width
        return lines

    def _render_verse_content(self, primary_verse):
        """Render verse text with overlay format using accurate font sizing."""
        translations = self.display.secondary_translations
        total = 1 + len(translations)

        self._clear_verse_content()

        if total <= 1:
            # Single translation
            verse_text = primary_verse.get("text", "")
            ref_text = primary_verse.get("reference", "")
            trans_name = primary_verse.get("translation", "")

            if trans_name:
                self.ref_label.setText(f"{ref_text} — {trans_name}")
            else:
                self.ref_label.setText(ref_text)

            verse_font = self._calc_single_font_size(verse_text)
            verse_label = QLabel(verse_text)
            verse_label.setFont(QFont("Segoe UI", verse_font))
            verse_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
            verse_label.setWordWrap(True)
            padding = max(8, int(verse_font * 0.25))
            verse_label.setStyleSheet(f"color: #e8e2d8; background: transparent; padding: {padding}px;")
            self.verse_layout.addStretch(1)
            self.verse_layout.addWidget(verse_label)
            self.verse_layout.addStretch(1)
            return

        # Overlay mode – reference only (no version)
        ref_text = primary_verse.get("reference", "")
        self.ref_label.setText(ref_text)

        verses_to_render = [primary_verse] + translations
        verse_font, trans_font = self._calc_overlay_font_sizes(verses_to_render)

        def add_verse_block(verse, is_primary=False):
            """Create a verse block with translation name inline with the verse text."""
            trans = verse.get("translation", "")
            text = verse.get("text", "")
            color = "#c8a03c" if is_primary else "#d4a84b"
            text_color = "#e8e2d8" if is_primary else "#d0c8b8"
            
            padding = max(8, int(verse_font * 0.25))

            label = QLabel(
                f'<span style="color: {color}; font-size: {trans_font}px; font-weight: 700;">{trans}</span> '
                f'<span style="color: {text_color};">{text}</span>'
            )
            label.setFont(QFont("Segoe UI", verse_font))
            label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
            label.setWordWrap(True)
            label.setTextFormat(Qt.TextFormat.RichText)
            label.setStyleSheet(f"background: transparent; padding: {padding}px;")

            return label

        self.verse_layout.addStretch(1)

        # Primary (top)
        self.verse_layout.addWidget(add_verse_block(primary_verse, is_primary=True))

        # Overlays with separators
        for overlay_verse in translations:
            sep = QFrame()
            sep.setFrameShape(QFrame.Shape.HLine)
            sep.setStyleSheet("background: rgba(200,160,60,0.2);")
            sep.setFixedHeight(1)
            self.verse_layout.addWidget(sep)
            self.verse_layout.addWidget(add_verse_block(overlay_verse, is_primary=False))

        self.verse_layout.addStretch(1)

    def _on_layout_changed(self, mode):
        """Update display layout based on layout mode."""
        self._layout_mode = mode
        # Future: implement different layout templates
        # For now, single verse layout works for all modes

    def _start_fade(self):
        """Instant display update — no fade animation to avoid desktop flash."""
        self.setWindowOpacity(1.0)

    def _fade_in(self):
        """No-op — instant display now."""
        pass

    def _finish_fade(self):
        """No-op — instant display now."""
        pass

    def resizeEvent(self, event):
        """Recalculate font sizes when the window is resized."""
        super().resizeEvent(event)
        if self.display.current and self._is_live:
            self._render_verse_content(self.display.current)

    def _apply_theme_styling(self):
        """Apply theme-based styling to display elements."""
        theme = self.theme_mgr.current
        if not theme:
            self._apply_default_styling()
            return

        c = theme.c

        # Background gradient
        self.setStyleSheet(f"""
            QMainWindow {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {c('bg_primary')}, stop:1 {c('bg_secondary')});
            }}
            QWidget {{
                background: transparent;
                color: {c('text_primary')};
            }}
        """)

        # Label styling
        self.ref_label.setStyleSheet(f"""
            color: {c('gold')};
            background: transparent;
            letter-spacing: 4px;
        """)

        self.verse_scroll.setStyleSheet(f"""
            QScrollArea {{
                background: transparent;
                border: none;
            }}
        """)

        self.bottom_bar.setStyleSheet(f"""
            color: {c('text_faint')};
            background: transparent;
        """)

    def _apply_default_styling(self):
        """Apply default dark theme styling if no theme is loaded."""
        self.setStyleSheet("""
            QMainWindow {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #0f0f1a, stop:1 #0a0a14);
            }
            QWidget {
                background: transparent;
                color: #e8e2d8;
            }
        """)

        self.ref_label.setStyleSheet("""
            color: #c8a03c;
            background: transparent;
            letter-spacing: 4px;
        """)

        self.verse_scroll.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none;
            }
        """)

        self.bottom_bar.setStyleSheet("""
            color: rgba(200,160,60,0.15);
            background: transparent;
        """)

    def toggle_fullscreen(self):
        """Toggle fullscreen mode."""
        if self._is_fullscreen:
            self.showNormal()
            self._is_fullscreen = False
        else:
            self.showFullScreen()
            self._is_fullscreen = True

    def keyPressEvent(self, event):
        """Handle key events for display control."""
        if event.key() == Qt.Key.Key_Escape:
            if self._is_fullscreen:
                self.showNormal()
                self._is_fullscreen = False
            else:
                self.close()
        elif event.key() == Qt.Key.Key_F11:
            self.toggle_fullscreen()
        super().keyPressEvent(event)

    def mouseDoubleClickEvent(self, event):
        """Double-click to toggle fullscreen."""
        self.toggle_fullscreen()
        super().mouseDoubleClickEvent(event)
