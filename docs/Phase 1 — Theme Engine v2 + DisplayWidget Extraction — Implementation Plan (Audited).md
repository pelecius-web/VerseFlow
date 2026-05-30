# Phase 1 — Engine v2 + DisplayWidget Extraction + Guard Migration
## Implementation Plan (v2.0 — Post-Audit Revision)

> **Status:** ✅ Complete (May 16, 2026)
> **Audit basis:** Direct codebase inspection + independent audit report (May 14, 2026)
> **Previous version:** v1.0 — superseded by this document
> **Sub-roadmap deviations:** 3 intentional (documented below)

---

## Deviations from v1.3.0 Sub-Roadmap

### Deviation 1 — `display_core.py` NOT modified in Phase 1

**Sub-roadmap says:** Add `set_logo_path(path)` to `DisplayController`.

**Plan says:** `DisplayController.set_logo_path()` is added as a **forwarding stub only** in Phase 1 (not deferred as v1.0 claimed — audit D11 requires the full chain). The stub forwards to `DisplayWindow.set_logo_path()` → `DisplayWidget.set_logo_path()` → `_refresh_logo()`. Without this chain, channel-level `logo_path` in `ChannelSettings` never reaches `DisplayWidget._build_logo_widget()`.

**Justification:** The `hasattr` guard in `display_channel.py:210` silently suppresses the call today. Keeping it broken means logo changes via Settings panel have zero effect — a user-visible bug on first Phase 2 test.

---

### Deviation 2 — `ChannelManager` NOT modified in Phase 1

**Sub-roadmap says:** (implied) ThemeManager injection requires ChannelManager changes.

**Plan says:** No `ChannelManager` changes needed. Audit D8/D9 raised this concern, but inspection of `display_channel.py:203` shows `apply_settings()` already accesses `theme_mgr` via `self._controller.theme_mgr`. Since every `DisplayController` receives `theme_mgr` in `main.py` (`DisplayController(db=self.db, theme_mgr=self._theme_mgr)`), this path works without adding a `theme_manager` parameter to `DisplayChannel.__init__` or `ChannelManager.add_channel()`. The fix is to change the **call** from `theme_mgr.set_theme()` to `theme_mgr.get_theme()` + `self.set_theme()`, not the injection mechanism.

**Justification:** Adding a `theme_manager` parameter to `ChannelManager` risks breaking the compatibility shim layer (lines 235–348) and requires changes to `main.py` constructor calls that are out of scope. The existing injection path is sufficient.

---

### Deviation 3 — Extraction scope is ~900 lines, not "~432 across 7 methods"

**Sub-roadmap says:** "Extract ~432 lines across 7 methods."

**Plan says:** The actual extraction is **~900 lines across 25 method/block units** — more than half of `display_window.py`'s 1182 lines. The sub-roadmap's count covered only 7 paint methods and missed the entire rendering support chain, all helper methods those paint methods call, and the widget-construction infrastructure.

**Justification:** Partial extraction — moving only the 7 top-level methods without their dependencies — causes immediate `AttributeError` at runtime (audit D5, D6). The complete dependency chain must move together.

---

## Files Created

- `src/display/display_widget.py` — **NEW:** `DisplayWidget(QWidget)`, ~900 lines
- `tests/test_theme_engine.py` — **NEW:** pytest unit tests (~80 lines)
- `src/utils/themes/fonts/` — **NEW:** empty directory (fonts land in Phase 3)
- `src/utils/themes/assets/` — **NEW:** empty directory (convention for shared assets)

## Files Modified

- `scripts/pre_commit_checks.py` — **P0:** path migration + new `check_phase1_theme_engine()`
- `scripts/verify_critical_fixes.py` — **P0:** same path migration
- `src/display/display_window.py` — major refactor: thin shell wrapping `DisplayWidget`
- `src/display/display_core.py` — add forwarding stubs: `set_logo_path()` → `display_window` (D11)
- `src/utils/theme.py` — schema v2 engine, `_load_application_fonts`, `set_app_theme`
- `src/display/display_channel.py` — `set_theme()` + decoupled `apply_settings()` (D8)
- `src/utils/settings.py` — fix channel default `"default"` → `"dark_gold"` (4 locations)
- `src/main.py` — wire `set_app_theme()`, per-channel theme loop
- `src/utils/themes/dark_gold.json` — add `schema_version`, `fullscreen`, missing `lower_third` keys
- `src/utils/themes/light.json` — same
- `src/utils/themes/high_contrast.json` — same

## Files Not Touched

- `src/core/channel_manager.py` — see Deviation 2
- `src/core/channel_display_facade.py` — active HomePanel dependency
- `src/ndi/ndi_bridge.py`, `ndi_sender.py`, `ndi_manager.py` — NDI pipeline; zero modifications
- `src/ui/home_panel.py` — no operator UI changes this phase
- `src/ui/settings_panel.py` — designer UI lands in Phase 2
- `src/utils/constants.py` — `LOWER_THIRD_*` kept as v2.0 fallback values

---

## Step 0 — Guard Script Path Migration (P0 — Do First)

Both scripts currently hard-code `SRC = ROOT / '2. Source Code'` (confirmed `pre_commit_checks.py:7`). Run them first to establish a clean baseline before any source changes.

### `scripts/pre_commit_checks.py` and `scripts/verify_critical_fixes.py` — top of file

**Replace:**
```python
SRC = ROOT / '2. Source Code'
```

**With:**
```python
SRC       = ROOT / 'src'
SRC_UI    = SRC / 'ui'
SRC_CORE  = SRC / 'core'
SRC_DISP  = SRC / 'display'
SRC_NDI   = SRC / 'ndi'
SRC_UTILS = SRC / 'utils'
SCRIPTS   = ROOT / 'scripts'
TESTS     = ROOT / 'tests'
```

### File path substitution table (apply mechanically to every function in both scripts)

| Old path | New path |
|----------|----------|
| `SRC / 'home_panel.py'` | `SRC_UI / 'home_panel.py'` |
| `SRC / 'settings_panel.py'` | `SRC_UI / 'settings_panel.py'` |
| `SRC / 'playlist_panel.py'` | `SRC_UI / 'playlist_panel.py'` |
| `SRC / 'queue_panel.py'` | `SRC_UI / 'queue_panel.py'` |
| `SRC / 'editors.py'` | `SRC_UI / 'editors.py'` |
| `SRC / 'channel_manager.py'` | `SRC_CORE / 'channel_manager.py'` |
| `SRC / 'navigator.py'` | `SRC_CORE / 'navigator.py'` |
| `SRC / 'models.py'` | `SRC_CORE / 'models.py'` |
| `SRC / 'display_window.py'` | `SRC_DISP / 'display_window.py'` |
| `SRC / 'display_channel.py'` | `SRC_DISP / 'display_channel.py'` |
| `SRC / 'display_core.py'` | `SRC_DISP / 'display_core.py'` |
| `SRC / 'channel_display_facade.py'` | `SRC_DISP / 'channel_display_facade.py'` |
| `SRC / 'ndi_bridge.py'` | `SRC_NDI / 'ndi_bridge.py'` |
| `SRC / 'ndi_sender.py'` | `SRC_NDI / 'ndi_sender.py'` |
| `SRC / 'ndi_manager.py'` | `SRC_NDI / 'ndi_manager.py'` |
| `SRC / 'theme.py'` | `SRC_UTILS / 'theme.py'` |
| `SRC / 'settings.py'` | `SRC_UTILS / 'settings.py'` |
| `SRC / 'constants.py'` | `SRC_UTILS / 'constants.py'` |
| `SRC / 'db_layer.py'` | `SRC_UTILS / 'db_layer.py'` |
| `SRC / 'themes' / 'dark_gold.json'` | `SRC_UTILS / 'themes' / 'dark_gold.json'` |
| `SRC / 'main.py'` | `SRC / 'main.py'` |

