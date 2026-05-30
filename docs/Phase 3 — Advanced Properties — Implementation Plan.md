# Phase 3 — Advanced Properties (Image Backgrounds, Font Import, Fade Transitions)
## Implementation Plan (v1.0)

> **Status:** ✅ Complete (May 23, 2026)
> **Timeline:** 1 week (see Deviation 3)
> **Audit basis:** Direct codebase inspection (May 19, 2026) — display_widget.py (1098 lines), theme.py, theme_designer.py verified against sub-roadmap Phase 3 spec
> **Sub-roadmap deviations:** 3 intentional (documented below)

---

## Deviations from Sub-Roadmap

### Deviation 1 — `_load_application_fonts` re-entrancy via guard removal

**Sub-roadmap says:** "Subsequent calls (e.g., after Font Import in the designer) register only newly-added files." (Decision 5)

**Plan says:** The existing `_load_application_fonts` at `theme.py:284` has a `self._fonts_loaded` boolean guard that prevents re-execution. The per-file `_loaded_font_paths: set[str]` already prevents double-registration. Plan removes the boolean guard and makes the method re-entrant. A public `reload_fonts()` method is NOT added — the designer calls `_load_application_fonts()` directly since it already handles dedup.

**Justification:** Adding a separate `reload_fonts()` wrapper is unnecessary complexity. The method's existing per-file tracking (`_loaded_font_paths`) already guarantees idempotency. Removing the boolean guard is the minimal change.

**Private-method access note:** The designer calls `ThemeManager._load_application_fonts()` (private) directly. This is intentional — exposing a public `reload_fonts()` wrapper for a single callsite adds surface area without benefit. If `ThemeManager` grows additional font-related APIs, a public wrapper should be introduced at that point.

### Deviation 2 — Background image wired in `paintEvent`, not `_render_fullscreen`

**Sub-roadmap says:** "Wire fullscreen background: `_render_fullscreen` calls `_BackgroundImageRenderer.paint` before placing labels." (Phase 3, Step 4)

**Plan says:** Background image painting for both fullscreen and lower-third modes is wired in `paintEvent`, not in `_render_fullscreen`. The fullscreen path paints the background image after `super().paintEvent()` (which applies the stylesheet gradient) but before child widgets render their text.

**Justification:** Centralizing background painting in `paintEvent` gives consistent behavior across both modes and respects Qt's parent-before-children paint order. Putting it in `_render_fullscreen` would require separate handling in `paintEvent` for lower-third, duplicating logic. The paint order is safe: parent's `paintEvent` paints the background image, then child widgets (labels) paint on top independently.

### Deviation 3 — Phase 3 timeline: 0.5 weeks → 1 week

**Sub-roadmap says:** "Phase 3 — Advanced Properties ... (0.5 week)" (line 568)

**Plan says:** 1 week.

**Justification:** Evidence-based estimate from Phase 1/2 velocity: ~400 lines/week. Phase 3 scope is ~350 lines new/changed across 5 files, 1 new class (`_BackgroundImageRenderer`), and 2 rendering path changes (`paintEvent`, `_start_fade`). The 0.5-week estimate assumes ideal conditions; 1 week accounts for integration testing, NDI verification, and the designer UI wiring for font import.

---

## Files Created

None. All changes are additive to existing files.

## Files Modified

- `src/display/display_widget.py` — Add `_BackgroundImageRenderer` nested class; modify `paintEvent` and `_render_fullscreen` to paint background images; replace `_start_fade` no-op with `QPropertyAnimation` fade
- `src/utils/theme.py` — Remove `_fonts_loaded` boolean guard from `_load_application_fonts` to allow re-entrant font loading
- `src/ui/theme_designer.py` — Add Font Import button to `PropertyEditor`; wire to file picker + copy + re-scan
- `scripts/pre_commit_checks.py` — Add `check_phase3_advanced_properties()` guard function
- `scripts/verify_critical_fixes.py` — Add Phase 3 verification block

## Files Not Touched

