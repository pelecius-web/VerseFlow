# Thumbnail Renderer Overhaul — Implementation Plan

**Goal:** Surpass Bibleshow's 6-year-old theme picker at the same thumbnail size.
**Constraint:** Fixed 600×192 canvas → 300×96 card. No resizing.

---

## Phase 0 — Fix lower-third key bug

**File:** `src/ui/theme_designer.py` lines 1208–1209

Change:
```python
band_color = QColor(lt.get("band_color", c("bg_primary")))
band_opacity = float(lt.get("band_opacity", 0.85))
```

To:
```python
band_color = QColor(lt.get("background_color", c("bg_primary")))
band_opacity = float(lt.get("background_alpha", 0.85))
```

**Why:** `band_color` / `band_opacity` exist in zero theme JSONs. The live renderer at `display_widget.py:1329` correctly reads `background_alpha`. This makes the thumbnail lower-third strip match the live display.

---

## Phase 1 — Add `thumbnail_style` to the Theme model

**File:** `src/utils/theme.py`

### 1a. Module-level enum constants

Add after `KNOWN_SCHEMA_VERSIONS` (line 28):

```python
THUMBNAIL_BACKGROUND_MODES = {"diagonal", "radial", "vignette", "flat", "split", "wash"}
THUMBNAIL_SURFACES = {"none", "soft_grain", "paper", "glass", "broadcast_grid"}
THUMBNAIL_ACCENT_LAYOUTS = {"top_rule", "bottom_rule", "side_rail", "corner_bracket", "double_rule"}
THUMBNAIL_TEXT_TREATMENTS = {"live_centered"}  # single allowed value

DEFAULT_THUMBNAIL_STYLE = {
    "background_mode": "diagonal",
    "surface": "none",
    "accent_layout": "top_rule",
    # Reserved metadata for a future contrast pass; current renderer can ignore it safely.
    "contrast_boost": 1.0,
    "text_treatment": "live_centered",
}
```

### 1b. Normalization helper (single source of truth)

```python
def _normalize_thumbnail_style(self):
    """Apply defaults and validate enum values for thumbnail_style."""
    raw = getattr(self, "thumbnail_style", None) or {}
    normalized = dict(DEFAULT_THUMBNAIL_STYLE)
    for key in DEFAULT_THUMBNAIL_STYLE:
        if key in raw:
            normalized[key] = raw[key]
    # Validate enums — warn but don't crash on invalid values
    if normalized["background_mode"] not in THUMBNAIL_BACKGROUND_MODES:
        logger.warning("[Theme] Invalid thumbnail_style.background_mode '%s', using default",
                       normalized["background_mode"])
        normalized["background_mode"] = DEFAULT_THUMBNAIL_STYLE["background_mode"]
    if normalized["surface"] not in THUMBNAIL_SURFACES:
        logger.warning("[Theme] Invalid thumbnail_style.surface '%s', using default",
                       normalized["surface"])
        normalized["surface"] = DEFAULT_THUMBNAIL_STYLE["surface"]
    if normalized["accent_layout"] not in THUMBNAIL_ACCENT_LAYOUTS:
        logger.warning("[Theme] Invalid thumbnail_style.accent_layout '%s', using default",
                       normalized["accent_layout"])
        normalized["accent_layout"] = DEFAULT_THUMBNAIL_STYLE["accent_layout"]
    if normalized["text_treatment"] not in THUMBNAIL_TEXT_TREATMENTS:
        logger.warning("[Theme] Invalid thumbnail_style.text_treatment '%s', using default",
                       normalized["text_treatment"])
        normalized["text_treatment"] = DEFAULT_THUMBNAIL_STYLE["text_treatment"]
    self.thumbnail_style = normalized
```

### 1c. Theme.__init__ changes

At line ~103, after `self.typography` and before `_upgrade_to_v2()`:

```python
self.thumbnail_style: dict = data.get("thumbnail_style", {})
```