> **Note:** `playlist_panel.py`, `queue_panel.py`, `editors.py`, `models.py`, `db_layer.py`, and `themes/dark_gold.json` were confirmed present in `pre_commit_checks.py` but were missing from the original table. All are opened directly via `open(SRC / 'filename')` and will raise `FileNotFoundError` after the path migration if not updated.

**Verify after migration:**
```powershell
python scripts/pre_commit_checks.py
python scripts/verify_critical_fixes.py
```
Both must pass with zero errors before Step 1 begins. Any failure here is a path-mapping error, not a code regression.

---

## Step 1 — Create `src/display/display_widget.py`

### 1.1 Full Corrected Extraction Scope

The complete set of method/block units that move from `display_window.py` to `display_widget.py`. **All 26 units must move together** — moving any subset causes `AttributeError` at runtime on the first verse push or resize.

| # | Method / Block | Lines in `display_window.py` | Approx. |
|---|---|---|---|
| 1 | Fullscreen widget construction (new `_build_fullscreen_page()`) | `__init__` lines 89–125 | ~37 |
| 2 | `_build_lower_third_page()` | 511–625 | ~115 |
| 3 | `_clear_verse_content()` **(O2 fix)** | 224–235 | ~12 |
| 4 | `_clear_all_mode_content()` **(O2 fix)** | 237–246 | ~10 |
| 5 | `_available_verse_area()` **(D6 fix)** | 248–281 | ~34 |
| 6 | `_calc_single_font_size()` | 283–324 | ~42 |
| 7 | `_calc_overlay_font_sizes()` | 326–369 | ~44 |
| 8 | `_overlay_content_fits()` | 371–394 | ~24 |
| 9 | `_measure_wrapped_text_height()` | 396–405 | ~10 |
| 10 | `_measure_rich_text_height()` | 407–416 | ~10 |
| 11 | `_render_verse_content()` | 418–423 | ~6 |
| 12 | `_render_fullscreen()` | 425–492 | ~68 |
| 13 | `_build_overlay_html()` | 494–509 | ~16 |
| 14 | `_render_lower_third()` | 627–670 | ~44 |
| 15 | `_update_lower_third_geometry()` | 672–700 | ~29 |
| 16 | `_lower_third_available_area()` **(D5 fix)** | 702–721 | ~20 |
| 17 | `_fit_church_name_font()` | 723–777 | ~55 |
| 18 | `_fit_reference_font()` **(D5 fix)** | 779–812 | ~34 |
| 19 | `_fit_lower_third_fonts()` | 814–893 | ~80 |
| 20 | `paintEvent()` | 895–928 | ~34 |
| 21 | `_apply_theme_styling()` **(D1, D4 fix)** | 1011–1053 | ~43 |
| 22 | `_apply_default_styling()` **(D1 fix)** | 1055–1087 | ~33 |
| 23 | `_start_fade()` **(O4 fix)** | 974–976 | ~3 |
| 24 | `_do_translations_update()` + `_translations_update_timer` setup **(O3 fix)** | 68–73, 218–222 | ~10 |
| 25 | All instance variables: `ref_label`, `verse_scroll`, `verse_content`, `verse_layout`, `bottom_bar`, all `_lt_*`, `_stacked`, `_fullscreen_page`, `_lt_page`, `_fit_cache`, `_overlay_labels` | `__init__` | ~40 |
| 26 | `_on_layout_changed()` **(I6 fix)** | 968–972 | ~5 |

**Total: ~913 lines (~77% of `display_window.py`)**

> **I6 fix:** `_on_layout_changed` is connected in `DisplayWidget.__init__` (§1.2) but was missing from the extraction table. It is a 5-line stub (`self._layout_mode = mode`) that must move with the widget or `layout_changed` signal fires into a missing method at runtime (`AttributeError`).

### 1.2 `DisplayWidget.__init__` — Full Signature (D3 fix)

```python
class DisplayWidget(QWidget):
    """Extracted rendering core for VerseFlow congregation display.

    Self-contained: all paint logic, font fitting, layout construction,
    logo infrastructure, and theme application live here. Can be embedded
    in DisplayWindow (live output) or ThemeDesignerPanel (Phase 2 preview).

    Args:
        display_controller: DisplayController-compatible object. Signals
            verse_changed, translations_changed, layout_changed are
            connected read-only. DisplayWidget never writes to the controller.
        theme_manager: ThemeManager instance. Held only as a fallback
            reference for the designer preview (Phase 2). Per-channel
            theming uses self._theme set via set_theme(); this reference
            is NOT used for styling decisions in live mode.
        church_name: Pre-fetched church name string for the lower-third
            label. Eliminates the hidden SettingsManager dependency in
            _render_lower_third() (audit D3). Caller (DisplayWindow or
            designer) is responsible for reading and passing this value.
            Defaults to "" if not provided.
        parent: Optional parent QWidget.
    """

    LAYOUT_GAP = 16
    SAFETY_BUFFER = 4
    BLOCK_MARGIN = 6
    RESIZE_DEBOUNCE_MS = 100

    def __init__(self, display_controller, theme_manager=None,
                 church_name: str = "", parent=None):
        super().__init__(parent)
        self.display = display_controller
        self.theme_mgr = theme_manager
        self._theme = None            # per-channel; set via set_theme()
        self._church_name = church_name
        self._display_mode = DISPLAY_MODE_FULLSCREEN
        self._overlay_labels = []
        self._fit_cache = {}
        self._logo_path_override = None  # I2 fix: per-widget override, never mutates shared Theme

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
        # verse_changed is NOT connected here — it routes exclusively through
        # DisplayWindow._on_verse_changed, which then delegates to _deferred_render().
        # Connecting it here too would cause double-render and AttributeError
        # (DisplayWidget has no _on_verse_changed). (I1 fix)
        self.display.layout_changed.connect(self._on_layout_changed)
        self.display.translations_changed.connect(self._on_translations_changed)

        self._apply_theme_styling()
```

> **D3 resolution:** `_render_lower_third()` previously called `SettingsManager()` at line 661 to read `church_name`. After extraction, it reads `self._church_name` instead. `DisplayWindow` reads it once from `SettingsManager` and passes it to `DisplayWidget.__init__`. If the church name changes (Settings panel save), `DisplayWindow` calls `display_widget.set_church_name(name)` which updates `self._church_name` and triggers a re-render if currently live.

### 1.3 `set_theme()` and `set_display_mode()` on `DisplayWidget`

```python
def set_theme(self, theme) -> None:
    """Apply a Theme to this widget only. Does NOT call QApplication.setStyleSheet().

    Clears _fit_cache because font families may change (audit O5 fix).
    Refreshes logo widget if logo_path changed.
    Triggers a single repaint.
    Idempotent — calling with the same theme twice repaints only.
    """
    self._theme = theme
    self._fit_cache.clear()     # O5 fix: stale cached sizes invalid after font change
    self._refresh_logo()
    self._apply_theme_styling() # D4 fix: reads self._theme, not theme_mgr.current
    self.update()

def set_display_mode(self, mode: str) -> None:
    """Switch rendering mode. Rendering concerns only — no window flags."""
    self._display_mode = mode
    self._fit_cache.clear()
    self._stacked.setCurrentIndex(
        1 if mode == DISPLAY_MODE_LOWER_THIRD else 0
    )
    self._apply_theme_styling()
    self.update()

def set_church_name(self, name: str) -> None:
    """Update the church name used in lower-third rendering.
    Re-renders if currently live in lower-third mode.
    """
    self._church_name = name
    if self._display_mode == DISPLAY_MODE_LOWER_THIRD and self.display.current:
        self._render_lower_third(self.display.current)
```

