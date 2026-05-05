"""display_window.py — VerseFlow Congregation Display Window

Separate QMainWindow for second monitor display.
Shows ONLY the current verse with theme styling, animations, and optional reference overlay.
No controls visible to audience.
"""

import logging
import math

from PyQt6.QtCore import Qt, QTimer, QRectF

logger = logging.getLogger("VerseFlow")
from PyQt6.QtGui import QFont, QColor, QPainter, QPen, QLinearGradient, QFontMetrics, QTextDocument, QTextOption
from constants import (
    DISPLAY_MODE_FULLSCREEN, DISPLAY_MODE_LOWER_THIRD,
    LOWER_THIRD_HEIGHT_RATIO, LOWER_THIRD_LOGO_WIDTH_RATIO,
    LOWER_THIRD_LOGO_MAX_HEIGHT_RATIO, LOWER_THIRD_SEPARATOR_WIDTH,
    LOWER_THIRD_TEXT_MARGIN, LOWER_THIRD_REF_FONT_RATIO,
    LOWER_THIRD_BACKGROUND_ALPHA,
)
from db_layer import abbreviate_translation
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QFrame, QSizePolicy, QApplication, QScrollArea,
    QStackedWidget,
)


class DisplayWindow(QMainWindow):
    """Congregation display window for second monitor.
    Opens as a normal window initially. Goes frameless+fullscreen when a verse goes live.
    """

    # Layout/measurement constants — single source of truth.
    # verse_layout uses setSpacing(16); single mode has 2 gaps (stretch|label|stretch).
    LAYOUT_GAP = 16
    SAFETY_BUFFER = 4  # Sub-pixel rendering margin (tight — measurement is accurate)
    BLOCK_MARGIN = 6   # Per-block safety for QLabel internal doc margin not captured by QTextDocument
    RESIZE_DEBOUNCE_MS = 100

    def __init__(self, display_controller, theme_manager, screen=None, parent=None):
        super().__init__(parent)
        logger.info("v0.7.2 — lazy fullscreen loaded")
        self.display = display_controller
        self.theme_mgr = theme_manager
        self._target_screen = screen  # Stored at creation; self.screen() unreliable when hidden
        self._is_fullscreen = False
        self._is_live = False  # Only fullscreen when verse goes live
        self._layout_mode = "single"
        self._display_mode = DISPLAY_MODE_FULLSCREEN
        self._overlay_labels = []  # Track overlay labels for cleanup

        # Debounce expensive verse re-renders during window resize.
        self._resize_timer = QTimer()
        self._resize_timer.setSingleShot(True)
        self._resize_timer.timeout.connect(self._handle_resize_finished)

        # Debounce translation overlay updates.
        # When HomePanel adds 2-3 translations in a single batch, translations_changed
        # fires once per add_translation() call. Without debouncing, each signal triggers
        # a full clear + re-render, stacking ghost widgets (via deleteLater) before Qt
        # can remove them, which causes long verses to overflow the viewport.
        # A 0ms timer coalesces all signals in one batch into a single re-render.
        self._translations_update_timer = QTimer()
        self._translations_update_timer.setSingleShot(True)
        self._translations_update_timer.setInterval(0)
        self._translations_update_timer.timeout.connect(self._do_translations_update)

        # Cache fitted font sizes by (text_hash, viewport_w, viewport_h, mode).
        self._fit_cache = {}

        # Start as a normal window (not frameless)
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setWindowTitle("VerseFlow — Congregation Display")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)

        # Central widget — QStackedWidget with fullscreen (Page 0) and lower-third (Page 1)
        self._stacked = QStackedWidget()
        self.setCentralWidget(self._stacked)

        # ── Page 0: Fullscreen layout ────────────────────────────────────────
        self._fullscreen_page = QWidget()
        layout = QVBoxLayout(self._fullscreen_page)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(8)

        # Verse reference label (Flexible height + Word Wrap)
        self.ref_label = QLabel("")
        self.ref_label.setFont(QFont("Segoe UI", 32, QFont.Weight.Black))
        self.ref_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.ref_label.setWordWrap(True)
        self.ref_label.setMinimumHeight(56)
        layout.addWidget(self.ref_label, 0)  # Explicitly 0 stretch (header)

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
        layout.addWidget(self.verse_scroll, 1)  # Takes remaining space

        # Bottom bar (subtle)
        self.bottom_bar = QLabel("VerseFlow — v0.7.2")
        self.bottom_bar.setFont(QFont("Segoe UI", 9, QFont.Weight.Light))
        self.bottom_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.bottom_bar.setFixedHeight(18)
        layout.addWidget(self.bottom_bar)

        self._stacked.addWidget(self._fullscreen_page)  # Page 0

        # ── Page 1: Lower-third layout ──────────────────────────────────────
        self._lt_page = QWidget()
        self._build_lower_third_page()
        self._stacked.addWidget(self._lt_page)  # Page 1

        # Default to fullscreen page
        self._stacked.setCurrentIndex(0)

        # Connect to display controller
        self.display.verse_changed.connect(self._on_verse_changed)
        self.display.layout_changed.connect(self._on_layout_changed)
        self.display.translations_changed.connect(self._on_translations_changed)

        # Apply initial styling
        self._apply_theme_styling()

    def _on_verse_changed(self, verse):
        """Update display when verse changes."""
        if not verse:
            self._clear_verse_content()
            self.ref_label.setText("")
            self._is_live = False
            if self.isFullScreen() or self._is_fullscreen:
                self.showNormal()
            self._is_fullscreen = False
            # TODO v1.1.0 polish: animate band out before closing
            # Close window entirely — BibleShow behavior for extended display
            self.close()
            return

        # Verse is going live — set up window based on display mode
        if not self._is_live:
            self._is_live = True
            if self._display_mode == DISPLAY_MODE_FULLSCREEN:
                screen = self._target_screen or self.screen()
                geo = screen.geometry()
                self.setGeometry(geo)
                self.showFullScreen()
                self._is_fullscreen = True
            else:
                # Lower-third: frameless window at full screen size, band at bottom
                self._apply_lower_third_window_state()

        # Reference label (fullscreen page only — lower-third has its own)
        self.ref_label.setText(verse.get("reference", ""))

        # Defer render briefly so Windows/Qt has committed fullscreen/window
        # geometry before font-fit reads dimensions.
        QTimer.singleShot(50, lambda v=verse: self._deferred_render(v))

    def _deferred_render(self, verse):
        """Render verse content after geometry has settled.

        Called via QTimer.singleShot so that showFullScreen()/resize()
        events have been processed and self.width()/self.height() return
        the correct monitor dimensions instead of the default widget size.
        """
        try:
            self._render_verse_content(verse)
        except Exception as e:
            logger.error("ERROR rendering verse: %s", e, exc_info=True)
            return
        # Instant display — no fade to avoid desktop flash
        self._start_fade()

    def _on_translations_changed(self, translations):
        """Coalesce rapid translation-changed signals into a single re-render.

        HomePanel._rebuild_display_overlays() calls add_translation() once per
        overlay in a tight loop, emitting translations_changed each time. Without
        debouncing, each signal triggers a full clear+render cycle, and Qt's deferred
        deleteLater() causes ghost widgets to stack up, making long verses overflow.
        The 0ms timer defers the render to the next event-loop iteration, by which
        point all add_translation() calls in the same batch have completed.
        """
        if self.display.current:
            self._translations_update_timer.start()  # restart — no-op if already queued

    def _do_translations_update(self):
        """Perform the actual re-render after all translation changes have settled."""
        if self.display.current:
            self._render_verse_content(self.display.current)
            self._start_fade()

    def _clear_verse_content(self):
        """Clear all verse content from the active mode's layout."""
        if self._display_mode == DISPLAY_MODE_LOWER_THIRD:
            # Lower-third: clear labels only (frame, logo, separator persist as layout)
            self._lt_ref_label.setText("")
            self._lt_verse_label.setText("")
        else:
            while self.verse_layout.count():
                item = self.verse_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

    def _available_verse_area(self):
        """Calculate available verse area from window geometry (not stale viewport).

        viewport().height() is unreliable immediately after ref_label.setText()
        because the layout hasn't settled yet — it returns the old size.
        This method computes the same value directly from the window.
        """
        # Outer layout margins
        outer_margins = 20 * 2  # layout.setContentsMargins(20,20,20,20)
        outer_spacing = 8        # layout.setSpacing(8)

        # ref_label actual height — use fontMetrics with word wrap calculation
        # sizeHint() underestimates wrapped text; boundingRect() computes actual wrapped height
        avail_label_width = self.width() - outer_margins
        fm = self.ref_label.fontMetrics()
        ref_text = self.ref_label.text()
        rect = fm.boundingRect(
            0, 0, avail_label_width, 9999,
            Qt.TextFlag.TextWordWrap,
            ref_text
        )
        # +16px accounts for CSS padding on ref_label: "padding: 6px 0 10px 0;"
        # QFontMetrics.boundingRect() measures only raw text height, not CSS padding.
        # Omitting this causes avail_h to be overestimated, leading to subtle clipping.
        ref_h = max(self.ref_label.minimumHeight(), rect.height() + 16)

        # bottom bar
        bottom_h = 18

        # verse_scroll viewport = window - chrome
        vp_w = self.width() - outer_margins
        vp_h = self.height() - outer_margins - outer_spacing - ref_h - outer_spacing - bottom_h

        return max(1, vp_w), max(1, vp_h)

    def _calc_single_font_size(self, text, min_font=8, max_font=96):
        """Binary search for single verse font size that fills the screen.

        Uses class constants LAYOUT_GAP and SAFETY_BUFFER as the single source
        of truth for chrome accounting (was previously duplicated as magic '32').
        Results are cached because resize events repeatedly request the same fit.
        """
        avail_w, avail_h = self._available_verse_area()
        if avail_w <= 0 or avail_h <= 0:
            return 64

        cache_key = (self._display_mode, hash(text), avail_w, avail_h, 'single')
        if cache_key in self._fit_cache:
            return self._fit_cache[cache_key]

        # Single mode layout: [stretch | label | stretch] → 2 gaps between adjacent items.
        layout_overhead = self.LAYOUT_GAP * 2
        available_height = avail_h - layout_overhead - self.SAFETY_BUFFER

        low, high = min_font, max_font
        best = min_font

        max_iters = math.ceil(math.log2(max_font - min_font + 1)) + 1
        for _ in range(max_iters):
            if low > high:
                break
            mid = (low + high) // 2
            font = QFont("Segoe UI", mid)
            padding = max(8, int(mid * 0.25))
            text_width = avail_w - (padding * 2)
            text_height = self._measure_wrapped_text_height(text, font, text_width)
            total_height = text_height + (padding * 2) + self.BLOCK_MARGIN
            if total_height <= available_height:
                best = mid
                low = mid + 1
            else:
                high = mid - 1

        self._fit_cache[cache_key] = best
        if len(self._fit_cache) > 50:
            self._fit_cache.pop(next(iter(self._fit_cache)))
        return best

    def _calc_overlay_font_sizes(self, verses, min_font=8, max_font=80):
        """Binary search for largest verse_font that fits all overlay blocks.

        Chrome deduction now consistent with single mode: LAYOUT_GAP × num_gaps
        plus SAFETY_BUFFER (was inconsistently '-10' here vs '-32' in single mode).
        """
        avail_w, avail_h = self._available_verse_area()
        if avail_w <= 0 or avail_h <= 0:
            return min_font, max(8, int(min_font * 0.75))

        # Overlay layout: [stretch | label_1 | ... | label_N | stretch] → N+1 gaps.
        num_gaps = len(verses) + 1
        layout_overhead = self.LAYOUT_GAP * num_gaps
        available_height = avail_h - layout_overhead - self.SAFETY_BUFFER

        if available_height <= 0:
            return min_font, max(8, int(min_font * 0.75))

        # Cache key includes verse identities so different overlay sets get distinct entries.
        verses_sig = tuple((v.get("translation", ""), hash(v.get("text", ""))) for v in verses)
        cache_key = (self._display_mode, verses_sig, avail_w, avail_h, 'overlay')
        if cache_key in self._fit_cache:
            best = self._fit_cache[cache_key]
            return best, max(8, int(best * 0.75))

        low, high = min_font, max_font
        best = min_font

        max_iters = math.ceil(math.log2(max_font - min_font + 1)) + 1
        for _ in range(max_iters):
            if low > high:
                break
            mid = (low + high) // 2
            trans_font = max(8, int(mid * 0.75))
            if self._overlay_content_fits(mid, trans_font, avail_w, available_height, verses):
                best = mid
                low = mid + 1
            else:
                high = mid - 1

        self._fit_cache[cache_key] = best
        if len(self._fit_cache) > 50:
            self._fit_cache.pop(next(iter(self._fit_cache)))
        return best, max(8, int(best * 0.75))

    def _overlay_content_fits(self, verse_font, trans_font, max_width, max_height, verses):
        """Simulate rendering of all overlay blocks with inline translation name.

        max_height is already net of layout gaps (deducted by caller using
        LAYOUT_GAP); this routine sums only the per-block heights.
        """
        v_font = QFont("Segoe UI", verse_font)

        padding = max(8, int(verse_font * 0.25))
        # Deduct CSS padding from both sides to get true text area width
        text_width = max_width - (padding * 2)

        total_height = 0
        for i, verse in enumerate(verses):
            html = self._build_overlay_html(
                verse,
                trans_font,
                verse.get("text", ""),
                is_primary=(i == 0),
            )
            block_height = self._measure_rich_text_height(html, v_font, text_width) + (padding * 2) + self.BLOCK_MARGIN
            total_height += block_height

        return total_height <= max_height

    def _measure_wrapped_text_height(self, text, font, max_width):
        """Measure plain text height using Qt's wrap engine, including long tokens."""
        doc = QTextDocument()
        doc.setDefaultFont(font)
        opt = doc.defaultTextOption()
        opt.setWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
        doc.setDefaultTextOption(opt)
        doc.setPlainText(text or "")
        doc.setTextWidth(max(1, max_width))
        return math.ceil(doc.size().height())

    def _measure_rich_text_height(self, html, font, max_width):
        """Measure rich text height using the same wrapping model QLabel uses."""
        doc = QTextDocument()
        doc.setDefaultFont(font)
        opt = doc.defaultTextOption()
        opt.setWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
        doc.setDefaultTextOption(opt)
        doc.setHtml(html or "")
        doc.setTextWidth(max(1, max_width))
        return math.ceil(doc.size().height())

    def _render_verse_content(self, primary_verse):
        """Dispatch verse rendering to the active display mode."""
        if self._display_mode == DISPLAY_MODE_LOWER_THIRD:
            self._render_lower_third(primary_verse)
        else:
            self._render_fullscreen(primary_verse)

    def _render_fullscreen(self, primary_verse):
        """Render verse text in fullscreen mode with overlay support."""
        # Clear lower-third labels to prevent ghost bleed-through
        self._lt_ref_label.setText("")
        self._lt_verse_label.setText("")
        
        # Switch to fullscreen page
        self._stacked.setCurrentIndex(0)

        translations = self.display.secondary_translations
        total = 1 + len(translations)

        self._clear_verse_content()

        if total <= 1:
            # Single translation
            verse_text = primary_verse.get("text", "")
            ref_text = primary_verse.get("reference", "")
            trans_name = primary_verse.get("translation", "")

            if trans_name:
                self.ref_label.setText(f"{ref_text} — {abbreviate_translation(trans_name)}")
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
            text = verse.get("text", "")
            padding = max(8, int(verse_font * 0.25))
            html = self._build_overlay_html(verse, trans_font, text, is_primary)
            label = QLabel(html)
            label.setFont(QFont("Segoe UI", verse_font))
            label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
            label.setWordWrap(True)
            label.setTextFormat(Qt.TextFormat.RichText)
            label.setStyleSheet(f"background: transparent; padding: {padding}px;")

            return label

        self.verse_layout.addStretch(1)

        # Primary (top)
        self.verse_layout.addWidget(add_verse_block(primary_verse, is_primary=True))

        # Overlays
        for overlay_verse in translations:
            self.verse_layout.addWidget(add_verse_block(overlay_verse, is_primary=False))

        self.verse_layout.addStretch(1)

    def _build_overlay_html(self, verse, trans_font, text, is_primary):
        """Build the rich text string used for overlay rendering and measurement.

        Uses 'px' (not 'pt') for the translation badge so the rendered size is
        DPI-independent and matches what QTextDocument measures.  QFont uses points
        internally, but QLabel's RichText engine interprets CSS px consistently across
        measurement and display — pt introduces a DPI-dependent scale factor that
        causes measurement vs. rendering drift on high-DPI screens.
        """
        trans = abbreviate_translation(verse.get("translation", ""))
        color = "#c8a03c" if is_primary else "#d4a84b"
        text_color = "#e8e2d8" if is_primary else "#d0c8b8"
        return (
            f'<span style="color: {color}; font-size: {trans_font}px; font-weight: 700;">{trans}</span> '
            f'<span style="color: {text_color};">{text}</span>'
        )

    def _build_lower_third_page(self):
        """Construct the lower-third layout (QStackedWidget Page 1).

        Layout: [logo_frame | separator | text_column(ref_label + verse_label)]
        The page occupies the full window but only the bottom band is painted
        (via paintEvent). Everything above the band is transparent.
        """
        # Outer layout: push content to the bottom
        outer = QVBoxLayout(self._lt_page)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Stretch above the band — keeps the band at the bottom
        outer.addStretch(1)

        # Band container — horizontal: logo | separator | text
        self._lt_band = QFrame()
        self._lt_band.setObjectName("lt_band")
        band_layout = QHBoxLayout(self._lt_band)
        band_layout.setContentsMargins(0, 0, LOWER_THIRD_TEXT_MARGIN, 0)
        band_layout.setSpacing(0)

        # ── Logo placeholder ────────────────────────────────────────────────
        # Phase 3: static QFrame placeholder. Designed for QWidget swap in
        # v1.3.0 (Theme Designer) — the container accepts any QWidget.
        self._lt_logo_container = QWidget()
        self._lt_logo_container.setObjectName("lt_logo_container")
        logo_container_layout = QVBoxLayout(self._lt_logo_container)
        logo_container_layout.setContentsMargins(
            LOWER_THIRD_TEXT_MARGIN, LOWER_THIRD_TEXT_MARGIN,
            LOWER_THIRD_TEXT_MARGIN, LOWER_THIRD_TEXT_MARGIN
        )
        logo_container_layout.setSpacing(0)

        self._lt_logo = QFrame()
        self._lt_logo.setObjectName("lt_logo")
        self._lt_logo.setStyleSheet("""
            QFrame#lt_logo {
                background: rgba(30, 30, 40, 0.5);
                border: 1px solid rgba(200, 160, 60, 0.25);
                border-radius: 4px;
            }
        """)
        logo_container_layout.addWidget(self._lt_logo)
        band_layout.addWidget(self._lt_logo_container)

        # ── Separator ───────────────────────────────────────────────────────
        self._lt_separator = QFrame()
        self._lt_separator.setObjectName("lt_separator")
        self._lt_separator.setFixedWidth(LOWER_THIRD_SEPARATOR_WIDTH)
        self._lt_separator.setStyleSheet("""
            QFrame#lt_separator {
                background: rgba(200, 160, 60, 0.6);
                border: none;
            }
        """)
        band_layout.addWidget(self._lt_separator)

        # ── Text column ─────────────────────────────────────────────────────
        self._lt_text_column = QWidget()
        self._lt_text_column.setObjectName("lt_text_column")
        text_layout = QVBoxLayout(self._lt_text_column)
        text_layout.setContentsMargins(LOWER_THIRD_TEXT_MARGIN, 0, 0, 0)
        text_layout.setSpacing(4)

        # Reference row: "JOHN 3:16 — KJV"
        self._lt_ref_label = QLabel("")
        self._lt_ref_label.setObjectName("lt_ref")
        self._lt_ref_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom)
        self._lt_ref_label.setWordWrap(False)
        self._lt_ref_label.setStyleSheet("""
            QLabel#lt_ref {
                color: #c8a03c;
                background: transparent;
                font-weight: 700;
                letter-spacing: 2px;
            }
        """)
        text_layout.addWidget(self._lt_ref_label)

        # Verse text row
        self._lt_verse_label = QLabel("")
        self._lt_verse_label.setObjectName("lt_verse")
        self._lt_verse_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self._lt_verse_label.setWordWrap(True)
        self._lt_verse_label.setStyleSheet("""
            QLabel#lt_verse {
                color: #e8e2d8;
                background: transparent;
            }
        """)
        text_layout.addWidget(self._lt_verse_label)

        band_layout.addWidget(self._lt_text_column, 1)  # Text takes remaining width

        outer.addWidget(self._lt_band)

        # Lower-third page is transparent by default — paintEvent paints the band
        self._lt_page.setStyleSheet("background: transparent;")

    def _render_lower_third(self, primary_verse):
        """Render verse in lower-third band layout.

        Phase 3: primary verse only. Secondary translations are skipped.
        The lower-third band is transient — it appears when a verse goes live
        and disappears when cleared.
        """
        # Clear fullscreen content to prevent ghost bleed-through
        while self.verse_layout.count():
            item = self.verse_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.ref_label.setText("")
        
        # Switch to lower-third page
        self._stacked.setCurrentIndex(1)

        # Update logo and separator sizes based on current window geometry
        self._update_lower_third_geometry()

        # Reference row: "JOHN 3:16 — KJV"
        ref_text = primary_verse.get("reference", "")
        trans_name = abbreviate_translation(primary_verse.get("translation", ""))
        if trans_name:
            display_ref = f"{ref_text} — {trans_name}"
        else:
            display_ref = ref_text
        self._lt_ref_label.setText(display_ref)

        # Verse text
        verse_text = primary_verse.get("text", "")
        self._lt_verse_label.setText(verse_text)

        # Font fitting for lower-third
        self._fit_lower_third_fonts(verse_text, display_ref)

    def _update_lower_third_geometry(self):
        """Recalculate lower-third widget sizes based on current window geometry.

        Called on render and on resize to keep ratio-based sizes correct.
        """
        w = self.width()
        h = self.height()
        band_h = int(h * LOWER_THIRD_HEIGHT_RATIO)

        # Logo container width and max height
        logo_w = int(w * LOWER_THIRD_LOGO_WIDTH_RATIO)
        logo_max_h = int(band_h * LOWER_THIRD_LOGO_MAX_HEIGHT_RATIO)
        self._lt_logo_container.setFixedWidth(logo_w)
        self._lt_logo_container.setMaximumHeight(logo_max_h)

        # Band height is set via stretch + fixed height on the band frame
        self._lt_band.setFixedHeight(band_h)

    def _lower_third_available_area(self):
        """Calculate usable text area within the lower-third band.

        Returns (text_width, text_height) for font fitting.
        """
        band_h = int(self.height() * LOWER_THIRD_HEIGHT_RATIO)
        logo_w = int(self.width() * LOWER_THIRD_LOGO_WIDTH_RATIO)
        sep_w = LOWER_THIRD_SEPARATOR_WIDTH
        margin_w = LOWER_THIRD_TEXT_MARGIN * 2  # left padding + right margin in band
        margin_h = LOWER_THIRD_TEXT_MARGIN * 2   # vertical padding in text column

        text_w = self.width() - logo_w - sep_w - margin_w
        text_h = band_h - margin_h

        return max(1, text_w), max(1, text_h)

    def _fit_lower_third_fonts(self, verse_text, ref_text):
        """Binary search for the largest font size that fits the lower-third band.

        Reference font is LOWER_THIRD_REF_FONT_RATIO of verse font.
        Uses display mode in cache key for disambiguation.
        """
        avail_w, avail_h = self._lower_third_available_area()
        if avail_w <= 0 or avail_h <= 0:
            self._lt_verse_label.setFont(QFont("Segoe UI", 16))
            self._lt_ref_label.setFont(QFont("Segoe UI", 10))
            return

        cache_key = (self._display_mode, hash(verse_text), hash(ref_text), avail_w, avail_h)
        if cache_key in self._fit_cache:
            verse_font_size = self._fit_cache[cache_key]
        else:
            # Cap max font for lower-third (band is ~28% of screen)
            max_font = min(64, max(16, avail_h // 3))
            min_font = 10
            best = min_font

            max_iters = math.ceil(math.log2(max_font - min_font + 1)) + 1
            for _ in range(max_iters):
                if min_font > max_font:
                    break
                mid = (min_font + max_font) // 2
                ref_font_size = max(8, int(mid * LOWER_THIRD_REF_FONT_RATIO))

                # Measure reference height
                ref_fm = QFont("Segoe UI", ref_font_size, QFont.Weight.Bold)
                ref_h = self._measure_wrapped_text_height(ref_text, ref_fm, avail_w)

                # Measure verse height
                verse_fm = QFont("Segoe UI", mid)
                verse_h = self._measure_wrapped_text_height(verse_text, verse_fm, avail_w)

                # Total: ref + verse + spacing between them (4px)
                total_h = ref_h + verse_h + 4
                if total_h <= avail_h:
                    best = mid
                    min_font = mid + 1
                else:
                    max_font = mid - 1

            self._fit_cache[cache_key] = best
            if len(self._fit_cache) > 50:
                self._fit_cache.pop(next(iter(self._fit_cache)))
            verse_font_size = best

        ref_font_size = max(8, int(verse_font_size * LOWER_THIRD_REF_FONT_RATIO))
        self._lt_verse_label.setFont(QFont("Segoe UI", verse_font_size))
        self._lt_ref_label.setFont(QFont("Segoe UI", ref_font_size, QFont.Weight.Bold))

    def paintEvent(self, event):
        """Paint the lower-third semi-transparent band when in lower-third mode.

        Fullscreen mode delegates to Qt's default painting.
        """
        if self._display_mode != DISPLAY_MODE_LOWER_THIRD:
            super().paintEvent(event)
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        band_h = int(self.height() * LOWER_THIRD_HEIGHT_RATIO)
        band_y = self.height() - band_h

        # Semi-transparent dark band
        bg_alpha = int(255 * LOWER_THIRD_BACKGROUND_ALPHA)
        painter.fillRect(0, band_y, self.width(), band_h,
                         QColor(10, 10, 10, bg_alpha))

        # Optional: gradient fade above band (future polish)
        # fade_h = 40
        # gradient = QLinearGradient(0, band_y - fade_h, 0, band_y)
        # gradient.setColorAt(0, QColor(10, 10, 10, 0))
        # gradient.setColorAt(1, QColor(10, 10, 10, bg_alpha))
        # painter.fillRect(0, band_y - fade_h, self.width(), fade_h, gradient)

        painter.end()

    def _apply_lower_third_window_state(self):
        """Configure window for lower-third display mode.

        Sets frameless window + translucent background, positions at the
        target screen with full dimensions so the band sits at the bottom
        while the top remains transparent (desktop shows through).
        """
        # Exit fullscreen before changing window flags — prevents Win32
        # from restoring fullscreen geometry when show() is called.
        self.showNormal()
        self._is_fullscreen = False

        screen = self._target_screen or self.screen()
        geo = screen.geometry()
        self.hide()
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setGeometry(geo)
        self.show()

        # Reapply theme — lower-third needs transparent QMainWindow background
        # instead of the fullscreen opaque gradient.
        self._apply_theme_styling()

    def _on_layout_changed(self, mode):
        """Update display layout based on layout mode."""
        self._layout_mode = mode
        # Future: implement different layout templates
        # For now, single verse layout works for all modes

    def _start_fade(self):
        """Instant display update — no fade animation to avoid desktop flash."""
        self.setWindowOpacity(1.0)

    def resizeEvent(self, event):
        """Recalculate font sizes proportionally when the window is resized.

        Reference label updates immediately (cheap). Verse content re-render is
        debounced because resize events fire 60-120 times/second during drag,
        and each re-render runs binary search + ~7 QTextDocument measurements.
        """
        super().resizeEvent(event)

        # Proportional reference scaling — cheap, run every event (fullscreen only)
        if self._display_mode == DISPLAY_MODE_FULLSCREEN:
            window_height = self.height()
            new_ref_size = max(24, min(60, window_height // 22))
            font = self.ref_label.font()
            font.setPointSize(new_ref_size)
            self.ref_label.setFont(font)

        # Update lower-third geometry on resize (ratio-based sizes change)
        if self._display_mode == DISPLAY_MODE_LOWER_THIRD:
            self._update_lower_third_geometry()

        # Viewport changed → invalidate fit cache.
        self._fit_cache.clear()

        # Debounce expensive verse re-render until resize settles.
        if self.display.current and self._is_live:
            self._resize_timer.start(self.RESIZE_DEBOUNCE_MS)

    def _handle_resize_finished(self):
        """Re-render verse content after the resize event stream settles."""
        if self.display.current and self._is_live:
            self._render_verse_content(self.display.current)

    def _apply_theme_styling(self):
        """Apply theme-based styling to display elements."""
        theme = self.theme_mgr.current
        if not theme:
            self._apply_default_styling()
            return

        c = theme.c

        # Lower-third: transparent background so desktop shows through above the band.
        # Fullscreen: gradient background fills the entire window.
        bg_value = "transparent" if self._display_mode == DISPLAY_MODE_LOWER_THIRD else \
                   f"qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {c('bg_primary')}, stop:1 {c('bg_secondary')})"

        self.setStyleSheet(f"""
            QMainWindow {{
                background: {bg_value};
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
            letter-spacing: 5px;
            padding: 6px 0 10px 0;
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
        bg_value = "transparent" if self._display_mode == DISPLAY_MODE_LOWER_THIRD else \
                   "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #0f0f1a, stop:1 #0a0a14)"

        self.setStyleSheet(f"""
            QMainWindow {{
                background: {bg_value};
            }}
            QWidget {{
                background: transparent;
                color: #e8e2d8;
            }}
        """)

        self.ref_label.setStyleSheet("""
            color: #c8a03c;
            background: transparent;
            letter-spacing: 5px;
            padding: 6px 0 10px 0;
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

    def set_display_mode(self, mode: str):
        """Set the rendering display mode.

        Valid modes are DISPLAY_MODE_FULLSCREEN and DISPLAY_MODE_LOWER_THIRD.
        Changing the mode invalidates cached font sizes, switches the
        QStackedWidget page, updates window flags/attributes, and re-renders
        the current verse if the display is live.
        """
        valid = (DISPLAY_MODE_FULLSCREEN, DISPLAY_MODE_LOWER_THIRD)
        if mode not in valid:
            return
        if mode == self._display_mode:
            return
        self._display_mode = mode
        self._fit_cache.clear()

        # Switch window flags/attributes if live
        if self._is_live:
            if mode == DISPLAY_MODE_LOWER_THIRD:
                # Clear fullscreen labels to prevent ghost content
                self._clear_verse_content()
                self.ref_label.setText("")
                self._apply_lower_third_window_state()
            else:
                # Clear lower-third labels to prevent ghost content
                self._lt_ref_label.setText("")
                self._lt_verse_label.setText("")
                
                self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
                self.hide()
                self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.WindowStaysOnTopHint)
                
                # Force native window handle recreation to clear corrupted 
                # WS_EX_LAYERED compositor state from the lower-third mode.
                self.winId()
                
                # Need to grab geometry here as self.screen() may fail while hidden
                screen = self._target_screen or self.screen()
                geo = screen.geometry()
                self.setGeometry(geo)
                self.showFullScreen()
                self._is_fullscreen = True

            # Switch QStackedWidget page
            if mode == DISPLAY_MODE_LOWER_THIRD:
                self._stacked.setCurrentIndex(1)
            else:
                self._stacked.setCurrentIndex(0)

            # Reapply theme — lower-third needs transparent background
            self._apply_theme_styling()
            self._render_verse_content(self.display.current)
        else:
            # Switch QStackedWidget page if not live
            if mode == DISPLAY_MODE_LOWER_THIRD:
                self._stacked.setCurrentIndex(1)
            else:
                self._stacked.setCurrentIndex(0)

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
        if self._display_mode == DISPLAY_MODE_LOWER_THIRD:
            if event.key() == Qt.Key.Key_Escape:
                self.display.clear()  # triggers _on_verse_changed({}) → close()
            return  # F11 and other keys are no-ops in lower-third
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
        """Double-click to toggle fullscreen (fullscreen mode only)."""
        if self._display_mode == DISPLAY_MODE_LOWER_THIRD:
            return  # no-op in lower-third
        self.toggle_fullscreen()
        super().mouseDoubleClickEvent(event)