After `_upgrade_to_v2()` call and typography fallback, add:

```python
self._normalize_thumbnail_style()
```

**NOTE:** `_normalize_thumbnail_style()` runs AFTER `_upgrade_to_v2()`, so v1.0 themes that lack the section get the default. v2.0 themes with the section get it normalized. No duplication in the upgrade path.

### 1d. deep_copy() — critical omission fix

Add `thumbnail_style` to the data dict built in `deep_copy()` (around line 213):

```python
"thumbnail_style": copy.deepcopy(self.thumbnail_style),
```

### 1e. _to_dict() — serialization

Add `thumbnail_style` to the returned dict (around line 232):

```python
"thumbnail_style": self.thumbnail_style,
```

### 1f. CSS rgba() parse guard (defensive)

Keep this helper in `theme_designer.py`, not `theme.py`. `theme.py` currently has no PyQt6 dependency and should remain a model/schema module; the thumbnail renderer already imports `QColor`, so color parsing belongs beside the painter code.

Add a small helper in `theme_designer.py`:

```python
def _parse_color_safe(value: str, fallback: QColor | None = None) -> QColor:
    """Parse a color string safely.

    Handles hex, named colors, and CSS rgba()/rgb() strings. Falls back to the
    provided default color on parse failure — never crashes on malformed input.
    """
    c = QColor(value)
    if c.isValid():
        return c
    # Minimal rgba() parser for Qt-safe thumbnail rendering.
    m = re.fullmatch(
        r"rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)"
        r"(?:\s*,\s*(\d*\.?\d+)\s*)?\)",
        value,
    )
    if m:
        r, g, b = (int(m.group(i)) for i in range(1, 4))
        alpha = m.group(4)
        if alpha is None:
            return QColor(r, g, b)
        a = int(round(float(alpha) * 255))
        return QColor(r, g, b, max(0, min(255, a)))
    logger.warning("[Theme] Failed to parse color '%s'; using fallback", value)
    return fallback if fallback is not None else QColor(0, 0, 0)
```

Use this in the thumbnail renderer with explicit fallbacks:

- Background colors: fallback to `bg_primary` / `bg_secondary`
- Text and accent colors: fallback to the theme token defaults already in use

---

## Phase 2 — Add `thumbnail_style` to 10 built-in theme JSONs

Each built-in theme at `src/utils/themes/{id}.json` gets a `thumbnail_style` block.

| Theme | `background_mode` | `surface` | `accent_layout` |
|---|---|---|---|
| `dark_gold` | `diagonal` | `soft_grain` | `top_rule` |
| `crimson_red` | `vignette` | `glass` | `corner_bracket` |
| `forest_green` | `radial` | `soft_grain` | `bottom_rule` |
| `midnight_blue` | `split` | `broadcast_grid` | `side_rail` |
| `royal_purple` | `vignette` | `none` | `double_rule` |
| `slate_gray` | `flat` | `none` | `side_rail` |
| `warm_amber` | `radial` | `none` | `bottom_rule` |
| `high_contrast` | `flat` | `none` | `top_rule` |
| `light` | `flat` | `paper` | `top_rule` |
| `pastel_calm` | `flat` | `paper` | `top_rule` |

All include `"text_treatment": "live_centered"` and `"contrast_boost": 1.0`.
`contrast_boost` is reserved metadata for a later renderer pass and does not need to change the first implementation of the painter helpers.

**Note:** `test.json` is NOT a built-in. Update only the 10 file names matching `BUILTIN_THEME_IDS`. Custom themes without `thumbnail_style` fall back to defaults — tested in Phase 5.

---

## Phase 3 — Refactor `_generate_theme_thumbnail` into paint helpers

**File:** `src/ui/theme_designer.py`

Extract three dispatchers from `_generate_theme_thumbnail`. Original method flow becomes:

```
painter setup → _paint_thumb_background → _paint_thumb_surface
→ reference text → _paint_thumb_accent(under_text) → fitted verse text
→ lower-third strip → _paint_thumb_accent(over_band) → footer → painter.end()
```

### 3a. Module-level noise tile (deterministic `soft_grain`)

At module top in `theme_designer.py`, compute once:

```python
import random as _random
_SEED = 42
_NOISE_TILE: QPixmap | None = None

def _get_noise_tile(size: int = 128) -> QPixmap:
    """Return a precomputed noise tile (deterministic seed, cached)."""
    global _NOISE_TILE
    if _NOISE_TILE is not None:
        return _NOISE_TILE
    rng = _random.Random(_SEED)
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    for y in range(size):
        for x in range(size):
            alpha = rng.randint(0, 12)  # 0–12 out of 255
            if alpha > 0:
                painter.setPen(QColor(255, 255, 255, alpha))
                painter.drawPoint(x, y)
    painter.end()
    _NOISE_TILE = pix
    return _NOISE_TILE
```

### 3b. Background mode dispatcher

`_paint_thumb_background(painter, style, bg_primary, bg_secondary, W, H)`:

| Mode | Implementation |
|---|---|
| `diagonal` | `QLinearGradient(0, 0, W, H)` — current behavior, unchanged |
| `radial` | `QRadialGradient(W * 0.5, H * 0.35, max(W, H) * 0.8)` — center glow |
| `vignette` | Darken edges via `QPainterPath` frame: fill full rect with `bg_primary`, then overlay a centered rect with `bg_secondary` gradient fading to transparent at edges |
| `flat` | `painter.fillRect(0, 0, W, H, bg_primary)` — no gradient |
| `split` | Top band `bg_secondary` (0 → H*0.4), bottom band `bg_primary` (H*0.4 → H) |
| `wash` | Solid `bg_primary` base + radial `bg_secondary` glow at 30% opacity centered at (W*0.5, H*0.3) |

### 3c. Surface overlay dispatcher

`_paint_thumb_surface(painter, style, W, H)`:

| Surface | Implementation |
|---|---|
| `none` | No-op |
| `soft_grain` | Tile `_NOISE_TILE` across the rect via `painter.drawTiledPixmap(0, 0, W, H, _NOISE_TILE)` with `setCompositionMode(CompositionMode_Overlay)` then restore to `SourceOver` |
| `paper` | Subtle brightness variations: 3–4 horizontal strips of slightly lighter/darker rectangles with 3-5% alpha |
| `glass` | Diagonal highlight: `QLinearGradient` from top-left to center with white at 0% (15% alpha) fading to transparent at 50% |
| `broadcast_grid` | Evenly spaced horizontal lines (every 12px) in white at 3% alpha |

### 3d. Accent layout dispatcher

`_paint_thumb_accent(painter, style, color, W, H, ref_bottom_y, band_y, layer)`:

**`layer` parameter:** `"under_text"` draws behind verse. `"over_band"` draws after lower-third.

| Layout | Layer | Implementation |
|---|---|---|
| `top_rule` | `under_text` | 8px horizontal bar at `y = ref_bottom_y + 2`, span `24 → W-24`, full opacity |
| `bottom_rule` | `over_band` | 8px horizontal bar at `y = band_y - 8`, same span, full opacity |
| `side_rail` | `under_text` | 4px vertical strip at right edge `W-24 → W-20`, full height, full opacity |
| `corner_bracket` | `under_text` | L-shapes at top-right and bottom-left corners: 12px arms, 2px thickness |
| `double_rule` | `under_text` | Two 2px horizontal lines at `y = ref_bottom_y + 2` and `y = ref_bottom_y + 8`, same span, 60% opacity |

### 3e. CSS-safe color helper usage

Replace all `QColor(c(key))` calls in the thumbnail renderer with the local `_parse_color_safe(c(key), fallback=...)` helper.

---