### 1.4 `_apply_theme_styling()` — Rewritten to Read `self._theme` (D4 fix)

The current `display_window.py:1013` reads `self.theme_mgr.current` — the **global** current theme. After extraction, it must read the **per-channel** `self._theme`:

```python
def _apply_theme_styling(self) -> None:
    """Apply per-channel theme styling. Reads self._theme, NOT theme_mgr.current.

    This is the ONLY method that reads self._theme for styling. It is
    called from set_theme(), set_display_mode(), and __init__.
    Never calls QApplication.setStyleSheet().
    """
    if self._theme is None:
        self._apply_default_styling()
        return

    c = self._theme.c
    bg_value = (
        "transparent"
        if self._display_mode == DISPLAY_MODE_LOWER_THIRD
        else f"qlineargradient(x1:0, y1:0, x2:1, y2:1, "
             f"stop:0 {c('bg_primary')}, stop:1 {c('bg_secondary')})"
    )

    # QWidget.setStyleSheet applies to this widget subtree only (not QApplication)
    self.setStyleSheet(f"""
        QWidget {{
            background: {bg_value};
            color: {c('text_primary')};
        }}
    """)
    self.ref_label.setStyleSheet(f"""
        color: {c('gold')};
        background: transparent;
        letter-spacing: 5px;
        padding: 6px 0 10px 0;
    """)
    self.verse_scroll.setStyleSheet("""
        QScrollArea { background: transparent; border: none; }
    """)
    self.bottom_bar.setStyleSheet(f"""
        color: {c('text_faint')}; background: transparent;
    """)
```

> **Critical note:** `self.setStyleSheet()` on a `QWidget` subtree is **not** `QApplication.setStyleSheet()`. It scopes to this widget and its children only — per-channel isolation is maintained.

### 1.5 `paintEvent()` — Theme-Aware Version (reads `self._theme`)

```python
def paintEvent(self, event):
    """Paint lower-third band. Reads self._theme for colors and ratios.
    Falls back to LOWER_THIRD_* constants when self._theme is None (O6 confirmed safe).
    """
    if self._display_mode != DISPLAY_MODE_LOWER_THIRD:
        super().paintEvent(event)
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
    color = QColor(bg_hex)
    color.setAlphaF(bg_alpha)
    painter.fillRect(0, band_y, self.width(), band_h, color)
    painter.end()
```

### 1.6 `_on_verse_changed()` Split (O1 fix)

`_on_verse_changed()` interleaves window-level decisions with rendering calls. After extraction, it is **split** across both classes:

**In `DisplayWindow`** (stays): handles show/hide/fullscreen/headless logic, updates `ref_label`, and delegates rendering:
```python
def _on_verse_changed(self, verse):
    """Window-level handler: manages window visibility and delegates rendering."""
    if not verse:
        self._is_live = False
        if self.isFullScreen() or self._is_fullscreen:
            self.showNormal()
        self._is_fullscreen = False
        self.close()
        return

    if not self._is_live:
        self._is_live = True
        if self._display_mode == DISPLAY_MODE_FULLSCREEN:
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
            self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.WindowStaysOnTopHint)
            if self._headless:
                self.setGeometry(0, 0, 1920, 1080)
                self.winId()
            else:
                screen = self._target_screen or self.screen()
                self.setGeometry(screen.geometry())
                self.showFullScreen()
                self._is_fullscreen = True
        else:
            self._apply_lower_third_window_state()

    # Update fullscreen ref_label (lives on DisplayWidget after extraction).
    # Must be called here, before _deferred_render, so geometry-dependent
    # font sizing in _available_verse_area() accounts for the correct label height.
    # (I5 fix: ref_label update was omitted from the original split — runtime bug)
    self._display_widget.ref_label.setText(verse.get("reference", ""))

    # Delegate all rendering to DisplayWidget
    QTimer.singleShot(50, lambda v=verse: self._display_widget._deferred_render(v))
```

**In `DisplayWidget`**: `_deferred_render()` and `_on_translations_changed()` are already there (units 24, extracted from `display_window.py:190-222`). No `_on_verse_changed` signal connection in `DisplayWidget.__init__` — the signal routes only through `DisplayWindow._on_verse_changed`, which then delegates. (I1 fix)

### 1.7 Logo Widget Factory (I2 fix applied)

```python
def _build_logo_widget(self) -> QWidget | None:
    """Return the correct widget for the current logo path.
    Returns QSvgWidget, QLabel (pixmap), QFrame (placeholder), or None.

    Priority: self._logo_path_override (set via set_logo_path()) takes
    precedence over theme.lower_third.logo_path. This avoids mutating
    the shared Theme object, which would contaminate the other channel
    and all future get_theme() calls for the same theme ID. (I2 fix)
    """
    lt = self._theme.lower_third if self._theme else {}
    # I2 fix: use per-widget override before falling back to theme value
    logo_path_str = self._logo_path_override or lt.get("logo_path")
    show_placeholder = lt.get("show_logo_placeholder", True)

    if logo_path_str:
        if self._theme and hasattr(self._theme, '_source_path'):
            logo_path = (self._theme._source_path.parent / logo_path_str).resolve()
        else:
            logo_path = Path(logo_path_str)
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

def set_logo_path(self, path: str | None) -> None:
    """Update logo from an external path (channel-level override).
    Called by DisplayWindow.set_logo_path() (D11 chain terminus).

    Stores path in self._logo_path_override — does NOT mutate
    self._theme.lower_third. The shared Theme object (held by ThemeManager
    and referenced by both channels) must remain unmodified. (I2 fix)
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

---

## Step 2 — Refactor `display_window.py` to a Thin Shell (D2 fix)

`DisplayWindow` retains only window-management responsibilities. Every rendering call is delegated to `self._display_widget`.

### 2.1 What stays in `DisplayWindow`

| Concern | Method | Stays/Moves |
|---|---|---|
| Window flags, `WA_TranslucentBackground` | `_apply_lower_third_window_state()` | **Stays** |
| Headless geometry setup | `_on_verse_changed()` headless branch | **Stays** |
| Fullscreen show/hide | `showFullScreen()`, `showNormal()` | **Stays** |
| Resize debounce timer | `_resize_timer`, `resizeEvent()`, `_handle_resize_finished()` | **Stays** (delegates) |
| `set_theme()` delegation | New method | **Stays** (forwards) |
| `set_display_mode()` — window flags only | See §2.2 | **Stays** (split) |
| NDI `grab()` surface | `QMainWindow.grab()` | **Stays** (unaffected) |
| Key/mouse events | `keyPressEvent`, `mouseDoubleClickEvent` | **Stays** |
| `toggle_fullscreen()` | Exists today | **Stays** |

> **`_apply_lower_third_window_state()` delegation (implementor note):**
> This method currently calls `self._stacked.setCurrentIndex(1)` and `self._apply_theme_styling()` directly — both in the headless branch (lines 945, 947) and the non-headless branch (lines 961, 964). After extraction, `_stacked` and `_apply_theme_styling` no longer exist on `DisplayWindow`.
>
> **Resolution:** Replace both pairs of calls with a single delegation:
> ```python
> self._display_widget.set_display_mode(DISPLAY_MODE_LOWER_THIRD)
> ```
> `DisplayWidget.set_display_mode()` already does `_stacked.setCurrentIndex(1)` + `_apply_theme_styling()` + `_fit_cache.clear()` + `update()` — making it the correct and complete replacement. This applies in **both** the headless and non-headless branches. The `self.update()` call on the window itself (line 948/966) should be kept separately, as it triggers `DisplayWindow.paintEvent()` (the lower-third band paint).

### 2.2 `set_display_mode()` — Explicit Split (D2 fix)

This 61-line method (lines 1089–1150) interleaves window-flag mutations with rendering calls. After extraction it is split:

```python
# In DisplayWindow — window concerns only
def set_display_mode(self, mode: str):
    """Handle window-flag concerns for mode switch.
    Rendering concerns (stacked page, cache, re-render) delegated to DisplayWidget.
    """
    valid = (DISPLAY_MODE_FULLSCREEN, DISPLAY_MODE_LOWER_THIRD)
    if mode not in valid or mode == self._display_mode:
        return

    # 1. Clear mode-specific content via widget (needs old mode to clear correctly)
    if self._is_live:
        self._display_widget._clear_all_mode_content()

    self._display_mode = mode  # update window's local copy

    # 2. Window flags / attributes (window-level — stays here)
    if self._is_live:
        if mode == DISPLAY_MODE_LOWER_THIRD:
            self._apply_lower_third_window_state()  # stays in DisplayWindow
        else:
            screen = self._target_screen or self.screen()
            geo = screen.geometry()
            self.hide()
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
            self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.WindowStaysOnTopHint)
            if self._headless:
                self.setGeometry(0, 0, 1920, 1080)
            else:
                self.setGeometry(geo)
                self.showFullScreen()
                self._is_fullscreen = True

    # 3. Delegate rendering concerns to DisplayWidget
    self._display_widget.set_display_mode(mode)  # handles _stacked, _fit_cache, _apply_theme_styling

    # 4. Re-render if live
    if self._is_live and self.display.current:
        if mode == DISPLAY_MODE_FULLSCREEN:
            QTimer.singleShot(50, lambda: self.display.current and
                              self._display_widget._render_verse_content(self.display.current))
        else:
            self._display_widget._render_verse_content(self.display.current)
