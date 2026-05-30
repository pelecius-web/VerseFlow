"""display_widget.py — VerseFlow Congregation Display Widget (Rendering Core)

Extracted from display_window.py in Phase 1. Contains all rendering logic,
font fitting, widget construction, and theme application. DisplayWindow
retains only window-management responsibilities (flags, fullscreen, headless,
resize, NDI grab surface).
"""

import logging
import math
from typing import Optional

from PyQt6.QtCore import Qt, QTimer, QAbstractAnimation, QRect
from PyQt6.QtGui import QFont, QColor, QPainter, QPixmap, QFontMetrics, QTextDocument, QTextOption
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QFrame, QScrollArea,
    QStackedWidget,
)

from constants import (
    DISPLAY_MODE_FULLSCREEN, DISPLAY_MODE_LOWER_THIRD,
    LOWER_THIRD_HEIGHT_RATIO, LOWER_THIRD_LOGO_WIDTH_RATIO,
    LOWER_THIRD_LOGO_MAX_HEIGHT_RATIO, LOWER_THIRD_SEPARATOR_WIDTH,
    LOWER_THIRD_TEXT_MARGIN, LOWER_THIRD_REF_ROW_HEIGHT,
    LOWER_THIRD_REF_FONT_MAX, LOWER_THIRD_REF_FONT_RATIO,
    LOWER_THIRD_CHURCH_NAME_FONT_MAX,
    LOWER_THIRD_CHURCH_NAME_SPACING, LOWER_THIRD_BACKGROUND_ALPHA,
)
from db_layer import abbreviate_translation
from theme import WEIGHT_MAP

logger = logging.getLogger("VerseFlow")