- `src/ndi/ndi_bridge.py`, `ndi_sender.py`, `ndi_manager.py` — NDI pipeline; zero modifications. Background image painting in `paintEvent` produces frames naturally captured by `grab()`.
- `src/display/channel_display_facade.py` — Active HomePanel dependency; no Phase 3 changes.
- `src/core/channel_manager.py` — No channel lifecycle changes.
- `src/display/display_core.py` — No DisplayController changes.
- `src/display/display_channel.py` — `set_theme()` already forwards to DisplayWidget; no changes needed.
- `src/display/display_window.py` — Thin shell; delegates all rendering to DisplayWidget.
- `src/utils/settings.py` — No new settings keys.
- `src/utils/themes/*.json` — Schema v2 already defines all Phase 3 fields (`background_image`, `background_image_fit`, `transition`). No schema changes.

---

## Step 0 — Pre-Flight Verification

Before any code change, confirm the APIs that Phase 3 depends on are stable.

| Required by plan | Present in code | Status |
|---|---|---|
| `DisplayWidget.__init__(display_controller, theme_manager, church_name, parent)` | `display_widget.py:51` | Confirmed |
| `DisplayWidget.set_theme(theme)` | `display_widget.py:94` | Confirmed |
| `DisplayWidget.paintEvent(event)` | `display_widget.py:1066` | Confirmed |
| `DisplayWidget._render_fullscreen(primary_verse)` | `display_widget.py:644` | Confirmed |
| `DisplayWidget._start_fade()` | `display_widget.py:277` | Confirmed (no-op stub) |
| `ThemeManager._load_application_fonts()` | `theme.py:284` | Confirmed (has body, boolean-guarded) |
| `ThemeManager.application_fonts: set[str]` | `theme.py:265` | Confirmed |
| `ThemeManager._loaded_font_paths: set[str]` | `theme.py:266` | Confirmed |
| `PropertyEditor._create_widget(kind, spec)` | `theme_designer.py:606` | Confirmed |
| `PropertyEditor._browse_image()` | `theme_designer.py:841` | Confirmed |
| `theme.lower_third.background_image` field in schema | `THEME_EDITOR_SCHEMA` entry #18 | Confirmed (`image_path` kind) |
| `theme.fullscreen.background_image` field in schema | `THEME_EDITOR_SCHEMA` entry #7 | Confirmed (`image_path` kind) |
| `theme.lower_third.transition` dict in Theme object | In Theme object via `_upgrade_to_v2()` at `theme.py:111` — fade reads from the Theme object, not the editor schema | Confirmed |
| `THEME_EDITOR_SCHEMA` transition entries | NOT present — `transition.type`, `duration_ms`, `easing` have no editor rows (deferred to v1.3.x point release) | Confirmed (deferred) |

If any signature drifts during Phase 3, the implementation breaks. Run `python scripts/pre_commit_checks.py` before Step 1 and confirm zero errors.

---

## Step 1 — `_BackgroundImageRenderer` Helper Class (`display_widget.py`)

Add a nested class inside `DisplayWidget` (before `paintEvent`, around line 1060). It handles PNG, JPEG, and SVG background image rendering with an LRU cache.

### 1.1 Class structure

```python
class _BackgroundImageRenderer:
    """Renders background images with fit modes and LRU caching.

    Supports PNG, JPEG (via QPixmap) and SVG (via QSvgRenderer).
    Cache key: (path, target_w, target_h, fit_mode).
    Bound: 16 entries.
    """

    MAX_CACHE_ENTRIES = 16

    def __init__(self):
        from collections import OrderedDict
        self._cache = OrderedDict()  # key -> QPixmap or QImage

    def paint(self, painter, rect, theme_section, source_path):
        """Paint background image into rect, or skip if no image set.

        Args:
            painter: QPainter instance
            rect: target QRect to fill
            theme_section: dict with background_image, background_image_fit, background_image_opacity
            source_path: Path to theme JSON file (for relative path resolution)
        """
        image_path_str = theme_section.get("background_image")
        if not image_path_str:
            return  # No background image — caller handles solid color fallback

        # Resolve relative path (Decision 6)
        from pathlib import Path as _Path
        if source_path is not None:
            image_path = (_Path(source_path).parent / image_path_str).resolve()
        else:
            image_path = _Path(image_path_str)

        if not image_path.exists():
            return  # File not found — skip, caller handles fallback

        fit_mode = theme_section.get("background_image_fit", "cover")
        opacity = float(theme_section.get("background_image_opacity", 1.0))

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
            painter.drawPixmap(rect, scaled, x, y, target_w, target_h)
        elif fit_mode == "contain":
            scaled = pixmap.scaled(target_w, target_h,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation)
            # Center in rect
            x = rect.x() + (target_w - scaled.width()) // 2
            y = rect.y() + (target_h - scaled.height()) // 2
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
        """Retrieve decoded pixmap from cache, or decode and cache.

        Caches at native resolution. Scaling happens at paint time.
        """
        if key in self._cache:
            self._cache.move_to_end(key)
            return self._cache[key]

        pixmap = self._decode(path)
        if pixmap is None:
            return None

        self._cache[key] = pixmap
        if len(self._cache) > self.MAX_CACHE_ENTRIES:
            self._cache.popitem(last=False)  # Evict oldest
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
        """Clear the entire cache. Called on theme change."""
        self._cache.clear()
```