## Phase 4 — Wire helpers into `_generate_theme_thumbnail`

Replace the inline gradient fill + accent bar code with dispatcher calls:

```python
style = theme.thumbnail_style

# Background
_paint_thumb_background(painter, style, bg_primary, bg_secondary, W, H)

# Surface overlay
_paint_thumb_surface(painter, style, W, H)

# Reference text (unchanged from current)
# ... existing ref text code ...

ref_bottom_y = 46  # after ref text + spacing

# Accent — under text
_paint_thumb_accent(painter, style, ref_color, W, H, ref_bottom_y, band_y=H-28, layer="under_text")

# Verse text (unchanged — uses _fit_thumb_font_size)
# ... existing verse text code ...

# Lower-third band (fixed keys from Phase 0)
# ... existing lower-third code, band_y = H - 28 ...

# Accent — over band
_paint_thumb_accent(painter, style, ref_color, W, H, ref_bottom_y, band_y=H-28, layer="over_band")

# Footer (unchanged)
```

---

## Phase 5 — Tests

**File:** `tests/test_thumbnail_rendering.py` (new)

All thumbnail-generation tests use `tempfile.TemporaryDirectory`, copying theme JSON into temp dirs. Never writes to `src/utils/themes/`.
Use either a temp-backed fake `ThemeManager` registry or `monkeypatch` the module-level `THEMES_DIR` used by `theme.py` so thumbnail generation resolves only temp files.

### Test A — Schema enum validation

Requires `QApplication` only if the test imports or instantiates Qt widgets; JSON-only checks stay headless.

```python
def test_all_builtin_thumbnail_styles_have_valid_enums():
    """Every built-in theme's thumbnail_style must use valid enum values."""
    for tid in BUILTIN_THEME_IDS:
        path = THEMES_DIR / f"{tid}.json"
        data = json.loads(path.read_text())
        ts = data.get("thumbnail_style", DEFAULT_THUMBNAIL_STYLE)
        assert ts["background_mode"] in THUMBNAIL_BACKGROUND_MODES, \
            f"{tid}: invalid background_mode '{ts['background_mode']}'"
        assert ts["surface"] in THUMBNAIL_SURFACES, \
            f"{tid}: invalid surface '{ts['surface']}'"
        assert ts["accent_layout"] in THUMBNAIL_ACCENT_LAYOUTS, \
            f"{tid}: invalid accent_layout '{ts['accent_layout']}'"
        assert ts["text_treatment"] in THUMBNAIL_TEXT_TREATMENTS, \
            f"{tid}: invalid text_treatment '{ts['text_treatment']}'"
```

### Test B — Fallback render identity

```python
def test_default_style_equals_absent_style():
    """Thumbnail with absent thumbnail_style must match default style output."""
    # Generate two thumbnails — one with no thumbnail_style key, one with defaults
    # Pixel-compare: they must be identical.
```

### Test C — Lower-third key correctness

```python
def test_lower_third_reads_background_color_not_band_color():
    """After Phase 0 fix, lower-third strip must reflect background_color/alpha."""
    # Theme with background_color="#ff0000", background_alpha=1.0
    # Sample a pixel inside the band but away from accents/separator (for example x=30, y=H-14) → must be #ff0000
```

### Test D — Font fitting boundaries

```python
def test_fit_thumb_font_size_returns_valid_range():
    """Fitted font must be 8–80pt and measured height ≤ verse_max_h."""
    # Requires the Qt app fixture from conftest.py.
    designer = ThemeDesignerPanel(theme_mgr=ThemeManager(), channel_manager=None)
    for verse_text in [SAMPLE_VERSES[0]["text"], SAMPLE_VERSES[1]["text"], SAMPLE_VERSES[2]["text"]]:
        size = designer._fit_thumb_font_size(verse_text, "Segoe UI", 400, 552, 78)
        assert 8 <= size <= 80
        # Measure and verify fits
```