class DisplayWidget(QWidget):
    """Self-contained rendering core for the congregation display.

    Owns all display-mode rendering (fullscreen and lower-third), font fitting,
    widget construction, logo infrastructure, and theme application.

    DisplayWindow delegates all rendering calls to this widget. Per-channel
    theme isolation is achieved by applying stylesheets via self.setStyleSheet()
    (scoped to this widget subtree only — never QApplication).
    """

    LAYOUT_GAP = 16
    SAFETY_BUFFER = 4
    BLOCK_MARGIN = 6

    def __init__(self, display_controller, theme_manager=None,
                 church_name: str = "", parent=None):
        super().__init__(parent)
        self.display = display_controller
        self.theme_mgr = theme_manager
        self._theme = None            # per-channel; set via set_theme()
        self._church_name = church_name
        self._display_mode = DISPLAY_MODE_FULLSCREEN
        self._layout_mode = "single"
        self._overlay_labels = []
        self._fit_cache = {}
        self._logo_path_override = None  # per-channel logo; never mutates Theme object
        self._bg_renderer = self._BackgroundImageRenderer()

        # Translation debounce timer (moved from DisplayWindow — O3 fix)
        self._translations_update_timer = QTimer(self)
        self._translations_update_timer.setSingleShot(True)
        self._translations_update_timer.setInterval(0)
        self._translations_update_timer.timeout.connect(self._do_translations_update)

        # Build stacked layout
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        self._stacked = QStackedWidget(self)
        outer.addWidget(self._stacked)

        self._fullscreen_page = QWidget()
        self._build_fullscreen_page()
        self._stacked.addWidget(self._fullscreen_page)   # Page 0

        self._lt_page = QWidget()
        self._build_lower_third_page()
        self._stacked.addWidget(self._lt_page)           # Page 1

        self._stacked.setCurrentIndex(0)

        # Connect controller signals (read-only)
        self.display.layout_changed.connect(self._on_layout_changed)
        self.display.translations_changed.connect(self._on_translations_changed)

        self._apply_theme_styling()

    @property
    def theme(self):
        """Public property to read active theme."""
        return self._theme

    @property
    def display_mode(self):
        """Public property to read current display mode."""
        return self._display_mode

    # ── New methods (not in original display_window.py) ──────────────────────

    def set_theme(self, theme):
        """Apply a per-channel Theme object and refresh affected widgets.

        Clears _fit_cache because font families may change (O5 fix).
        Refreshes logo widget if logo_path changed.
        Refreshes ref_label font from fullscreen.ref_font_family/weight (B2 fix).
        Triggers a single repaint.
        Idempotent — calling with the same theme twice repaints only.

        Uses self.setStyleSheet() — scoped to this widget subtree only.
        Never calls QApplication.setStyleSheet().
        """
        self._theme = theme
        self._fit_cache.clear()
        # Stop any active fade animation and clear effects (Step 5.2)
        if hasattr(self, '_fade_anim') and self._fade_anim is not None:
            if self._fade_anim.state() == QAbstractAnimation.State.Running:
                self._fade_anim.stop()
            self._fade_anim = None
        if self._display_mode == DISPLAY_MODE_LOWER_THIRD:
            self._lt_text_column.setGraphicsEffect(None)
        else:
            self.verse_content.setGraphicsEffect(None)
        self._bg_renderer.clear_cache()
        self._refresh_logo()
        self._refresh_ref_label_font()
        self._apply_theme_styling()
        if self.display.current:
            self._render_verse_content(self.display.current)
        self.update()

    def _refresh_ref_label_font(self):
        """Update the fullscreen ref_label font from theme.fullscreen.

        B2 fix: ref_font_family and ref_font_weight on the theme were
        previously dead — _build_fullscreen_page hardcodes the initial
        QFont. After set_theme(), pull the actual values from the theme.
        """
        if self._theme is None:
            return
        fs = self._theme.fullscreen
        family = fs.get("ref_font_family", "Segoe UI")
        weight_name = fs.get("ref_font_weight", "Black")
        weight = WEIGHT_MAP.get(weight_name, 900)  # 900 = QFont.Weight.Black
        # Preserve the current point size — only update family and weight
        current_size = self.ref_label.font().pointSize()
        if current_size <= 0:
            current_size = 32
        font = QFont(family, current_size)
        font.setWeight(weight)
        self.ref_label.setFont(font)

    def _resolve_theme_path(self, relative_path: str):
        """Resolve a relative theme image path to an absolute Path, or None if missing.

        Theme images are stored relative to the themes/ directory (Decision 6).
        The theme file lives in utils/themes/<theme_id>.json, so sibling paths
        resolve from utils/themes/.
        """
        from pathlib import Path as _Path
        if not relative_path:
            return None
        abs_path = (_Path(__file__).resolve().parent.parent / "utils" / "themes" / relative_path)
        return abs_path if abs_path.exists() else None

    def set_display_mode(self, mode: str):
        """Set the rendering display mode.

        Handles stacked page switch, theme styling, cache invalidation,
        and widget update. Window flags are NOT handled here — those stay
        on DisplayWindow.
        """
        valid = (DISPLAY_MODE_FULLSCREEN, DISPLAY_MODE_LOWER_THIRD)
        if mode not in valid:
            return
        if mode == self._display_mode:
            return
        self._display_mode = mode
        self._fit_cache.clear()

        if mode == DISPLAY_MODE_LOWER_THIRD:
            self._stacked.setCurrentIndex(1)
        else:
            self._stacked.setCurrentIndex(0)

        self._apply_theme_styling()
        self.update()

    def set_church_name(self, church_name: str):
        """Update the church name displayed in the lower-third band."""
        self._church_name = church_name
        self._lt_church_label.setText(church_name)
        self._fit_church_name_font(church_name)

    def set_logo_path(self, path: str | None) -> None:
        """Update logo from an external path (channel-level override).

        Stored in self._logo_path_override — never mutates the shared Theme object.
        """
        self._logo_path_override = path
        self._refresh_logo()

    def _refresh_logo(self):
        """Swap the logo widget in-place, preserving layout index 0."""
        new_widget = self._build_logo_widget()
        if new_widget is None:
            return
        layout = self._lt_logo_container.layout()
        old_item = layout.takeAt(0)
        if old_item and old_item.widget():
            old_item.widget().deleteLater()
        layout.insertWidget(0, new_widget)
        self._lt_logo = new_widget
        self._update_lower_third_geometry()

    def _build_logo_widget(self):
        """Factory: create the logo widget from override, theme, or placeholder.

        Priority: self._logo_path_override (set via set_logo_path()) takes
        precedence over theme.lower_third.logo_path. This avoids mutating
        the shared Theme object, which would contaminate the other channel
        and all future get_theme() calls for the same theme ID. (I2 fix)

        Supports SVG via QSvgWidget, raster images via QPixmap, and a styled
        QFrame placeholder when no logo is configured. Falls back to placeholder
        when the file is missing or the pixmap is null.
        """
        lt = self._theme.lower_third if self._theme else {}
        logo_path_str = self._logo_path_override or lt.get("logo_path")
        show_placeholder = lt.get("show_logo_placeholder", True)

        if logo_path_str:
            from pathlib import Path as _Path
            # B1 fix: Theme stores source_path (not _source_path).
            # Resolve theme-relative paths against the theme JSON's directory.
            source_path = getattr(self._theme, 'source_path', None) if self._theme else None
            if source_path is not None:
                logo_path = (_Path(source_path).parent / logo_path_str).resolve()
            else:
                logo_path = _Path(logo_path_str)
            if str(logo_path_str).lower().endswith(".svg"):
                from PyQt6.QtSvgWidgets import QSvgWidget
                return QSvgWidget(str(logo_path))
            label = QLabel()
            px = QPixmap(str(logo_path))
            if not px.isNull():
                label.setPixmap(px)
                label.setScaledContents(True)
            return label

        if show_placeholder:
            frame = QFrame()
            frame.setObjectName("lt_logo")
            frame.setStyleSheet("""
                QFrame#lt_logo {
                    background: rgba(30, 30, 40, 0.5);
                    border: 1px solid rgba(200, 160, 60, 0.25);
                    border-radius: 4px;
                }
            """)
            return frame
        return None

    def _build_placeholder_logo(self):
        """Build the default QFrame placeholder logo widget."""
        placeholder = QFrame()
        placeholder.setObjectName("lt_logo")
        placeholder.setStyleSheet("""
            QFrame#lt_logo {
                background: rgba(30, 30, 40, 0.5);
                border: 1px solid rgba(200, 160, 60, 0.25);
                border-radius: 4px;
            }
        """)
        return placeholder

    # ── Signal handlers ──────────────────────────────────────────────────────

    def _on_layout_changed(self, mode):
        """Update display layout based on layout mode."""
        self._layout_mode = mode

    def _on_translations_changed(self, translations):
        """Coalesce rapid translation-changed signals into a single re-render."""
        if self.display.current:
            self._translations_update_timer.start()

    def _do_translations_update(self):
        """Perform the actual re-render after all translation changes have settled."""
        if self.display.current:
            self._render_verse_content(self.display.current)
            self._start_fade(*self._get_fade_params())

    # ── Deferred rendering ───────────────────────────────────────────────────

    def _deferred_render(self, verse):
        """Render verse content after geometry has settled.

        Called by DisplayWindow._on_verse_changed via QTimer.singleShot so that
        showFullScreen()/resize() events have been processed.
        """
        try:
            self._render_verse_content(verse)
        except Exception as e:
            logger.error("ERROR rendering verse: %s", e, exc_info=True)
            return
        self._start_fade(*self._get_fade_params())

    def _get_fade_params(self):
        """Read transition settings from the per-channel theme.

        Returns (duration_ms, easing_name) if transition.type == "fade",
        otherwise (0, "OutCubic") — which _start_fade treats as a no-op.
        """
        if self._theme is None:
            return (0, "OutCubic")
        transition = self._theme.lower_third.get("transition", {})
        if transition.get("type") != "fade":
            return (0, "OutCubic")
        duration = int(transition.get("duration_ms", 200))
        easing = transition.get("easing", "OutCubic")
        return (duration, easing)

    def _start_fade(self, duration_ms: int = 0, easing_name: str = "OutCubic"):
        """Apply a fade-in opacity animation to the active content widget.

        Parameters
        ----------
        duration_ms : int
            Fade duration in milliseconds. 0 = no-op (instant display, no animation).
            Default 0 preserves existing behavior for callers that don't pass args.
        easing_name : str
            Easing curve name (default "OutCubic"). Mapped to QEasingCurve.Type.
        """
        if duration_ms <= 0:
            self.setWindowOpacity(1.0)  # no-op behavior (previous implementation)
            return

        # Get the active content widget to animate
        if self._display_mode == DISPLAY_MODE_LOWER_THIRD:
            target = self._lt_text_column
        else:
            target = self.verse_content

        # Stop any existing fade animation to prevent orphaned effects
        from PyQt6.QtWidgets import QGraphicsOpacityEffect
        from PyQt6.QtCore import QPropertyAnimation, QEasingCurve, QAbstractAnimation

        if hasattr(self, '_fade_anim') and self._fade_anim is not None:
            if self._fade_anim.state() == QAbstractAnimation.State.Running:
                self._fade_anim.stop()
        if target.graphicsEffect() is not None:
            target.setGraphicsEffect(None)

        # Create opacity effect
        effect = QGraphicsOpacityEffect(target)
        target.setGraphicsEffect(effect)

        anim = QPropertyAnimation(effect, b"opacity", target)
        anim.setDuration(duration_ms)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)

        # Map easing name to QEasingCurve.Type
        easing_map = {
            "OutCubic": QEasingCurve.Type.OutCubic,
            "InCubic": QEasingCurve.Type.InCubic,
            "InOutCubic": QEasingCurve.Type.InOutCubic,
            "Linear": QEasingCurve.Type.Linear,
        }
        anim.setEasingCurve(easing_map.get(easing_name, QEasingCurve.Type.OutCubic))

        # Store reference to prevent garbage collection
        self._fade_anim = anim
        anim.start()

    # ── Content clearing ─────────────────────────────────────────────────────

    def _clear_verse_content(self):
        """Clear all verse content from the active mode's layout."""
        if self._display_mode == DISPLAY_MODE_LOWER_THIRD:
            self._lt_ref_label.setText("")
            self._lt_verse_label.setText("")
        else:
            while self.verse_layout.count():
                item = self.verse_layout.takeAt(0)
                widget = item.widget()
                if widget:
                    widget.setParent(None)

    def _clear_all_mode_content(self):
        """Clear verse content from both fullscreen and lower-third layouts."""
        while self.verse_layout.count():
            item = self.verse_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)
        self.ref_label.setText("")
        self._lt_ref_label.setText("")
        self._lt_verse_label.setText("")

    # ── Measurement utilities ────────────────────────────────────────────────

    def _available_verse_area(self):
        """Calculate available verse area from window geometry (not stale viewport)."""
        outer_margins = 20 * 2
        outer_spacing = 8

        avail_label_width = self.width() - outer_margins
        fm = self.ref_label.fontMetrics()
        ref_text = self.ref_label.text()
        rect = fm.boundingRect(
            0, 0, avail_label_width, 9999,
            Qt.TextFlag.TextWordWrap,
            ref_text
        )
        ref_h = max(self.ref_label.minimumHeight(), rect.height() + 16)

        bottom_h = 18

        vp_w = self.width() - outer_margins
        vp_h = self.height() - outer_margins - outer_spacing - ref_h - outer_spacing - bottom_h

        return max(1, vp_w), max(1, vp_h)

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

    # ── Font fitting ─────────────────────────────────────────────────────────

    def _calc_single_font_size(self, text, font_family="Segoe UI", min_font=8, max_font=96, font_weight=400):
        """Binary search for single verse font size that fills the screen."""
        avail_w, avail_h = self._available_verse_area()
        if avail_w <= 0 or avail_h <= 0:
            return 64

        cache_key = (self._display_mode, hash(text), font_family, font_weight, avail_w, avail_h, 'single')
        if cache_key in self._fit_cache:
            return self._fit_cache[cache_key]

        layout_overhead = self.LAYOUT_GAP * 2
        available_height = avail_h - layout_overhead - self.SAFETY_BUFFER

        low, high = min_font, max_font
        best = min_font

        max_iters = math.ceil(math.log2(max_font - min_font + 1)) + 1
        for _ in range(max_iters):
            if low > high:
                break
            mid = (low + high) // 2
            font = QFont(font_family, mid, font_weight)
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

    def _calc_overlay_font_sizes(self, verses, font_family="Segoe UI", min_font=8, max_font=80, font_weight=400):
        """Binary search for largest verse_font that fits all overlay blocks."""
        avail_w, avail_h = self._available_verse_area()
        if avail_w <= 0 or avail_h <= 0:
            return min_font, max(8, int(min_font * 0.75))

        num_gaps = len(verses) + 1
        layout_overhead = self.LAYOUT_GAP * num_gaps
        available_height = avail_h - layout_overhead - self.SAFETY_BUFFER

        if available_height <= 0:
            return min_font, max(8, int(min_font * 0.75))

        verses_sig = tuple((v.get("translation", ""), hash(v.get("text", ""))) for v in verses)
        cache_key = (self._display_mode, verses_sig, font_family, font_weight, avail_w, avail_h, 'overlay')
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
            if self._overlay_content_fits(mid, trans_font, avail_w, available_height, verses, font_family, font_weight=font_weight):
                best = mid
                low = mid + 1
            else:
                high = mid - 1

        self._fit_cache[cache_key] = best
        if len(self._fit_cache) > 50:
            self._fit_cache.pop(next(iter(self._fit_cache)))
        return best, max(8, int(best * 0.75))

    def _overlay_content_fits(self, verse_font, trans_font, max_width, max_height, verses, font_family="Segoe UI", font_weight=400):
        """Simulate rendering of all overlay blocks with inline translation name."""
        v_font = QFont(font_family, verse_font, font_weight)

        padding = max(8, int(verse_font * 0.25))
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

    def _lower_third_available_area(self):
        """Calculate usable text area within the lower-third band.

        Reads height_ratio and logo_width_ratio from the per-channel theme
        when available, falling back to LOWER_THIRD_* constants.
        """
        if self._theme is not None:
            lt = self._theme.lower_third
            height_ratio = float(lt.get("height_ratio", LOWER_THIRD_HEIGHT_RATIO))
            logo_width_ratio = float(lt.get("logo_width_ratio", LOWER_THIRD_LOGO_WIDTH_RATIO))
        else:
            height_ratio = LOWER_THIRD_HEIGHT_RATIO
            logo_width_ratio = LOWER_THIRD_LOGO_WIDTH_RATIO

        band_h = int(self.height() * height_ratio)
        logo_w = int(self.width() * logo_width_ratio)
        sep_w = LOWER_THIRD_SEPARATOR_WIDTH
        v_margin = LOWER_THIRD_TEXT_MARGIN // 2
        margin_w = LOWER_THIRD_TEXT_MARGIN + LOWER_THIRD_TEXT_MARGIN

        text_w = self.width() - logo_w - sep_w - margin_w
        text_h = band_h - (v_margin * 2)

        return max(1, text_w), max(1, text_h)

    def _fit_reference_font(self, ref_text, row_height, avail_w):
        """Find the largest bold reference font that fits within a dedicated row height.

        Patch 4 (B2 extension): reads ref_font_family from self._theme.lower_third
        with safe fallback. Both measurement and final font use the same family
        so the chosen size matches what is actually rendered.
        """
        ref_family = (self._theme.lower_third.get("ref_font_family", "Segoe UI")
                      if self._theme else "Segoe UI")
        best_size = 8.0
        for half_pt in range(int(LOWER_THIRD_REF_FONT_MAX * 2), 15, -1):
            size = half_pt * 0.5
            f = QFont(ref_family)
            f.setPointSizeF(size)
            f.setWeight(QFont.Weight.Bold)
            h = self._measure_wrapped_text_height(ref_text, f, avail_w)
            if h <= row_height:
                best_size = size
                break

        for i in range(1, 5):
            candidate = best_size + (i * 0.1)
            if candidate > LOWER_THIRD_REF_FONT_MAX:
                break
            f = QFont(ref_family)
            f.setPointSizeF(candidate)
            f.setWeight(QFont.Weight.Bold)
            h = self._measure_wrapped_text_height(ref_text, f, avail_w)
            if h <= row_height:
                best_size = candidate
            else:
                break

        return best_size

    def _fit_church_name_font(self, church_text):
        """Size the church name label to fit below the square logo.

        Patch 4 (B2 extension): reads ref_font_family from self._theme.lower_third
        for the church name (it shares the gold-tinted bold styling with the
        reference label).
        """
        if not church_text:
            self._lt_church_label.setVisible(False)
            return

        ref_family = (self._theme.lower_third.get("ref_font_family", "Segoe UI")
                      if self._theme else "Segoe UI")

        container_margins = self._lt_logo_container.layout().contentsMargins()
        square_side = self._lt_logo.height()
        logo_max_h = self._lt_logo_container.maximumHeight()
        if logo_max_h == 0:
            logo_max_h = int(self.height() * LOWER_THIRD_HEIGHT_RATIO
                             * LOWER_THIRD_LOGO_MAX_HEIGHT_RATIO)

        avail_h = (logo_max_h
                   - container_margins.top() - container_margins.bottom()
                   - square_side - LOWER_THIRD_CHURCH_NAME_SPACING)
        avail_h = max(0, avail_h)

        logo_w = self._lt_logo_container.width()
        avail_w = max(1, logo_w - container_margins.left() - container_margins.right())

        best_size = 0.0
        for half_pt in range(int(LOWER_THIRD_CHURCH_NAME_FONT_MAX * 2), 13, -1):
            size = half_pt * 0.5
            f = QFont(ref_family)
            f.setPointSizeF(size)
            f.setWeight(QFont.Weight.Bold)
            h = self._measure_wrapped_text_height(church_text, f, avail_w)
            if h <= avail_h:
                best_size = size
                break

        if best_size < 7.0:
            self._lt_church_label.setVisible(False)
            return

        font = QFont(ref_family)
        font.setPointSizeF(best_size)
        font.setWeight(QFont.Weight.Bold)
        self._lt_church_label.setFont(font)
        self._lt_church_label.setVisible(True)

    def _fit_lower_third_fonts(self, verse_text, ref_text):
        """Binary search for the largest verse font that fits the lower-third band.

        Patch 4 (B2 extension): reads ref_font_family and verse_font_family from
        self._theme.lower_third (with safe fallbacks). Both measurement and final
        label fonts use the theme family so that text wrapping and the chosen
        size remain consistent with what is actually rendered.
        """
        # Pull theme font families and weights once with fallbacks
        lt = self._theme.lower_third if self._theme else {}
        verse_family = lt.get("verse_font_family", "Segoe UI")
        ref_family = lt.get("ref_font_family", "Segoe UI")
        verse_weight_name = lt.get("verse_font_weight", "Normal")
        verse_weight = WEIGHT_MAP.get(verse_weight_name, 400)
        ref_weight_name = lt.get("ref_font_weight", "Bold")
        ref_weight = WEIGHT_MAP.get(ref_weight_name, 700)

        avail_w, avail_h = self._lower_third_available_area()
        if avail_w <= 0 or avail_h <= 0:
            vf = QFont(verse_family, 16)
            vf.setWeight(verse_weight)
            self._lt_verse_label.setFont(vf)
            rf = QFont(ref_family, 10)
            rf.setWeight(ref_weight)
            self._lt_ref_label.setFont(rf)
            return

        ref_font_size = self._fit_reference_font(
            ref_text, LOWER_THIRD_REF_ROW_HEIGHT, avail_w)

        verse_avail_h = avail_h - LOWER_THIRD_REF_ROW_HEIGHT - 4 - self.SAFETY_BUFFER

        # Cache key now includes verse_family and verse_weight because different
        # font families and weights wrap differently.
        cache_key = (self._display_mode, hash(verse_text), hash(ref_text),
                     avail_w, avail_h, verse_family, verse_weight)
        if cache_key in self._fit_cache:
            verse_font_size = self._fit_cache[cache_key]
        else:
            max_font = 96
            min_font = 8
            best_int = min_font

            max_iters = math.ceil(math.log2(max_font - min_font + 1)) + 1
            for _ in range(max_iters):
                if min_font > max_font:
                    break
                mid = (min_font + max_font) // 2

                verse_fm = QFont(verse_family, mid, verse_weight)
                verse_h = self._measure_wrapped_text_height(verse_text, verse_fm, avail_w)

                if verse_h <= verse_avail_h:
                    best_int = mid
                    min_font = mid + 1
                else:
                    max_font = mid - 1

            verse_font_size = float(best_int)
            for i in range(1, 10):
                candidate = best_int + (i * 0.1)

                verse_f = QFont(verse_family)
                verse_f.setPointSizeF(candidate)
                verse_f.setWeight(verse_weight)
                verse_h = self._measure_wrapped_text_height(verse_text, verse_f, avail_w)

                if verse_h <= verse_avail_h:
                    verse_font_size = candidate
                else:
                    break

            self._fit_cache[cache_key] = verse_font_size
            if len(self._fit_cache) > 50:
                self._fit_cache.pop(next(iter(self._fit_cache)))

        verse_font = QFont(verse_family)
        verse_font.setPointSizeF(verse_font_size)
        verse_font.setWeight(verse_weight)
        self._lt_verse_label.setFont(verse_font)
        ref_font = QFont(ref_family)
        ref_font.setPointSizeF(ref_font_size)
        ref_font.setWeight(ref_weight)
        self._lt_ref_label.setFont(ref_font)

    # ── Rendering ────────────────────────────────────────────────────────────

    def _render_verse_content(self, primary_verse):
        """Dispatch verse rendering to the active display mode."""
        if self._display_mode == DISPLAY_MODE_LOWER_THIRD:
            self._render_lower_third(primary_verse)
        else:
            self._render_fullscreen(primary_verse)

    def _render_fullscreen(self, primary_verse):
        """Render verse text in fullscreen mode with overlay support.

        B2 fix: reads colors and font families from self._theme.fullscreen
        (with safe fallbacks) so theme edits in the designer produce visible
        change on the rendered display.
        """
        self._lt_ref_label.setText("")
        self._lt_verse_label.setText("")
        self._stacked.setCurrentIndex(0)

        # Pull theme values once with fallbacks
        fs = self._theme.fullscreen if self._theme else {}
        verse_color = fs.get("verse_color", self._theme.c("text_primary") if self._theme else "#e8e2d8")
        verse_family = fs.get("verse_font_family", "Segoe UI")
        verse_weight_name = fs.get("verse_font_weight", "Normal")
        verse_weight = WEIGHT_MAP.get(verse_weight_name, 400)
        ref_weight_name = fs.get("ref_font_weight", "Black")
        ref_weight = WEIGHT_MAP.get(ref_weight_name, 900)

        translations = self.display.secondary_translations
        total = 1 + len(translations)

        self._clear_verse_content()

        if total <= 1:
            verse_text = primary_verse.get("text", "")
            ref_text = primary_verse.get("reference", "")
            trans_name = primary_verse.get("translation", "")

            if trans_name:
                self.ref_label.setText(f"{ref_text} — {abbreviate_translation(trans_name)}")
            else:
                self.ref_label.setText(ref_text)

            verse_font = self._calc_single_font_size(verse_text, verse_family, font_weight=verse_weight)
            verse_label = QLabel(verse_text)
            vf = QFont(verse_family, verse_font)
            vf.setWeight(verse_weight)
            verse_label.setFont(vf)
            verse_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
            verse_label.setWordWrap(True)
            padding = max(8, int(verse_font * 0.25))
            verse_label.setStyleSheet(f"color: {verse_color}; background: transparent; padding: {padding}px;")
            self.verse_layout.addStretch(1)
            self.verse_layout.addWidget(verse_label)
            self.verse_layout.addStretch(1)
            return

        ref_text = primary_verse.get("reference", "")
        self.ref_label.setText(ref_text)

        verses_to_render = [primary_verse] + translations
        verse_font, trans_font = self._calc_overlay_font_sizes(verses_to_render, verse_family, font_weight=verse_weight)

        def add_verse_block(verse, is_primary=False):
            text = verse.get("text", "")
            padding = max(8, int(verse_font * 0.25))
            html = self._build_overlay_html(verse, trans_font, text, is_primary)
            label = QLabel(html)
            vf = QFont(verse_family, verse_font)
            vf.setWeight(verse_weight)
            label.setFont(vf)
            label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
            label.setWordWrap(True)
            label.setTextFormat(Qt.TextFormat.RichText)
            label.setStyleSheet(f"background: transparent; padding: {padding}px;")
            return label

        self.verse_layout.addStretch(1)
        self.verse_layout.addWidget(add_verse_block(primary_verse, is_primary=True))

        for overlay_verse in translations:
            self.verse_layout.addWidget(add_verse_block(overlay_verse, is_primary=False))

        self.verse_layout.addStretch(1)

    def _build_overlay_html(self, verse, trans_font, text, is_primary):
        """Build the rich text string used for overlay rendering and measurement.

        B2 fix: reads ref_color and verse_color from self._theme.fullscreen
        (with safe fallbacks). Secondary-translation tints are derived as
        slightly dimmer variants of the primary colors for visual hierarchy.
        """
        fs = self._theme.fullscreen if self._theme else {}
        primary_ref = fs.get("ref_color", self._theme.c("gold") if self._theme else "#c8a03c")
        primary_verse = fs.get("verse_color", self._theme.c("text_primary") if self._theme else "#e8e2d8")
        # Derive dimmer tints for secondary translations
        secondary_ref = self._dim_color(primary_ref)
        secondary_verse = self._dim_color(primary_verse)

        trans = abbreviate_translation(verse.get("translation", ""))
        color = primary_ref if is_primary else secondary_ref
        text_color = primary_verse if is_primary else secondary_verse
        return (
            f'<span style="color: {color}; font-size: {trans_font}px; font-weight: 700;">{trans}</span> '
            f'<span style="color: {text_color};">{text}</span>'
        )

    @staticmethod
    def _dim_color(hex_color: str) -> str:
        """Return a slightly dimmer variant of a hex color for secondary text.

        Used to derive secondary-translation tints from the primary theme colors.
        Mixes 88% original with 12% white-shifted to soften (matches the
        previous hardcoded #d4a84b → #c8a03c and #d0c8b8 → #e8e2d8 relationship).
        """
        try:
            qc = QColor(hex_color)
            if not qc.isValid():
                return hex_color
            r, g, b = qc.red(), qc.green(), qc.blue()
            r = max(0, min(255, int(r * 0.88 + 30)))
            g = max(0, min(255, int(g * 0.88 + 30)))
            b = max(0, min(255, int(b * 0.88 + 30)))
            return QColor(r, g, b).name()
        except Exception:
            return hex_color

    def _render_lower_third(self, primary_verse):
        """Render verse in lower-third band layout."""
        while self.verse_layout.count():
            item = self.verse_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)
        self.ref_label.setText("")
        self._stacked.setCurrentIndex(1)

        self._update_lower_third_geometry()

        ref_text = primary_verse.get("reference", "")
        trans_name = abbreviate_translation(primary_verse.get("translation", ""))
        if trans_name:
            display_ref = f"{ref_text} — {trans_name}"
        else:
            display_ref = ref_text
        self._lt_ref_label.setText(display_ref)

        verse_text = primary_verse.get("text", "")
        self._lt_verse_label.setText(verse_text)

        self._lt_church_label.setText(self._church_name)
        self._fit_church_name_font(self._church_name)

        self._fit_lower_third_fonts(verse_text, display_ref)

    # ── Widget construction ──────────────────────────────────────────────────

    def _build_fullscreen_page(self):
        """Construct the fullscreen layout (QStackedWidget Page 0)."""
        layout = QVBoxLayout(self._fullscreen_page)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(8)

        self.ref_label = QLabel("")
        self.ref_label.setFont(QFont("Segoe UI", 32, QFont.Weight.Black))
        self.ref_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.ref_label.setWordWrap(True)
        self.ref_label.setMinimumHeight(56)
        layout.addWidget(self.ref_label, 0)

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
        layout.addWidget(self.verse_scroll, 1)

        self.bottom_bar = QLabel("VerseFlow — v1.3.0")
        self.bottom_bar.setFont(QFont("Segoe UI", 9, QFont.Weight.Light))
        self.bottom_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.bottom_bar.setFixedHeight(18)
        layout.addWidget(self.bottom_bar)

    def _build_lower_third_page(self):
        """Construct the lower-third layout (QStackedWidget Page 1)."""
        outer = QVBoxLayout(self._lt_page)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addStretch(1)

        self._lt_band = QFrame()
        self._lt_band.setObjectName("lt_band")
        band_layout = QHBoxLayout(self._lt_band)
        band_layout.setContentsMargins(0, 0, LOWER_THIRD_TEXT_MARGIN, 0)
        band_layout.setSpacing(0)

        # Logo container
        self._lt_logo_container = QWidget()
        self._lt_logo_container.setObjectName("lt_logo_container")
        logo_container_layout = QVBoxLayout(self._lt_logo_container)
        logo_container_layout.setContentsMargins(6, 8, 6, 8)
        logo_container_layout.setSpacing(LOWER_THIRD_CHURCH_NAME_SPACING)

        self._lt_logo = self._build_placeholder_logo()
        logo_container_layout.addWidget(self._lt_logo)

        self._lt_church_label = QLabel("")
        self._lt_church_label.setObjectName("lt_church_name")
        self._lt_church_label.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
        self._lt_church_label.setWordWrap(True)
        self._lt_church_label.setVisible(False)
        self._lt_church_label.setStyleSheet("""
            QLabel#lt_church_name {
                color: #c8a03c;
                background: transparent;
                font-weight: 700;
                letter-spacing: 1px;
            }
        """)
        logo_container_layout.addWidget(self._lt_church_label)

        band_layout.addWidget(self._lt_logo_container)

        # Separator
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

        # Text column
        self._lt_text_column = QWidget()
        self._lt_text_column.setObjectName("lt_text_column")
        text_layout = QVBoxLayout(self._lt_text_column)
        v_margin = LOWER_THIRD_TEXT_MARGIN // 2
        text_layout.setContentsMargins(LOWER_THIRD_TEXT_MARGIN, v_margin, 0, v_margin)
        text_layout.setSpacing(4)

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

        band_layout.addWidget(self._lt_text_column, 1, Qt.AlignmentFlag.AlignTop)

        outer.addWidget(self._lt_band)
        self._lt_page.setStyleSheet("background: transparent;")

    def _update_lower_third_geometry(self):
        """Recalculate lower-third widget sizes based on current window geometry.

        Reads logo_width_ratio, height_ratio, logo_max_height_ratio from the
        per-channel theme when available, falling back to LOWER_THIRD_* constants.
        """
        w = self.width()
        h = self.height()

        if self._theme is not None:
            lt = self._theme.lower_third
            height_ratio = float(lt.get("height_ratio", LOWER_THIRD_HEIGHT_RATIO))
            logo_width_ratio = float(lt.get("logo_width_ratio", LOWER_THIRD_LOGO_WIDTH_RATIO))
            logo_max_height_ratio = float(lt.get("logo_max_height_ratio", LOWER_THIRD_LOGO_MAX_HEIGHT_RATIO))
        else:
            height_ratio = LOWER_THIRD_HEIGHT_RATIO
            logo_width_ratio = LOWER_THIRD_LOGO_WIDTH_RATIO
            logo_max_height_ratio = LOWER_THIRD_LOGO_MAX_HEIGHT_RATIO

        band_h = int(h * height_ratio)
        logo_w = int(w * logo_width_ratio)
        logo_max_h = int(band_h * logo_max_height_ratio)

        self._lt_logo_container.setFixedWidth(logo_w)
        self._lt_logo_container.setMaximumHeight(logo_max_h)

        container_margins = self._lt_logo_container.layout().contentsMargins()
        inner_w = logo_w - container_margins.left() - container_margins.right()
        square_side = max(1, inner_w)
        self._lt_logo.setFixedSize(square_side, square_side)

        church_text = self._lt_church_label.text()
        if church_text:
            self._fit_church_name_font(church_text)

        self._lt_band.setFixedHeight(band_h)

    # ── Theme application ────────────────────────────────────────────────────

    def _apply_theme_styling(self):
        """Apply per-channel theme styling via self.setStyleSheet().

        Uses self._theme (per-channel), never theme_mgr.current (global).
        Stylesheet is scoped to this widget subtree only.
        """
        if self._theme is None:
            self._apply_default_styling()
            return

        c = self._theme.c

        bg_value = "transparent" if self._display_mode == DISPLAY_MODE_LOWER_THIRD else \
                   f"qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {c('bg_primary')}, stop:1 {c('bg_secondary')})"

        self.setStyleSheet(f"""
            DisplayWidget {{
                background: {bg_value};
            }}
            DisplayWidget QWidget {{
                color: {c('text_primary')};
                background: transparent;
            }}
        """)

        self.ref_label.setStyleSheet(f"""
            color: {self._theme.fullscreen.get("ref_color", c("gold"))};
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

        # Lower-third labels
        self._lt_ref_label.setStyleSheet(f"""
            color: {self._theme.lower_third.get("ref_color", c("gold"))};
            background: transparent;
            font-weight: 700;
            letter-spacing: 2px;
        """)
        self._lt_verse_label.setStyleSheet(f"""
            color: {self._theme.lower_third.get("verse_color", c("text_primary"))};
            background: transparent;
        """)
        self._lt_church_label.setStyleSheet(f"""
            color: {c('gold')};
            background: transparent;
            font-weight: 700;
            letter-spacing: 1px;
        """)
        self._lt_separator.setStyleSheet(f"""
            background: {c('gold')};
            border: none;
        """)

    def _apply_default_styling(self):
        """Apply default dark theme styling if no theme is loaded."""
        bg_value = "transparent" if self._display_mode == DISPLAY_MODE_LOWER_THIRD else \
                   "qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #0f0f1a, stop:1 #0a0a14)"

        self.setStyleSheet(f"""
            DisplayWidget {{
                background: {bg_value};
            }}
            DisplayWidget QWidget {{
                color: #e8e2d8;
                background: transparent;
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

        # Lower-third label defaults
        self._lt_ref_label.setStyleSheet("""
            color: #c8a03c;
            background: transparent;
            font-weight: 700;
            letter-spacing: 2px;
        """)
        self._lt_verse_label.setStyleSheet("""
            color: #e8e2d8;
            background: transparent;
        """)
        self._lt_church_label.setStyleSheet("""
            color: #c8a03c;
            background: transparent;
            font-weight: 700;
            letter-spacing: 1px;
        """)
        self._lt_separator.setStyleSheet("""
            background: rgba(200, 160, 60, 0.6);
            border: none;
        """)

    # ── Background image renderer ────────────────────────────────────────────

    class _BackgroundImageRenderer:
        """Paints a Theme background image (PNG, JPEG, SVG) onto a target rect.

        Caches decoded pixmaps at native file resolution; scaling happens
        at paint time so one cached entry serves any target size.
        Uses QSvgRenderer for SVG files to avoid QtSvg dependency issues
        with QPixmap.
        MAX_CACHE_ENTRIES = 16  LRU eviction prevents unbounded growth.
        """

        MAX_CACHE_ENTRIES = 16

        def __init__(self):
            from collections import OrderedDict
            self._cache = OrderedDict()

        def paint(self, painter, rect, image_path, fit_mode, opacity):
            """Paint the image into rect. No-op if image_path is empty or invalid."""
            if not image_path:
                return
            target_w = rect.width()
            target_h = rect.height()
            cache_key = (str(image_path), fit_mode)  # Cache decoded pixmap at native resolution; scale at paint time

            pixmap = self._get_cached(cache_key, image_path)
            if pixmap is None or pixmap.isNull() or pixmap.width() == 0 or pixmap.height() == 0:
                return

            painter.save()
            painter.setOpacity(opacity)

            if fit_mode == "cover":
                scaled = pixmap.scaled(target_w, target_h,
                    Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                    Qt.TransformationMode.SmoothTransformation)
                # Center-crop
                x = (scaled.width() - target_w) // 2
                y = (scaled.height() - target_h) // 2
                source_rect = QRect(x, y, target_w, target_h)
                painter.drawPixmap(rect, scaled, source_rect)
            elif fit_mode == "contain":
                scaled = pixmap.scaled(target_w, target_h,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation)
                # Center
                x = (target_w - scaled.width()) // 2
                y = (target_h - scaled.height()) // 2
                painter.drawPixmap(x, y, scaled)
            elif fit_mode == "stretch":
                scaled = pixmap.scaled(target_w, target_h,
                    Qt.AspectRatioMode.IgnoreAspectRatio,
                    Qt.TransformationMode.SmoothTransformation)
                painter.drawPixmap(rect.topLeft(), scaled)
            elif fit_mode == "tile":
                # Tile from top-left (guard against zero-dimension pixmap)
                pw, ph = pixmap.width(), pixmap.height()
                if pw > 0 and ph > 0:
                    for y in range(rect.y(), rect.y() + target_h, ph):
                        for x in range(rect.x(), rect.x() + target_w, pw):
                            painter.drawPixmap(x, y, pixmap)

            painter.restore()

        def _get_cached(self, key, path):
            """Return cached QPixmap, decoding on miss. LRU eviction at MAX_CACHE_ENTRIES."""
            if key in self._cache:
                self._cache.move_to_end(key)
                return self._cache[key]
            pixmap = self._decode(path)
            if pixmap is not None:
                self._cache[key] = pixmap
                if len(self._cache) > self.MAX_CACHE_ENTRIES:
                    self._cache.popitem(last=False)
            return pixmap

        def _decode(self, path):
            """Decode image file. SVG via QSvgRenderer, raster via QPixmap."""
            path_str = str(path)
            if path_str.lower().endswith(".svg"):
                try:
                    from PyQt6.QtSvg import QSvgRenderer
                    from PyQt6.QtGui import QImage
                    renderer = QSvgRenderer(path_str)
                    if not renderer.isValid():
                        return None
                    size = renderer.defaultSize()
                    if size.width() <= 0 or size.height() <= 0:
                        return None
                    image = QImage(size, QImage.Format.Format_ARGB32)
                    image.fill(0)
                    from PyQt6.QtGui import QPainter as _QPainter
                    p = _QPainter(image)
                    renderer.render(p)
                    p.end()
                    return QPixmap.fromImage(image)
                except ImportError:
                    return None  # QtSvg not available
            else:
                px = QPixmap(path_str)
                return px if not px.isNull() else None

        def clear_cache(self):
            """Drop all cached pixmaps. Called on theme change."""
            self._cache.clear()

    # ── paintEvent ───────────────────────────────────────────────────────────

    def paintEvent(self, event):
        """Paint the lower-third semi-transparent band when in lower-third mode.

        Fullscreen mode delegates to Qt's default painting.
        """
        if self._display_mode != DISPLAY_MODE_LOWER_THIRD:
            super().paintEvent(event)
            # Fullscreen: paint background image on top of stylesheet, before child widgets
            if self._theme is not None:
                fs = self._theme.fullscreen
                bg_img = fs.get("background_image")
                if bg_img:
                    bg_path = self._resolve_theme_path(bg_img)
                    if bg_path:
                        from PyQt6.QtGui import QPainter as _QPainter
                        p = _QPainter(self)
                        self._bg_renderer.paint(
                            p, self.rect(), bg_path,
                            fs.get("background_image_fit", "cover"),
                            float(fs.get("background_image_opacity", 1.0)))
                        p.end()
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Source)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 0))

        if self._theme is not None:
            lt = self._theme.lower_third
            bg_hex     = lt.get("background_color", "#0a0a0a")
            bg_alpha   = float(lt.get("background_alpha", LOWER_THIRD_BACKGROUND_ALPHA))
            height_ratio = float(lt.get("height_ratio", LOWER_THIRD_HEIGHT_RATIO))
        else:
            bg_hex       = "#0a0a0a"
            bg_alpha     = LOWER_THIRD_BACKGROUND_ALPHA
            height_ratio = LOWER_THIRD_HEIGHT_RATIO

        band_h = int(self.height() * height_ratio)
        band_y = self.height() - band_h
        band_rect = QRect(0, band_y, self.width(), band_h)

        # Lower-third: paint background image first, then color overlay on top.
        # The semi-transparent color overlay guarantees text readability regardless
        # of the background image's brightness. Child widgets (labels) paint after
        # painter.end() and render on top of both layers.
        if self._theme is not None:
            bg_img = self._theme.lower_third.get("background_image")
            if bg_img:
                bg_path = self._resolve_theme_path(bg_img)
                if bg_path:
                    self._bg_renderer.paint(
                        painter, band_rect, bg_path,
                        self._theme.lower_third.get("background_image_fit", "cover"),
                        float(self._theme.lower_third.get("background_image_opacity", 1.0)))

        color = QColor(bg_hex)
        color.setAlphaF(bg_alpha)
        painter.fillRect(band_rect, color)

        painter.end()