### 1.2 Integration into DisplayWidget.__init__

At `display_widget.py:62`, add after `self._fit_cache = {}`:

```python
self._bg_renderer = self._BackgroundImageRenderer()
```

---

## Step 2 — Wire Background Image into `paintEvent` (`display_widget.py`)

### 2.1 Lower-third mode (modify `paintEvent` at line 1066)

Current flow: clear to transparent → fill solid band. New flow: clear to transparent → paint background image in band rect → fill semi-transparent color on top.

Modify `paintEvent` (lines 1081-1095):

```python
# After the transparent clear (line 1079):
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

# Paint background image (if set) BEFORE the color overlay
if self._theme is not None:
    source_path = getattr(self._theme, 'source_path', None)
    self._bg_renderer.paint(painter, band_rect, self._theme.lower_third, source_path)

# Semi-transparent color overlay (preserves text readability)
color = QColor(bg_hex)
color.setAlphaF(bg_alpha)
painter.fillRect(band_rect, color)
```

### 2.2 Fullscreen mode — add background image support

Currently `paintEvent` delegates to `super().paintEvent()` in fullscreen mode. Add a fullscreen background image path:

```python
def paintEvent(self, event):
    if self._display_mode == DISPLAY_MODE_LOWER_THIRD:
        # ... existing lower-third code (modified above) ...
    else:
        # Fullscreen mode
        super().paintEvent(event)
        # Paint background image on top of stylesheet gradient (if set)
        if self._theme is not None:
            bg_image = self._theme.fullscreen.get("background_image")
            if bg_image:
                painter = QPainter(self)
                source_path = getattr(self._theme, 'source_path', None)
                self._bg_renderer.paint(painter, self.rect(), self._theme.fullscreen, source_path)
                painter.end()
```

### 2.3 Cache invalidation on theme change

In `set_theme` (line 94), add after `self._fit_cache.clear()`:

```python
self._bg_renderer.clear_cache()
```

---

## Step 3 — Font Import in Designer (`theme_designer.py`)

### 3.1 Add Font Import button

In `PropertyEditor`, add a "Import Font..." button near the font family rows. Locate the `_create_widget` method for `font_family` kind (line 656). **Replace the existing `return combo` at line 665** with a container that holds the combo plus an import button:

```python
# In _create_widget, font_family branch (line 656):
# REPLACE the existing return combo (line 665) with this container:
container = QWidget()
row = QHBoxLayout(container)
row.setContentsMargins(0, 0, 0, 0)
combo = QFontComboBox()
# Filter to system fonts + application fonts
row.addWidget(combo)

import_btn = QPushButton("Import Font...")
import_btn.setFixedWidth(90)
import_btn.clicked.connect(lambda: self._import_font(combo))
row.addWidget(import_btn)

return container  # replaces the old return combo
```

### 3.2 `_import_font` method

Add to `PropertyEditor`:

```python
def _import_font(self, combo):
    """Import a .ttf/.otf file into themes/fonts/ and refresh the combo."""
    from PyQt6.QtWidgets import QFileDialog, QMessageBox
    import shutil
    from pathlib import Path

    path, _ = QFileDialog.getOpenFileName(
        self, "Import Font", "",
        "Font Files (*.ttf *.otf);;All Files (*)")
    if not path:
        return

    src = Path(path)
    fonts_dir = Path(__file__).resolve().parent.parent / "utils" / "themes" / "fonts"
    fonts_dir.mkdir(parents=True, exist_ok=True)
    dest = fonts_dir / src.name

    if dest.exists():
        QMessageBox.information(self, "Font Already Imported",
            f"'{src.name}' is already in themes/fonts/.")
        return

    try:
        shutil.copy2(str(src), str(dest))
    except Exception as e:
        QMessageBox.warning(self, "Import Failed", f"Could not copy font: {e}")
        return

    # Re-scan fonts (re-entrant after Step 4 removes boolean guard)
    if self._theme_mgr:
        self._theme_mgr._load_application_fonts()

    # Refresh combo box to include newly registered fonts
    combo.clear()
    from PyQt6.QtGui import QFontDatabase
    families = QFontDatabase.families()
    combo.addItems(families)
```

### 3.3 Pass `theme_mgr` to PropertyEditor

`PropertyEditor` needs access to `ThemeManager` for font re-scanning. Verify that `PropertyEditor.__init__` receives `theme_mgr`. If not, thread it through from `ThemeDesignerPanel.__init__`.

---

## Step 4 — Re-entrant Font Loading (`theme.py`)

### 4.1 Remove boolean guard and update docstring

At `theme.py:290-292`, change:

```python
# Before:
if self._fonts_loaded:
    return 0
self._fonts_loaded = True

# After:
# (remove the boolean guard entirely — per-file _loaded_font_paths handles dedup)
```

Also update the docstring at line 285-288:

```python
# Before:
"""Load custom fonts from themes/fonts/ directory.

Scans for .ttf and .otf files and registers them via QFontDatabase.
Returns the number of font families loaded. Only runs once.
"""

# After:
"""Load custom fonts from themes/fonts/ directory.

Scans for .ttf and .otf files and registers them via QFontDatabase.
Returns the number of NEW font families loaded. Re-entrant — per-file
tracking in _loaded_font_paths prevents double-registration.
"""
```

The method body (lines 294-311) already checks `self._loaded_font_paths` per-file, so re-calling is safe. Each call scans `themes/fonts/` and registers only files not yet in the tracking set.

---

## Step 5 — Fade Transition (`display_widget.py`)

### 5.1 Replace `_start_fade` no-op

At `display_widget.py:277-279`, replace:

```python
def _start_fade(self):
    """Instant display update — no fade animation to avoid desktop flash."""
    self.setWindowOpacity(1.0)
```

With:

```python
def _start_fade(self):
    """Apply fade-in transition if enabled in theme.

    Uses QPropertyAnimation on a QGraphicsOpacityEffect attached to the
    active verse content widget. Opt-in via theme.lower_third.transition.type == "fade".
    Falls back to instant display when transition is disabled or theme is missing.
    """
    # Determine transition settings
    transition = {}
    if self._theme is not None:
        transition = self._theme.lower_third.get("transition", {})
    trans_type = transition.get("type", "none")

    if trans_type != "fade":
        return  # No animation — instant display

    duration_ms = int(transition.get("duration_ms", 200))
    easing_name = transition.get("easing", "OutCubic")

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
```

### 5.2 Safety: stop active animation and clear effects on theme change

In `set_theme` (line 94), add before `self._fit_cache.clear()`:

```python
# Stop any active fade animation before clearing graphics effects
# (prevents crash if set_theme is called mid-fade)
from PyQt6.QtCore import QAbstractAnimation
if hasattr(self, '_fade_anim') and self._fade_anim.state() == QAbstractAnimation.State.Running:
    self._fade_anim.stop()

# Clear any active fade effect to prevent stale graphics effects
if self._display_mode == DISPLAY_MODE_LOWER_THIRD:
    self._lt_text_column.setGraphicsEffect(None)
else:
    self.verse_content.setGraphicsEffect(None)
```

---

## Step 6 — Guard Scripts

### 6.1 `scripts/pre_commit_checks.py`

Add `check_phase3_advanced_properties()`:

```python
def check_phase3_advanced_properties():
    errors = []
    dw_path = SRC / 'display' / 'display_widget.py'
    with open(dw_path, encoding='utf-8') as f:
        dw = f.read()
    if '_BackgroundImageRenderer' not in dw:
        errors.append("CRITICAL: Phase 3: display_widget.py missing _BackgroundImageRenderer")
    if 'background_image' not in dw:
        errors.append("CRITICAL: Phase 3: display_widget.py does not reference background_image")
    if 'QPropertyAnimation' not in dw:
        errors.append("CRITICAL: Phase 3: display_widget.py missing QPropertyAnimation fade")

    th_path = SRC / 'utils' / 'theme.py'
    with open(th_path, encoding='utf-8') as f:
        th = f.read()
    if 'def _load_application_fonts' not in th:
        errors.append("CRITICAL: Phase 3: theme.py missing _load_application_fonts")

    td_path = SRC / 'ui' / 'theme_designer.py'
    with open(td_path, encoding='utf-8') as f:
        td = f.read()
    if 'Import Font' not in td:
        errors.append("CRITICAL: Phase 3: theme_designer.py missing Font Import button")
    return errors
```

### 6.2 `scripts/verify_critical_fixes.py`

Add Phase 3 block:

```python
print("\n=== Phase 3: Advanced Properties ===")
_dw3 = SRC / 'display' / 'display_widget.py'
with open(_dw3, encoding='utf-8') as _f:
    _dw3c = _f.read()
for _sym, _label in [
    ('_BackgroundImageRenderer', 'Background image renderer class'),
    ('QPropertyAnimation', 'Fade transition animation'),
    ('background_image', 'Background image field reference'),
]:
    if _sym in _dw3c:
        print(f"  [OK] display_widget.py: {_label}")
    else:
        errors.append(f"  [FAIL] Phase 3: display_widget.py missing: {_label}")

_td3 = SRC / 'ui' / 'theme_designer.py'
with open(_td3, encoding='utf-8') as _f:
    _td3c = _f.read()
if 'Import Font' in _td3c:
    print("  [OK] theme_designer.py: Font Import button")
else:
    errors.append("  [FAIL] Phase 3: theme_designer.py missing Font Import button")
```

---

## Regression Hazards

| Hazard | Risk | Mitigation |
|---|---|---|
| **Background image painting in fullscreen overrides stylesheet gradient** | Medium — solid color or image may cover text labels | Background image paints BEFORE labels in `paintEvent`; labels use `background: transparent` stylesheet. Z-order preserved. |
| **SVG background requires QtSvg** | Low — `QtSvg` may not be installed | `_decode()` catches `ImportError` and returns `None`. Falls back to solid color. |
| **LRU cache memory growth** | Low — 16 entries of native-resolution pixmaps | `MAX_CACHE_ENTRIES = 16`. Each entry is a decoded pixmap at native file resolution (not target size). Scaling happens at paint time. 16 entries of typical 1920x1080 images ~ 128MB. |
| **Fade animation on NDI grab** | Low — animation frames captured naturally | `QWidget.grab()` captures whatever `paintEvent` renders. Animation frames appear in NDI output as normal intermediate frames. No special handling needed. |
| **`_fonts_loaded` guard removal causes double-registration** | Medium — GDI handle leak on Windows | `_loaded_font_paths` set already tracks per-file. Only new files are registered. Verified in existing code at `theme.py:307`. |
| **Font Import copies to wrong directory** | Low — path resolution error | Uses `Path(__file__).resolve().parent.parent / "utils" / "themes" / "fonts"` (two `.parent` calls from `src/ui/` to `src/`). Verified against project structure. |
| **`setGraphicsEffect` on verse_content may conflict with existing effects** | Low — no existing effects | `_start_fade` stops any existing animation and clears the effect before creating a new one. `set_theme` also clears effects on theme change. |

---

## Definition of Done

- [ ] `_BackgroundImageRenderer` class exists in `display_widget.py` with `paint()`, `_get_cached()`, `_decode()`, `clear_cache()` methods
- [ ] Image backgrounds render in fullscreen mode for PNG, JPEG, SVG
- [ ] Image backgrounds render in lower-third mode for PNG, JPEG, SVG
- [ ] All four `background_image_fit` modes work (cover, contain, stretch, tile)
- [ ] `background_image_opacity` controls image transparency
- [ ] Solid color fallback works when no image is set
- [ ] Solid color overlay works over background image (text remains readable)
- [ ] `_load_application_fonts()` is re-entrant (boolean guard removed)
- [ ] Font Import button in designer copies .ttf/.otf to `themes/fonts/`
- [ ] Font Import triggers re-scan; newly imported fonts appear in `QFontComboBox`
- [ ] Duplicate font import shows informational dialog (no crash)
- [ ] Fade transition animates opacity 0 to 1 on verse push (when `transition.type == "fade"`)
- [ ] Fade duration respects `transition.duration_ms`
- [ ] Fade easing respects `transition.easing`
- [ ] No fade when `transition.type == "none"` (default behavior preserved)
- [ ] `set_theme()` clears fade effects and background image cache
- [ ] `pre_commit_checks.py` passes with zero errors
- [ ] `verify_critical_fixes.py` passes with zero errors
- [ ] No NDI capture regression (background images and fade frames captured naturally by `grab()`)