### Test E — Mode signature distinctness

```python
def test_background_modes_produce_different_output():
    """Same palette + different background_mode → pixels must differ."""
    # Generate diagonal and vignette thumbnails with identical colors
    # Sample pixel values: >50% of positions must differ
```

### Test F — Luminance distribution differs across themes

```python
def test_similar_dark_themes_have_different_luminance():
    """Royal Purple and Slate Gray must have different luminance histograms."""
    # Generate both thumbnails
    # Compute luminance histograms (Y = 0.299R + 0.587G + 0.114B)
    # Histograms must differ by KS test or mean/std deviation
```

### Test G — Card load safety (existing test, still valid)

Existing `test_thumbnail_show_when_file_exists` covers this. No change needed.

### Test H — Cleanup safety

Existing `test_delete_cleans_thumb_file` and `test_delete_skips_missing_thumb` cover this. No change needed.

### Test I — Deep copy preservation

Add a regression test that `Theme.deep_copy()` preserves `thumbnail_style` and that mutating the copy does not affect the source theme.

---

## Phase 6 — Visual verification script

**File:** `scripts/regenerate_thumbs_contact_sheet.py` (new)

```python
"""Regenerate all built-in thumbnails and produce a contact-sheet for review."""
# 1. Copy built-in theme JSONs into a temp workspace or build temp Theme objects with temp source_path values
# 2. Instantiate a QApplication and ThemeDesignerPanel headlessly
# 3. Pass the temp-backed ThemeManager into ThemeDesignerPanel and do not touch the live theme folder
# 4. Generate thumbnails without touching the tracked theme files in src/utils/themes/
# 5. Stitch the results into a single contact-sheet PNG for side-by-side review
# 6. Save to logs/thumbnails_contact_sheet.png
```

Compare against `logs/Bibleshow.png`. Human judgment call.

---

## Execution order

```
Phase 0  (1 file,    1 line changed)       ← fix lower-third bug
Phase 1  (1 file,    ~60 lines added)      ← Theme model + enum constants + deep_copy + _to_dict
Phase 2  (10 files,  ~6 lines each)        ← JSON thumbnail_style blocks
Phase 3  (1 file,    ~200 lines added)     ← paint helpers + noise tile
Phase 4  (1 file,    ~30 lines changed)    ← wire dispatchers
Phase 5  (1 file,    ~120 lines added)     ← tests (all use temp dirs)
Phase 6  (1 file,    ~40 lines)            ← contact-sheet script
```

Each phase is independently testable. Phase 0 works standalone. Phase 1–2 are model/data (no rendering). Phase 3–4 are rendering. Phase 5 validates everything. Phase 6 is visual QA.

---

## Review fixes incorporated

| # | Review point | Resolution |
|---|---|---|
| 1 | `deep_copy()` omission | Phase 1d — added |
| 2 | `_upgrade_to_v2()` redundancy | Phase 1c — `_normalize_thumbnail_style()` runs once after upgrade |
| 3 | Enum constants | Phase 1a — module-level sets in `theme.py` |
| 4 | Custom theme JSON files | Phase 2 note — update only 10 built-in IDs; tests iterate `BUILTIN_THEME_IDS` |
| 5 | Accent layer ordering | Phase 3d/4 — two-pass painting with `layer` parameter |
| 6 | Deterministic noise | Phase 3a — `_SEED = 42`, cached `_NOISE_TILE` |
| 7 | Weak pixel variance test | Phase 5 — replaced with mode-signature (E) + luminance-distribution (F) + fallback-identity (B) |
| 8 | CSS rgba() guard | Phase 1f — local `_parse_color_safe` helper in `theme_designer.py` |
| 9 | Temp file safety | Phase 5 — all tests use `tempfile.TemporaryDirectory` |
| 10 | Visual contact sheet | Phase 6 — `scripts/regenerate_thumbs_contact_sheet.py` |