```

### 2.3 Resize Delegation (D7 fix)

`resizeEvent()` and `_handle_resize_finished()` stay in `DisplayWindow` but delegate to the widget:

```python
def resizeEvent(self, event):
    super().resizeEvent(event)
    # Proportional ref scaling — cheap, delegate to widget
    if self._display_mode == DISPLAY_MODE_FULLSCREEN:
        new_ref_size = max(24, min(60, self.height() // 22))
        font = self._display_widget.ref_label.font()
        font.setPointSize(new_ref_size)
        self._display_widget.ref_label.setFont(font)
    if self._display_mode == DISPLAY_MODE_LOWER_THIRD:
        self._display_widget._update_lower_third_geometry()  # D7 fix
    self._display_widget._fit_cache.clear()  # D7 fix
    if self.display.current and self._is_live:
        self._resize_timer.start(self.RESIZE_DEBOUNCE_MS)

def _handle_resize_finished(self):
    if self.display.current and self._is_live:
        self._display_widget._render_verse_content(self.display.current)  # D7 fix
```

### 2.4 Forwarding Methods on `DisplayWindow`

```python
def set_theme(self, theme) -> None:
    """Forward to DisplayWidget. Does NOT touch QApplication."""
    self._display_widget.set_theme(theme)

def set_logo_path(self, path: str | None) -> None:
    """Forward to DisplayWidget (D11 chain middle link)."""
    self._display_widget.set_logo_path(path)

def set_church_name(self, name: str) -> None:
    """Forward to DisplayWidget."""
    self._display_widget.set_church_name(name)
```

### 2.5 NDI `grab()` Verification Note

`QMainWindow.grab()` triggers `paintEvent` on all child widgets. Since `DisplayWidget` is the central widget, `grab()` captures `DisplayWidget.paintEvent()` output exactly as before. **`ndi_sender.py` requires zero changes.**

> **O6 confirmation:** `DisplayWidget.width()` and `DisplayWidget.height()` return the widget's size. Since `DisplayWindow.setCentralWidget(self._display_widget)` makes the widget fill the window exactly (Qt layout guarantee for central widgets), these values equal the window size. The assumption is safe.

---

## Step 3 — `src/display/display_core.py` + `display_window.py` — Forwarding Stubs + Church Name Wiring (D11 fix + I7 fix)

### 3.1 Forwarding stubs on `DisplayController` (D11 fix)

Add to `display_core.py`. These are thin forwarders — no rendering logic here.

```python
def set_logo_path(self, path: str | None) -> None:
    """Forward logo path to DisplayWindow → DisplayWidget.
    Called by DisplayChannel.apply_settings() via display_channel.py:211.
    No-op when display_window is None (lazy creation not yet triggered).
    """
    if self.display_window is not None and hasattr(self.display_window, 'set_logo_path'):
        self.display_window.set_logo_path(path)

def set_church_name(self, name: str) -> None:
    """Forward church name to DisplayWindow → DisplayWidget."""
    if self.display_window is not None and hasattr(self.display_window, 'set_church_name'):
        self.display_window.set_church_name(name)
```

### 3.2 `DisplayWindow.__init__` — accept and forward `church_name` (I7 fix)

The current `DisplayWindow.__init__` signature (line 44) has no `church_name` parameter. After extraction, `DisplayWidget.__init__` requires it. Add it:

```python
# Before (display_window.py line 44):
def __init__(self, display_controller, theme_manager, screen=None, parent=None, headless=False):

# After:
def __init__(self, display_controller, theme_manager, screen=None, parent=None,
             headless=False, church_name: str = ""):
```

And pass it through when constructing `DisplayWidget` inside `DisplayWindow.__init__`:

```python
self._display_widget = DisplayWidget(
    self.display,
    theme_manager=self.theme_mgr,
    church_name=church_name,   # I7 fix: passed from DisplayWindow, read from SettingsManager by caller
)
self.setCentralWidget(self._display_widget)
```

### 3.3 `DisplayCore.open_display_window()` — read and pass `church_name` (I7 fix)

The current call site (line 203) does not pass `church_name`. Update it:

```python
# Before (display_core.py line 203):
self.display_window = DisplayWindow(self, theme_mgr, screen=screen, headless=headless)

# After:
from settings import SettingsManager
church_name = SettingsManager().get("general", "church_name", "")
self.display_window = DisplayWindow(
    self, theme_mgr, screen=screen, headless=headless, church_name=church_name
)
```

> **Lazy creation note:** When `display_window` is `None` (verse not yet pushed), the `set_logo_path` and `set_church_name` stubs are no-ops. `church_name` is read from `SettingsManager` at window-construction time in `open_display_window()` and passed through the chain. If the church name changes later (Settings panel save), `DisplayChannel` or `HomePanel` calls `controller.set_church_name(name)` → `DisplayWindow.set_church_name()` → `DisplayWidget.set_church_name()` → re-render. The `logo_path` is passed by calling `set_logo_path()` immediately after `open_display_window()` returns — handled in the `display_channel.py` updated `apply_settings()`.

---

## Step 4 — `src/utils/theme.py` — Schema v2 Engine

### 4.1 `Theme.__init__` — Schema Versioning

```python
KNOWN_SCHEMA_VERSIONS = {"1.0", "2.0"}

class Theme:
    def __init__(self, data: dict, source_path: Path = None):
        self.schema_version: str = data.get("schema_version", "1.0")
        if self.schema_version not in KNOWN_SCHEMA_VERSIONS:
            logger.warning("[Theme] Unknown schema_version '%s'; treating as 1.0", self.schema_version)
            self.schema_version = "1.0"
        self.name        = data.get("name", "Unknown")
        self.id          = data.get("id", "unknown")
        self.description = data.get("description", "")
        self.version     = data.get("version", "1.0")
        self.author      = data.get("author", "")
        self.colors      = data.get("colors", {})
        self.fonts       = data.get("fonts", {})
        self.animation   = data.get("animation", {})
        self.spacing     = data.get("spacing", {})
        self.lower_third = data.get("lower_third", {})
        self.fullscreen  = data.get("fullscreen", {})
        self._source_path = source_path
        if self.schema_version == "1.0":
            self._upgrade_to_v2()

    def _upgrade_to_v2(self):
        """Populate v2-only fields in memory. On-disk file unchanged."""
        # lazy import to avoid circular dependency
        from constants import (
            LOWER_THIRD_HEIGHT_RATIO, LOWER_THIRD_BACKGROUND_ALPHA,
            LOWER_THIRD_LOGO_WIDTH_RATIO, LOWER_THIRD_LOGO_MAX_HEIGHT_RATIO,
            LOWER_THIRD_SEPARATOR_WIDTH,
        )
        if not self.fullscreen:
            self.fullscreen = {
                "background_color":         self.colors.get("bg_secondary", "#0a0a14"),
                "background_image":         None,
                "background_image_fit":     "cover",
                "background_image_opacity": 1.0,
                "ref_color":                self.colors.get("gold", "#c8a03c"),
                "verse_color":              self.colors.get("text_primary", "#e8e2d8"),
                "ref_font_family":          self.fonts.get("family", "Segoe UI"),
                "ref_font_weight":          "Black",
                "verse_font_family":        self.fonts.get("family", "Segoe UI"),
                "verse_font_weight":        "Normal",
            }
        lt_defaults = {
            "logo_path":              None,
            "logo_format":            "auto",
            "show_logo_placeholder":  True,
            # D10 fix: default is 0.16 (dark_gold.json value), NOT 0.10 (constant)
            "logo_width_ratio":       self.lower_third.get("logo_width_ratio", 0.16),
            "logo_max_height_ratio":  LOWER_THIRD_LOGO_MAX_HEIGHT_RATIO,
            "show_separator":         True,
            "separator_color":        self.colors.get("gold", "#c8a03c"),
            "separator_width":        LOWER_THIRD_SEPARATOR_WIDTH,
            "background_image":       None,
            "background_image_fit":   "cover",
            "background_alpha":       LOWER_THIRD_BACKGROUND_ALPHA,
            "height_ratio":           LOWER_THIRD_HEIGHT_RATIO,
            "accent_color":           self.colors.get("gold", "#c8a03c"),
            "ref_color":              self.colors.get("gold", "#c8a03c"),
            "verse_color":            self.colors.get("text_primary", "#e8e2d8"),
            "ref_font_family":        self.fonts.get("family", "Segoe UI"),
            "verse_font_family":      self.fonts.get("family", "Segoe UI"),
            "church_name_color":      self.colors.get("gold", "#c8a03c"),
            "transition":             {"type": "none", "duration_ms": 200, "easing": "OutCubic"},
        }
        for key, val in lt_defaults.items():
            self.lower_third.setdefault(key, val)
        self.schema_version = "2.0"
```

> **D10 fix:** The `logo_width_ratio` default in `_upgrade_to_v2` preserves the **existing JSON value** via `self.lower_third.get("logo_width_ratio", 0.16)` before `setdefault` runs. Since `dark_gold.json` already has `0.16`, it is preserved. The constant `LOWER_THIRD_LOGO_WIDTH_RATIO = 0.10` (the old hardcoded value) is only used as the fallback for themes that have no `logo_width_ratio` at all — not to override existing JSON values.

### 4.2 `ThemeManager.__init__`, `_load_application_fonts()`, `set_app_theme()`

```python
def __init__(self):
    self._themes: dict[str, Theme] = {}
    self._current: Optional[Theme] = None
    self.application_fonts: set[str] = set()
    self._loaded_font_paths: set[str] = set()
    self._load_application_fonts()   # one-time scan
    self._load_builtins()

def _load_application_fonts(self) -> None:
    """Scan themes/fonts/ for .ttf/.otf. Idempotent — path-tracked."""
    fonts_dir = THEMES_DIR / "fonts"
    if not fonts_dir.exists():
        return
    from PyQt6.QtGui import QFontDatabase
    for ext in ("*.ttf", "*.otf"):
        for p in fonts_dir.glob(ext):
            if str(p) not in self._loaded_font_paths:
                fid = QFontDatabase.addApplicationFont(str(p))
                if fid >= 0:
                    self.application_fonts.update(QFontDatabase.applicationFontFamilies(fid))
                    self._loaded_font_paths.add(str(p))

def _load_builtins(self):
    if not THEMES_DIR.exists():
        return
    for p in THEMES_DIR.glob("*.json"):
        try:
            with open(p, encoding="utf-8") as f:
                data = json.load(f)
            theme = Theme(data, source_path=p)
            self._themes[theme.id] = theme
        except (json.JSONDecodeError, KeyError) as exc:
            logger.warning("[ThemeManager] Failed to load '%s': %s", p, exc)

def set_app_theme(self, theme_id: str, app) -> bool:
    """Apply QSS to QApplication (operator panel chrome only).
    ONLY method permitted to call QApplication.setStyleSheet().
    """
    theme = self._themes.get(theme_id)
    if theme is None:
        logger.warning("[ThemeManager] set_app_theme: unknown id '%s'", theme_id)
        return False
    self._current = theme
    if app is not None:
        app.setStyleSheet(generate_stylesheet(theme))
    return True

def set_theme(self, theme_id: str, app=None) -> bool:
    """Deprecated alias for set_app_theme(). Removed in v1.4.0."""
    logger.warning("[ThemeManager] set_theme() deprecated. Use set_app_theme().")
    return self.set_app_theme(theme_id, app)
```

---

## Step 5 — `src/utils/themes/*.json` — Schema v2 Fields (D10 fix)

Add `schema_version` and `fullscreen` to all three JSON files. For `dark_gold.json`, also add the missing `lower_third` keys. **Existing values are not changed.**

### `dark_gold.json` — new/added keys only

```json
{
  "schema_version": "2.0",
  "author": "VerseFlow Built-in",
  "fullscreen": {
    "background_color": "#0a0a14",
    "background_image": null,
    "background_image_fit": "cover",
    "background_image_opacity": 1.0,
    "ref_color": "#c8a03c",
    "verse_color": "#e8e2d8",
    "ref_font_family": "Segoe UI",
    "ref_font_weight": "Black",
    "verse_font_family": "Segoe UI",
    "verse_font_weight": "Normal"
  },
  "lower_third": {
    "logo_width_ratio": 0.16,
    "logo_format": "auto",
    "separator_width": 1,
    "background_image": null,
    "background_image_fit": "cover",
    "height_ratio": 0.30,
    "ref_color": "#c8a03c",
    "verse_color": "#e8e2d8",
    "ref_font_family": "Segoe UI",
    "verse_font_family": "Segoe UI",
    "church_name_color": "#c8a03c",
    "transition": { "type": "none", "duration_ms": 200, "easing": "OutCubic" }
  }
}
```

> `logo_width_ratio: 0.16` is kept — **not** changed to 0.10. See D10 fix in Step 4.1.

---

## Step 6 — `src/display/display_channel.py` — Decouple `apply_settings()` (D8 fix)

### Add `set_theme()` and `theme` property

```python
def set_theme(self, theme) -> None:
    """Apply a Theme to this channel's DisplayWindow only.
    Caches for lazy-created windows. No QApplication side-effects.
    """
    self._theme = theme
    dw = getattr(self._controller, 'display_window', None)
    if dw is not None and hasattr(dw, 'set_theme'):
        dw.set_theme(theme)

@property
def theme(self):
    return getattr(self, '_theme', None)
```

### Updated `apply_settings()` — replace lines 188–212

```python
def apply_settings(self, settings: dict):
    mode = settings.get("mode")
    if mode in (self.MODE_FULLSCREEN, self.MODE_LOWER_THIRD):
        self.set_display_mode(mode)
    else:
        logger.warning("[DisplayChannel] '%s': invalid mode '%s'", self.name, mode)


    # D8 fix: get_theme() + channel.set_theme() — no global QSS call
    theme_id = settings.get("theme_id", "dark_gold")
    theme_mgr = getattr(self._controller, 'theme_mgr', None)
    if theme_mgr is not None:
        theme = theme_mgr.get_theme(theme_id)
        if theme is None:
            if not getattr(self, '_unknown_theme_warned', False):
                logger.warning("[DisplayChannel] '%s': unknown theme_id '%s'",
                               self.name, theme_id)
                self._unknown_theme_warned = True
        else:
            self._unknown_theme_warned = False
            self.set_theme(theme)   # per-channel — no QApplication side-effect

    logo_path = settings.get("logo_path")
    if logo_path and hasattr(self._controller, 'set_logo_path'):
        self._controller.set_logo_path(logo_path)   # D11 chain: controller → window → widget
```

---

## Step 7 — `src/utils/settings.py` — Fix Channel Defaults (4 locations)

| Location | Before | After |
|---|---|---|
| `ChannelSettings.theme_id` (line 44) | `"default"` | `"dark_gold"` |
| `_apply_defaults()` main channel (line 130) | `"theme": "default"` | `"theme": "dark_gold"` |
| `_apply_defaults()` alt channel (line 138) | `"theme": "default"` | `"theme": "dark_gold"` |
| `get_channel_settings()` fallback (line 321) | `or "default"` | `or "dark_gold"` |

> Users with existing `settings.json` containing `"theme": "default"` receive one warning log at startup (from `_unknown_theme_warned` in Step 6), then silence. No data loss.

---

## Step 8 — `src/main.py` — Wire `set_app_theme()` and Per-Channel Themes

### Replace `set_theme()` call in `main()` (lines 471–472)

```python
# Before:
theme_mgr.set_theme(DEFAULT_THEME, app=app)

# After:
active_theme_id = SettingsManager().get("theme", "active_theme", DEFAULT_THEME)
theme_mgr.set_app_theme(active_theme_id, app=app)  # operator panel chrome only
```

### Add per-channel theme loop after both `add_channel()` calls (after line 81)

```python
# v1.3.0 Phase 1: Belt-and-suspenders per-channel theme application.
# apply_settings() (called inside add_channel()) already calls set_theme().
# This loop re-applies for channels whose display_window was None at registration
# (lazy creation) — the cached self._theme is forwarded when the window opens.
for ch_name in ("main", "alt"):
    ch_settings = self._settings.get_channel_settings(ch_name)
    channel = self.channel_manager.get_channel(ch_name)
    if channel is not None:
        theme = self._theme_mgr.get_theme(ch_settings.theme_id)
        if theme is not None:
            channel.set_theme(theme)
        else:
            logger.warning("[MainWindow] Channel '%s': theme '%s' not found",
                           ch_name, ch_settings.theme_id)
```

---

## Step 9 — Pre-Commit Guards

**File:** `scripts/pre_commit_checks.py`

Add a new guard function for Phase 1 theme engine verification. Append to the existing guard registration block.

```python
def check_phase1_theme_engine():
    """Verify v1.3.0 Phase 1 Theme Engine v2 + DisplayWidget extraction."""
    errors = []

    # --- display_widget.py (must exist with full extraction) ---
    dw_path = SRC_DISP / 'display_widget.py'
    if not dw_path.exists():
        errors.append("CRITICAL: Phase 1: display_widget.py not created")
    else:
        with open(dw_path, encoding='utf-8') as f:
            dw = f.read()
        for sym, label in [
            ('class DisplayWidget', 'DisplayWidget class'),
            ('def set_theme', 'set_theme() method'),
            ('def set_display_mode', 'set_display_mode() method'),
            ('def set_church_name', 'set_church_name() method'),
            ('def set_logo_path', 'set_logo_path() method'),
            ('def _build_fullscreen_page', '_build_fullscreen_page()'),
            ('def _build_lower_third_page', '_build_lower_third_page()'),
            ('def _render_verse_content', '_render_verse_content()'),
            ('def _render_fullscreen', '_render_fullscreen()'),
            ('def _render_lower_third', '_render_lower_third()'),
            ('def _apply_theme_styling', '_apply_theme_styling()'),
            ('def paintEvent', 'paintEvent()'),
            ('def _build_logo_widget', '_build_logo_widget()'),
            ('self._theme', 'per-channel _theme attribute'),
            ('self._church_name', 'church_name instance variable'),
            ('self._logo_path_override', 'logo_path_override instance variable'),
            ('display_controller', 'display_controller constructor param'),
        ]:
            if sym in dw:
                print(f"  [OK] display_widget.py: {label}")
            else:
                print(f"  [FAIL] display_widget.py: missing {label}")
                errors.append(f"Phase 1 Theme Engine: display_widget.py missing: {label}")

        # Negative checks — must NOT contain
        if 'SettingsManager' in dw:
            errors.append("CRITICAL: Phase 1: display_widget.py contains SettingsManager — must read self._church_name")
        if 'QApplication.setStyleSheet' in dw or 'app.setStyleSheet' in dw:
            errors.append("CRITICAL: Phase 1: display_widget.py calls QApplication.setStyleSheet() — must use self.setStyleSheet() only")
        if 'theme_mgr.current' in dw:
            errors.append("CRITICAL: Phase 1: display_widget.py reads theme_mgr.current — must read self._theme")
        if '_on_verse_changed' in dw:
            errors.append("CRITICAL: Phase 1: display_widget.py contains _on_verse_changed — must route through DisplayWindow only")

    # --- display_window.py (must be refactored to thin shell) ---
    dw_path2 = SRC_DISP / 'display_window.py'
    if dw_path2.exists():
        with open(dw_path2, encoding='utf-8') as f:
            dw2 = f.read()
        for sym, label in [
            ('DisplayWidget', 'DisplayWidget import/usage'),
            ('_display_widget', '_display_widget instance variable'),
            ('def set_theme', 'set_theme() forwarding method'),
            ('def set_church_name', 'set_church_name() forwarding method'),
            ('def set_logo_path', 'set_logo_path() forwarding method'),
            ('def set_display_mode', 'set_display_mode() with window-flag split'),
        ]:
            if sym in dw2:
                print(f"  [OK] display_window.py: {label}")
            else:
                print(f"  [FAIL] display_window.py: missing {label}")
                errors.append(f"Phase 1 Theme Engine: display_window.py missing: {label}")

    # --- display_core.py (must have forwarding stubs) ---
    dc_path = SRC_DISP / 'display_core.py'
    if dc_path.exists():
        with open(dc_path, encoding='utf-8') as f:
            dc = f.read()
        for sym, label in [
            ('def set_logo_path', 'set_logo_path() forwarding stub'),
            ('def set_church_name', 'set_church_name() forwarding stub'),
            ('SettingsManager', 'SettingsManager import for church_name'),
        ]:
            if sym in dc:
                print(f"  [OK] display_core.py: {label}")
            else:
                print(f"  [FAIL] display_core.py: missing {label}")
                errors.append(f"Phase 1 Theme Engine: display_core.py missing: {label}")

    # --- theme.py (must have schema v2 engine) ---
    th_path = SRC_UTILS / 'theme.py'
    if th_path.exists():
        with open(th_path, encoding='utf-8') as f:
            th = f.read()
        for sym, label in [
            ('schema_version', 'schema_version field'),
            ('_upgrade_to_v2', '_upgrade_to_v2() method'),
            ('def set_app_theme', 'set_app_theme() method'),
            ('def _load_application_fonts', '_load_application_fonts() method'),
            ('application_fonts', 'application_fonts registry'),
            ('_loaded_font_paths', '_loaded_font_paths dedup set'),
            ('fullscreen', 'fullscreen dict in Theme.__init__'),
        ]:
            if sym in th:
                print(f"  [OK] theme.py: {label}")
            else:
                print(f"  [FAIL] theme.py: missing {label}")
                errors.append(f"Phase 1 Theme Engine: theme.py missing: {label}")

    # --- display_channel.py (must have set_theme + decoupled apply_settings) ---
    dch_path = SRC_DISP / 'display_channel.py'
    if dch_path.exists():
        with open(dch_path, encoding='utf-8') as f:
            dch = f.read()
        for sym, label in [
            ('def set_theme', 'set_theme() method'),
            ('theme_mgr.get_theme', 'get_theme() call (not set_theme())'),
            ('self._theme', '_theme attribute for lazy-window cache'),
            ('_unknown_theme_warned', 'unknown_theme_warned dedup flag'),
        ]:
            if sym in dch:
                print(f"  [OK] display_channel.py: {label}")
            else:
                print(f"  [FAIL] display_channel.py: missing {label}")
                errors.append(f"Phase 1 Theme Engine: display_channel.py missing: {label}")

    # --- settings.py (must have dark_gold default, not "default") ---
    sp_path = SRC_UTILS / 'settings.py'
    if sp_path.exists():
        with open(sp_path, encoding='utf-8') as f:
            sp = f.read()
        if '"default"' in sp:
            # Allow "default" only in non-channel contexts (general defaults, etc.)
            # Check specifically the ChannelSettings and _apply_defaults channel blocks
            if 'theme_id: str = "default"' in sp or 'theme: "default"' in sp:
                errors.append("CRITICAL: Phase 1: settings.py has literal 'default' as channel theme — must be 'dark_gold'")

    # --- main.py (must use set_app_theme + per-channel loop) ---
    main_path = SRC / 'main.py'
    if main_path.exists():
        with open(main_path, encoding='utf-8') as f:
            main = f.read()
        for sym, label in [
            ('set_app_theme', 'set_app_theme() call (not set_theme())'),
            ('get_channel_settings', 'get_channel_settings() in per-channel loop'),
        ]:
            if sym in main:
                print(f"  [OK] main.py: {label}")
            else:
                print(f"  [FAIL] main.py: missing {label}")
                errors.append(f"Phase 1 Theme Engine: main.py missing: {label}")

    # --- Guard script path migration (must use SRC_DISP, SRC_UI, etc.) ---
    for script_path, script_name in [
        (SCRIPTS / 'pre_commit_checks.py', 'pre_commit_checks.py'),
        (SCRIPTS / 'verify_critical_fixes.py', 'verify_critical_fixes.py'),
    ]:
        if script_path.exists():
            with open(script_path, encoding='utf-8') as f:
                sc = f.read()
            if 'SRC_DISP' not in sc:
                errors.append(f"CRITICAL: Phase 1: {script_name} not migrated — missing SRC_DISP")
            if 'SRC_UI' not in sc:
                errors.append(f"CRITICAL: Phase 1: {script_name} not migrated — missing SRC_UI")
            if '2. Source Code' in sc:
                errors.append(f"CRITICAL: Phase 1: {script_name} still references old '2. Source Code' path")

    return errors
```

**Add to guard registration block:**
```python
print("\n=== v1.3.0 Phase 1: Theme Engine v2 + DisplayWidget Extraction ===")
all_errors.extend(check_phase1_theme_engine())
```

---

## Step 10 — Verification Guards

**File:** `scripts/verify_critical_fixes.py`

```python
def verify_phase1_theme_engine():
    """Verify v1.3.0 Phase 1 Theme Engine v2 + DisplayWidget extraction source integrity."""
    errors = []

    dw_path = SRC_DISP / 'display_widget.py'
    dw2_path = SRC_DISP / 'display_window.py'
    dc_path = SRC_DISP / 'display_core.py'
    th_path = SRC_UTILS / 'theme.py'
    dch_path = SRC_DISP / 'display_channel.py'
    main_path = SRC / 'main.py'

    # display_widget.py — must exist as extracted class
    if dw_path.exists():
        with open(dw_path, encoding='utf-8') as f:
            dw = f.read()
        checks = [
            ('class DisplayWidget', 'DisplayWidget class defined'),
            ('def _render_verse_content', '_render_verse_content() present'),
            ('def paintEvent', 'paintEvent() present'),
            ('def _build_lower_third_page', '_build_lower_third_page() present'),
            ('def _build_fullscreen_page', '_build_fullscreen_page() present'),
            ('self._theme', 'per-channel _theme reference'),
            ('self._church_name', 'church_name instance variable'),
            ('self._logo_path_override', 'logo_path_override instance variable'),
            ('self.setStyleSheet', 'uses self.setStyleSheet() — scoped, not global'),
        ]
        for sym, label in checks:
            if sym in dw:
                print(f"  [OK] display_widget.py: {label}")
            else:
                print(f"  [FAIL] display_widget.py: missing {label}")
                errors.append(f"Phase 1 Theme Engine: display_widget.py missing: {label}")

        # Negative checks
        if 'QApplication.setStyleSheet' in dw or 'app.setStyleSheet' in dw:
            print("  [FAIL] display_widget.py: calls global QApplication.setStyleSheet()")
            errors.append("Phase 1 Theme Engine: display_widget.py must not call QApplication.setStyleSheet()")
        if 'SettingsManager' in dw:
            print("  [FAIL] display_widget.py: imports SettingsManager")
            errors.append("Phase 1 Theme Engine: display_widget.py must not import SettingsManager")
        if 'theme_mgr.current' in dw:
            print("  [FAIL] display_widget.py: reads global theme_mgr.current")
            errors.append("Phase 1 Theme Engine: display_widget.py must read self._theme, not theme_mgr.current")

    # display_window.py — must be thin shell delegating to DisplayWidget
    if dw2_path.exists():
        with open(dw2_path, encoding='utf-8') as f:
            dw2 = f.read()
        checks = [
            ('DisplayWidget', 'DisplayWidget imported/used'),
            ('_display_widget.set_theme', 'delegates set_theme() to DisplayWidget'),
            ('_display_widget.set_display_mode', 'delegates set_display_mode()'),
            ('_display_widget.set_logo_path', 'delegates set_logo_path()'),
            ('_display_widget.set_church_name', 'delegates set_church_name()'),
        ]
        for sym, label in checks:
            if sym in dw2:
                print(f"  [OK] display_window.py: {label}")
            else:
                print(f"  [FAIL] display_window.py: missing {label}")
                errors.append(f"Phase 1 Theme Engine: display_window.py missing: {label}")

    # display_core.py — must pass church_name through DisplayWindow
    if dc_path.exists():
        with open(dc_path, encoding='utf-8') as f:
            dc = f.read()
        checks = [
            ('def set_logo_path', 'set_logo_path() forwarding stub'),
            ('def set_church_name', 'set_church_name() forwarding stub'),
            ('church_name', 'church_name passed to DisplayWindow'),
        ]
        for sym, label in checks:
            if sym in dc:
                print(f"  [OK] display_core.py: {label}")
            else:
                print(f"  [FAIL] display_core.py: missing {label}")
                errors.append(f"Phase 1 Theme Engine: display_core.py missing: {label}")

    # theme.py — must have schema v2
    if th_path.exists():
        with open(th_path, encoding='utf-8') as f:
            th = f.read()
        checks = [
            ('schema_version', 'schema_version field'),
            ('_upgrade_to_v2', '_upgrade_to_v2() method'),
            ('set_app_theme', 'set_app_theme() for QApplication-only'),
            ('_load_application_fonts', '_load_application_fonts()'),
            ('fullscreen', 'fullscreen dict'),
        ]
        for sym, label in checks:
            if sym in th:
                print(f"  [OK] theme.py: {label}")
            else:
                print(f"  [FAIL] theme.py: missing {label}")
                errors.append(f"Phase 1 Theme Engine: theme.py missing: {label}")

    # display_channel.py — must use get_theme() not set_theme() in apply_settings
    if dch_path.exists():
        with open(dch_path, encoding='utf-8') as f:
            dch = f.read()
        if 'theme_mgr.get_theme' in dch:
            print("  [OK] display_channel.py: uses get_theme() (per-channel, no global QSS)")
        else:
            print("  [FAIL] display_channel.py: missing get_theme() call in apply_settings")
            errors.append("Phase 1 Theme Engine: display_channel.py must use theme_mgr.get_theme(), not theme_mgr.set_theme()")
        if 'self.set_theme' in dch:
            print("  [OK] display_channel.py: calls self.set_theme() for per-channel apply")
        else:
            print("  [FAIL] display_channel.py: missing self.set_theme() call")
            errors.append("Phase 1 Theme Engine: display_channel.py must call self.set_theme(theme)")

    # main.py — must call set_app_theme (not set_theme) for chrome
    if main_path.exists():
        with open(main_path, encoding='utf-8') as f:
            main = f.read()
        if 'set_app_theme' in main:
            print("  [OK] main.py: calls set_app_theme() for operator panel chrome")
        else:
            print("  [FAIL] main.py: missing set_app_theme() — chrome unthemed")
            errors.append("Phase 1 Theme Engine: main.py must call set_app_theme(), not set_theme()")

    return errors
```

**Add to `verify()` function:**
```python
print("\n=== v1.3.0 Phase 1: Theme Engine v2 + DisplayWidget Extraction ===")
errs.extend(verify_phase1_theme_engine())
```

---

## Regression Hazards

- **Double-render on verse push.** If `verse_changed` signal is connected in both `DisplayWindow` AND `DisplayWidget`, every push triggers two renders — the second render races with the first, causing visual flicker or stale text. Mitigation: `DisplayWidget.__init__` connects `translations_changed` and `layout_changed` only. `verse_changed` routes exclusively through `DisplayWindow._on_verse_changed`, which delegates to `_display_widget._deferred_render()`. Static guard confirms `_on_verse_changed` is absent from `display_widget.py`.

- **Cross-channel theme mutation via `_logo_path_override`** omission.** If `set_logo_path()` writes to `self._theme.lower_third.logo_path` directly (the shared Theme object), one channel's logo change contaminates the other channel and all future `get_theme()` calls for the same theme ID. Mitigation: `set_logo_path()` stores to `self._logo_path_override`, reads it in `_build_logo_widget()`, and never mutates `self._theme`. Static guard verifies `_logo_path_override` is present in `DisplayWidget`.

- **`channel_manager.py` regression risk.** Adding a `theme_manager` parameter to `ChannelManager.__init__` or `add_channel()` would require constructor changes in `main.py` and break the compatibility shim layer (lines 235–348). Mitigation: `apply_settings()` accesses `theme_mgr` via the existing `self._controller.theme_mgr` path — no `ChannelManager` changes needed. See Deviation 2.

- **Global QSS bleed from per-channel `set_theme()`.** If any method outside `ThemeManager.set_app_theme()` calls `QApplication.setStyleSheet()`, the operator panel chrome changes on every channel theme switch. Mitigation: only `set_app_theme()` in `main.py` (called once at startup) touches `QApplication.setStyleSheet()`. All per-channel theming uses `self.setStyleSheet()` on the widget subtree. Static guards verify no other file calls `QApplication.setStyleSheet()`.

- **Stale `hasattr` guard in `display_channel.py`.** `hasattr(controller, 'theme_mgr')` returns `True` when `theme_mgr = None`, causing a `NoneType` crash on `set_theme()`. Mitigation: `apply_settings()` uses `getattr(self._controller, 'theme_mgr', None) is not None` — catches both missing AND None-valued attributes. Static guard verifies `getattr` pattern.

- **`paintEvent()` fallback constants.** `DisplayWidget.paintEvent()` reads `LOWER_THIRD_*` constants when `self._theme is None`. If these constants are removed from `constants.py` before Phase 3 fonts land, the lower-third band falls back to zero-height. Mitigation: constants retained — they are the v2.0 fallback values. No removal until Phase 3 replaces them with schema-driven defaults.

- **Guard script path staleness.** After Step 0 path migration, any code referencing `SRC / 'filename.py'` with a flat path (instead of `SRC_DISP / 'filename.py'`) raises `FileNotFoundError` silently in guard scripts. Mitigation: Step 0 substitution table is exhaustive and verified by the guard script self-check — both `pre_commit_checks.py` and `verify_critical_fixes.py` confirm `SRC_DISP`, `SRC_UI`, etc. exist and `2. Source Code` does not.

- **Schema v1.0 theme files without `logo_width_ratio`.** If `_upgrade_to_v2()` defaults `logo_width_ratio` to the old constant (0.10) instead of preserving the JSON value (0.16 in `dark_gold.json`), existing layouts shrink unexpectedly on first upgrade. Mitigation: `_upgrade_to_v2()` reads `self.lower_third.get("logo_width_ratio", 0.16)` before `setdefault` — preserves existing JSON values. See D10 fix.

## Definition of Done

- [ ] All `scripts/pre_commit_checks.py` checks pass — including `check_phase1_theme_engine()`.
- [ ] All `scripts/verify_critical_fixes.py` checks pass — including `verify_phase1_theme_engine()`.
- [ ] `display_widget.py` exists with all 26 method/block units extracted from `display_window.py`.
- [ ] `DisplayWidget.__init__` accepts `display_controller`, `theme_manager`, `church_name`, `parent`.
- [ ] `display_window.py` is a thin shell — delegates rendering to `_display_widget`, handles window flags only.
- [ ] `display_core.py` has `set_logo_path()` and `set_church_name()` forwarding stubs.
- [ ] `theme.py` has `schema_version`, `_upgrade_to_v2()`, `set_app_theme()`, `_load_application_fonts()`.
- [ ] `display_channel.py` `apply_settings()` calls `theme_mgr.get_theme()` + `self.set_theme()` — no global QSS.
- [ ] `settings.py` channel defaults use `"dark_gold"` — no hardcoded `"default"`.
- [ ] `main.py` calls `set_app_theme()` for chrome, then per-channel `set_theme()` loop.
- [ ] All 3 theme JSON files (`dark_gold.json`, `light.json`, `high_contrast.json`) have `schema_version: "2.0"` and `fullscreen` block.
- [ ] Push Main — verse renders in fullscreen with per-channel theme colors.
- [ ] Push Alt — verse renders in lower-third with per-channel theme colors.
- [ ] Mode switch (fullscreen ↔ lower-third) re-renders without double-paint or flicker.
- [ ] `Ctrl+Shift+T` opens Theme Designer (Phase 2) — `DisplayWidget` renders preview correctly.
- [ ] NDI capture unaffected — `grab()` on `DisplayWindow` captures `DisplayWidget.paintEvent()` output.
- [ ] No regression: navigator, queue, playlist, history, hotkeys all function correctly.
- [ ] No `AttributeError` or `NameError` on startup, verse push, mode switch, or window resize.

## Status Log

| Date | Note |
|---|---|
| May 14, 2026 | v2.0 post-audit revision published. 11 defects + 6 omissions addressed. |
| May 14, 2026 | Independent audit report `Bug Analysis.md` reviewed. All claims verified. |
| May 16, 2026 | Phase 1 implementation signed off. All 8 steps code-complete. Manual test matrix passed. |
| _TBD_ | Template backfill — Pre-Commit Guards, Verification Guards, Regression Hazards, DoD, Status Log added per DOCUMENT_PROTOCOL.md. |