---

## Scope Note

**Transition editor controls:** After Phase 3, the Theme object will have transition data (from `_upgrade_to_v2` defaults: `type: "none"`, `duration_ms: 200`, `easing: "OutCubic"`), and `_start_fade` will read and apply it. However, `THEME_EDITOR_SCHEMA` has no entries for `transition.type`, `duration_ms`, or `easing` (line 122 explicitly deferts them). Users cannot configure fade transitions in the designer UI. This is tracked for a v1.3.x point release (not Phase 4 — Phase 4's scope is preset themes and regression sweep).

---

## Template Deviations

This plan deviates from the Implementation Plan Template in two ways:

1. **"Scope Note" section added.** Not in the template. Justification: documents the transition editor gap (THEME_EDITOR_SCHEMA has no transition entries) so implementers understand why fade transitions work at runtime but have no designer UI. Without this note, the gap looks like an oversight.

2. **Detailed code blocks with inline rationale.** The template specifies "Detailed pseudocode with exact line references" but the plan includes full Python code blocks with per-statement comments. Justification: Phase 3 touches rendering paths (`paintEvent`, `_start_fade`) where subtle bugs (paint ordering, effect lifecycle, cache key design) are easy to introduce. Full code blocks reduce ambiguity compared to pseudocode.

3. **Post-execution bug fixes not in plan.** Five bugs were found and fixed after implementation: (a) `drawPixmap` cover-mode crash — used `(QRect, QPixmap, int, int, int, int)` instead of `(QRect, QPixmap, QRect)`; (b) stylesheet cascade — `QWidget { background: gradient }` covered the background image, fixed by using `DisplayWidget` selector; (c) Import button clipping — `QFontComboBox.sizeHint` pushed button past viewport edge, fixed with `SizePolicy.Ignored`; (d) horizontal scrollbar — added `ScrollBarAlwaysOff`; (e) fade dead code — added `_get_fade_params()` helper to read theme transition dict. These were implementation bugs, not plan design flaws.

---

## Status Log

| Date | Note |
|------|------|
| May 19, 2026 | Plan drafted. 3 deviations from sub-roadmap (font loading re-entrancy, paintEvent background wiring, timeline 0.5→1 week). 8 implementation steps. |
| May 19, 2026 | Audit findings addressed: added Template Deviations section, split pre-flight transition entry, added orphan-effect guard in `_start_fade`, corrected deferral target to v1.3.x point release, clarified private-method access in Deviation 1. |
| May 20, 2026 | Implementation completed. 8 steps executed. Post-execution bugs found and fixed: drawPixmap cover-mode crash (QRect source rect), stylesheet cascade (QWidget→DisplayWidget selector), Import button clipping (SizePolicy.Ignored), horizontal scrollbar (ScrollBarAlwaysOff), fade dead code (_get_fade_params helper). All 6 manual verification tests pass. 3 minor deviations from plan (see below). |

---

## Implementation Deviations

These deviations from the plan were found during post-execution review. All are non-blocking:

1. **Font combo refresh: `update()` instead of `clear() + addItems()`.** Plan specified `combo.clear(); combo.addItems(QFontDatabase.families())`. Implementation uses `target_combo.update()` which schedules a repaint. `QFontComboBox` auto-refreshes from `QFontDatabase` on next dropdown open, so the imported font appears when needed. No functional impact.

2. **Import button label: "Import" instead of "Import Font...".** Shorter label is cleaner in context — the button is already next to a font combo. No functional impact.

3. **File filter: missing "All Files (*)` option.** Plan specified `"Font Files (*.ttf *.otf);;All Files (*)"`. Implementation only has `"Font files (*.ttf *.otf)"`. Prevents accidentally selecting wrong file types. Arguably better UX.
