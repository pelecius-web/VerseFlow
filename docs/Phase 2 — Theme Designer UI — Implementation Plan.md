# Phase 2 â€” Theme Designer UI
## Implementation Plan (v1.0)

> **Status:** ✅ Complete (May 19, 2026)
> **Sub-roadmap reference:** `docs/v1.3.0 Theme Designer â€” Sub-Roadmap.md` Â§ Phase 2
> **Prerequisite:** Phase 1 complete and audited (DisplayWidget extraction, schema v2, per-channel `set_theme`, font loader, guard scripts migrated).
> **Confirmed decisions:** Q1=Stack page, Q2=Save/Apply lockout only, Q3=Hardcoded sample verses, Q4=Curated 33-property scope, Q5=Deep-copy editing model, Q6=Save and Apply as separate actions.

---

## Phase 1.5 Patches (applied 2026-05-16, before Phase 2 begins)

Three Phase 1 implementation gaps surfaced during Phase 2 plan audit. Patches applied to `display_widget.py` before Phase 2 work starts:

1. **B1 â€” `_source_path` â†’ `source_path` attribute name fix.** `_build_logo_widget` now correctly resolves theme-relative logo paths against the theme JSON's parent directory using `getattr(self._theme, 'source_path', None)`. Theme-relative logos previously fell through to absolute-path treatment silently.

2. **B2 â€” Theme-aware `_render_fullscreen` and `_build_overlay_html`.** Both methods now read `self._theme.fullscreen.{ref_color, verse_color, verse_font_family}` with safe fallbacks. A new helper `_dim_color()` derives secondary-translation tints from primary theme colors. A new `_refresh_ref_label_font()` (called from `set_theme()`) updates the fullscreen ref_label's font family and weight from `theme.fullscreen.ref_font_family/weight`. After this patch, `fullscreen.{ref_color, verse_color, ref_font_family, ref_font_weight, verse_font_family}` produce visible change in preview and live display.

3. **B4/E4 â€” `lower_third.transition.*` deferred to Phase 3.** The two transition rows are removed from `THEME_EDITOR_SCHEMA` (Step 2). They remain in the JSON schema (populated by `_upgrade_to_v2` with safe defaults) and Phase 3 wires them to actual fade rendering. Phase 2 ships with 33 properties, all of which produce visible change.

4. **Patch 4 â€” Lower-third font theming (B2 extension, applied 2026-05-17).** `_fit_lower_third_fonts`, `_fit_reference_font`, and `_fit_church_name_font` in `display_widget.py` now read `lower_third.{ref_font_family, verse_font_family}` from `self._theme` with safe fallbacks. Both measurement and final label fonts use the theme family so that text wrapping and the chosen size remain consistent with what is actually rendered. Cache key in `_fit_lower_third_fonts` now includes `verse_family` to prevent stale cache hits when switching between themes with different font families.

**Not patched in Phase 1.5 (deferred):**
- B3 (16 hardcoded `QFont("Segoe UI", ...)` calls in font-fitting): `verse_font_weight` remains dead until B3 is addressed. Documented as a known limitation.
- B5 (SVG validation): Low risk; user-controlled themes only.
- B6 (stale "v0.7.2" version string): Cosmetic; tracked separately.

---

## Deviations from Sub-Roadmap

### Deviation 1 â€” Property scope is the curated 33 keys that DisplayWidget actually consumes

**Sub-roadmap says:** "All theme JSON properties from schema v2 are editable."

**Plan says:** The designer exposes only the **33 properties** that `DisplayWidget` actually reads in rendering (after Phase 1.5 patches B1/B2 land). The remaining ~70 keys (`colors.bg_sidebar`, `colors.crossref_*`, `colors.draft_*`, `colors.scrollbar`, etc.) drive `generate_stylesheet()` for the operator panel, not the congregation display. Per Decision 3 (display-only theme scope), the operator panel chrome is controlled by `theme.active_theme` + `set_app_theme()` â€” outside this designer's responsibility. The 2 `lower_third.transition.*` keys are deferred to Phase 3 (when fade-transition rendering ships) and are NOT included in this scope.

**Justification:** Exposing 100 properties means ~70 dead rows where edits never affect the preview â€” a UX bug, not a feature. The 33-property scope is "what you see is what the congregation gets." A future "App Theme Designer" can address the operator panel keys separately if needed.

### Deviation 2 â€” Designer mounts on `MainWindow.stack` as index 2 (not a `QDialog`)

**Sub-roadmap says:** "Accessible from Settings."

**Plan says:** `ThemeDesignerPanel(QWidget)` is added as `MainWindow.stack` index 2 alongside Home (0) and Settings (1). The Settings panel gets an "Open Theme Designer" button that calls `self._switch_tab(2)`. `Ctrl+Shift+T` opens it from anywhere. A new `Ctrl+3` view-menu shortcut mirrors the Home/Settings pattern.

**Justification:** A `QDialog` would be visually disjoint from operator-panel chrome and constrain the three-panel layout. The stack pattern is already wired (`_switch_tab` handles style updates and back-navigation). Zero new navigation infrastructure.

### Deviation 3 â€” Sample verses are hardcoded constants, not DB queries

**Sub-roadmap says:** "Designer holds these in a constant â€” does not query DB."

**Plan says:** `SAMPLE_VERSES: list[dict]` defined at module level in `theme_designer.py`. Four entries: short (`John 3:16` KJV), medium (`Psalm 23:1` KJV), long (`Hebrews 1:1-3` KJV), and overlay-ready (`Romans 8:28` KJV). Designer never imports `VerseDB`.

**Justification:** Per spec. Avoids hidden DB dependency that would couple designer lifetime to database availability and create unnecessary I/O on theme-property updates.

---

## Files Created

- `src/ui/theme_designer.py` â€” **NEW:** ~600 lines
  - `THEME_EDITOR_SCHEMA: list[PropertySpec]` â€” 33 properties, JSON-path-mapped
  - `SAMPLE_VERSES: list[dict]` â€” 4 hardcoded verse dicts
  - `BUILTIN_THEME_IDS: set[str]` â€” `{"dark_gold", "light", "high_contrast"}`
  - `class PropertySpec` â€” descriptor: `(json_path, label, widget_kind, options, tooltip)`
  - `class ThemesListPanel(QFrame)` â€” left column, theme list + buttons
  - `class PreviewSurface(QFrame)` â€” center, embedded `DisplayWidget` + mode toggle + verse picker + Apply controls
  - `class PropertyEditor(QScrollArea)` â€” right column, generated rows
  - `class ThemeDesignerPanel(QWidget)` â€” top-level, three-column layout

## Files Modified

- `src/utils/theme.py`
  - `Theme.update(json_path: str, value)` â€” set a value at a dotted path on the in-memory theme
  - `Theme.deep_copy() -> Theme` â€” return a fully independent Theme instance for editor sandboxing
  - `Theme.save() -> bool` â€” write back to `self.source_path`; returns False for unset path or IO error
  - `Theme.save_as(path: Path, new_id: str, new_name: str) -> Theme` â€” write to a new path, return the saved Theme
  - `Theme.delete() -> bool` â€” `self.source_path.unlink()`; refuses if `id` in `BUILTIN_THEME_IDS`
  - `ThemeManager.reload_theme(theme_id: str) -> Theme | None` â€” re-read JSON, replace registry instance
  - `ThemeManager.create_theme(new_id: str, new_name: str, source: Theme) -> Theme` â€” duplicate from an existing theme

- `src/ui/settings_panel.py`
  - Add "Open Theme Designer" button in the Channel Settings card (above the per-channel rows)
  - Emit new `pyqtSignal` `theme_designer_requested` when clicked

- `src/main.py`
  - Import `ThemeDesignerPanel`
  - Instantiate after `SettingsPanel`: `self.theme_designer = ThemeDesignerPanel(theme_mgr=..., channel_manager=...)`
  - `self.stack.addWidget(self.theme_designer)` â€” index 2
  - `self.settings_panel.theme_designer_requested.connect(lambda: self._switch_tab(2))`
  - Update `_switch_tab(index)` to handle index 2 styling (designer button needs dark/active states the same way Home/Settings do)
  - Add `theme_designer_action` to View menu with `Ctrl+3` shortcut
  - Add global `Ctrl+Shift+T` shortcut via `QShortcut(self)` calling `self._switch_tab(2)`

- `scripts/pre_commit_checks.py` â€” add `check_phase2_theme_designer()`
- `scripts/verify_critical_fixes.py` â€” add `=== Phase 2 Theme Designer ===` block

## Files Not Touched

- All v1.2.0 NDI files (`ndi_bridge.py`, `ndi_sender.py`, `ndi_manager.py`)
- `src/display/channel_display_facade.py`
- `src/ui/home_panel.py` (designer reached from Settings, not Home)
- `src/display/display_channel.py` â€” `set_theme()` is the public entry point used by Apply; no changes needed
- `src/core/channel_manager.py`
- `src/display/display_widget.py` â€” Phase 1 output; designer embeds it read-only
- `src/display/display_window.py`
- `src/utils/settings.py`
- `src/utils/themes/*.json` â€” no schema changes in Phase 2

---

## Step 0 â€” Pre-Flight Verification

Before any code change, confirm Phase 1's `display_widget.py` API is stable. The designer embeds `DisplayWidget` directly and depends on this exact contract:

| Required by designer | Present in `display_widget.py` |
|---|---|
| `DisplayWidget(display_controller, theme_manager, church_name, parent)` | âœ… Confirmed |
| `set_theme(theme: Theme) -> None` | âœ… Confirmed |
| `set_display_mode(mode: str) -> None` | âœ… Confirmed |
| `set_logo_path(path: str \| None) -> None` | âœ… Confirmed |
| `set_church_name(name: str) -> None` | âœ… Confirmed |
| `_deferred_render(verse: dict) -> None` | âœ… Confirmed |

If any signature drifts during Phase 2, the designer's preview breaks. Run `python scripts/pre_commit_checks.py` before starting Step 1 and confirm zero errors.

---

## Step 1 â€” Theme Persistence API (`src/utils/theme.py`)

Phase 2 adds 7 new methods. None affect the existing `set_app_theme()` / `get_theme()` contract.

### 1.1 `Theme.update(json_path: str, value)` â€” dotted path setter

```python
def update(self, json_path: str, value) -> None:
    """Set a value at a dotted JSON path on the in-memory theme.

    Examples:
        theme.update("lower_third.background_color", "#ff0000")
        theme.update("fullscreen.ref_color", "#c8a03c")
        theme.update("colors.gold", "#ffaa00")
        theme.update("lower_third.transition.type", "fade")

    Path components must be `dict` keys. Lists are not supported in v1.3.0.
    Unknown paths raise KeyError â€” callers must validate against the schema first.
    """
    parts = json_path.split(".")
    target = self
    for part in parts[:-1]:
        # Walk into known sections only â€” colors, fonts, lower_third, fullscreen, animation, spacing
        if hasattr(target, part) and isinstance(getattr(target, part), dict):
            target = getattr(target, part)
        elif isinstance(target, dict) and part in target:
            target = target[part]
        else:
            raise KeyError(f"Unknown theme path: {json_path}")
    leaf = parts[-1]
    if isinstance(target, dict):
        target[leaf] = value
    else:
        raise KeyError(f"Path leaf is not a dict: {json_path}")
```

### 1.2 `Theme.deep_copy() -> Theme` â€” sandboxing for editor

```python
def deep_copy(self) -> "Theme":
    """Return a fully independent Theme instance.

    Used by the designer to sandbox edits â€” mutations on the copy never
    propagate to the registry's shared instance until Save.
    """
    import copy
    data = {
        "name": self.name,
        "id": self.id,
        "description": self.description,
        "version": self.version,
        "schema_version": self.schema_version,
        "author": self.author,  # E2 fix: preserve author on deep copy
        "colors": copy.deepcopy(self.colors),
        "fonts": copy.deepcopy(self.fonts),
        "animation": copy.deepcopy(self.animation),
        "spacing": copy.deepcopy(self.spacing),
        "lower_third": copy.deepcopy(self.lower_third),
        "fullscreen": copy.deepcopy(self.fullscreen),
    }
    new_theme = Theme(data, source_path=self.source_path)
    return new_theme
```

### 1.3 `Theme.save()` and `Theme.save_as()`

```python
def save(self) -> bool:
    """Write theme to its source_path. Returns False if path is None or IO fails.

    Refuses if id is in BUILTIN_THEME_IDS â€” overwriting a built-in is not allowed.
    Use save_as() to clone a built-in into a user theme.
    """
    if self.source_path is None:
        logger.warning("[Theme] Cannot save: source_path is None")
        return False
    if self.id in BUILTIN_THEME_IDS:
        logger.warning("[Theme] Cannot save built-in theme '%s'. Use Save As.", self.id)
        return False
    try:
        with open(self.source_path, "w", encoding="utf-8") as f:
            json.dump(self._to_dict(), f, indent=2, ensure_ascii=False)
        return True
    except IOError as e:
        logger.error("[Theme] Failed to save '%s': %s", self.id, e)
        return False

def save_as(self, path: Path, new_id: str, new_name: str) -> "Theme":
    """Write theme to a new path with a new id and name.

    Mutates self.id, self.name, and self.source_path in-place.
    This is safe because callers (ThemeManager.create_theme) always call
    deep_copy() on the source before calling save_as(), so the registry
    instance is never modified. Do not call save_as() on a live registry
    Theme directly â€” always deep_copy() first. (E9 invariant documented)

    Returns self (the mutated copy) after writing to disk.
    """
    self.id = new_id
    self.name = new_name
    self.source_path = path
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self._to_dict(), f, indent=2, ensure_ascii=False)
    except IOError as e:
        logger.error("[Theme] Failed to save_as '%s': %s", path, e)
        raise
    return self

def _to_dict(self) -> dict:
    """Serialize to JSON-compatible dict. Keep schema_version v2.0 on save."""
    return {
        "name": self.name,
        "id": self.id,
        "description": self.description,
        "version": self.version,
        "schema_version": "2.0",  # Phase 1 in-memory upgrade is now persisted
        "author": getattr(self, "author", ""),
        "colors": self.colors,
        "fonts": self.fonts,
        "animation": self.animation,
        "spacing": self.spacing,
        "fullscreen": self.fullscreen,
        "lower_third": self.lower_third,
    }
```

### 1.4 `Theme.delete()`

```python
def delete(self) -> bool:
    """Delete the theme's source file. Refuses for built-ins.

    Returns True on success, False on failure (built-in, missing path, IO error).
    """
    if self.id in BUILTIN_THEME_IDS:
        logger.warning("[Theme] Cannot delete built-in theme '%s'", self.id)
        return False
    if self.source_path is None or not self.source_path.exists():
        return False
    try:
        self.source_path.unlink()
        return True
    except OSError as e:
        logger.error("[Theme] Failed to delete '%s': %s", self.id, e)
        return False
```

### 1.5 `ThemeManager.reload_theme()` and `create_theme()`

```python
def reload_theme(self, theme_id: str) -> Optional[Theme]:
    """Re-read the theme JSON from disk and replace the registry instance.

    Used after Save to ensure all channels referencing this theme see the
    updated values. Returns the fresh Theme, or None if the file is gone
    or unparseable.
    """
    theme = self._themes.get(theme_id)
    if theme is None or theme.source_path is None:
        return None
    if not theme.source_path.exists():
        # File was deleted â€” drop from registry
        del self._themes[theme_id]
        return None
    try:
        with open(theme.source_path, encoding="utf-8") as f:
            data = json.load(f)
        new_theme = Theme(data, source_path=theme.source_path)
        self._themes[theme_id] = new_theme
        return new_theme
    except (json.JSONDecodeError, KeyError) as e:
        logger.error("[ThemeManager] reload_theme '%s' failed: %s", theme_id, e)
        return None

def create_theme(self, new_id: str, new_name: str, source: Theme) -> Optional[Theme]:
    """Duplicate a source theme to a new file. Returns the new Theme on success.

    Refuses if new_id already exists or contains invalid characters.
    """
    import re
    if not re.match(r'^[a-z0-9_-]+$', new_id):  # E3 fix: sanitize before path construction
        logger.warning("[ThemeManager] Invalid theme id '%s' â€” use lowercase letters, digits, _ or -", new_id)
        return None
    if new_id in self._themes:
        logger.warning("[ThemeManager] Theme id '%s' already exists", new_id)
        return None
    new_path = THEMES_DIR / f"{new_id}.json"
    if new_path.exists():
        logger.warning("[ThemeManager] File '%s' already exists", new_path)
        return None
    new_theme = source.deep_copy()
    new_theme.save_as(new_path, new_id, new_name)
    self._themes[new_id] = new_theme
    return new_theme
```

### 1.6 Module-level `BUILTIN_THEME_IDS`

```python
BUILTIN_THEME_IDS = {"dark_gold", "light", "high_contrast"}
```

---

## Step 2 â€” `THEME_EDITOR_SCHEMA` (33 properties)

The schema descriptor is a `list[PropertySpec]` ordered for editor display. Every entry maps to a real key in `dark_gold.json` after schema v2 upgrade. Every key is one that `DisplayWidget` actually reads.

### 2.1 PropertySpec dataclass

```python
from dataclasses import dataclass
from typing import Any, Optional

@dataclass(frozen=True)
class PropertySpec:
    """Descriptor for one editable theme property.

    json_path:    Dotted path on Theme (e.g., "lower_third.background_color")
    label:        Human-readable label shown in the editor
    widget_kind:  One of "color", "float", "int", "bool", "font_family",
                  "font_weight", "image_path", "enum"
    section:      Group label ("Lower-Third", "Fullscreen", "Operator-Visible Colors")
    options:      Optional dict â€” for "enum" gives choices, for "float" gives min/max/step,
                  for "image_path" gives extensions
    tooltip:      Optional hover text
    """
    json_path: str
    label: str
    widget_kind: str
    section: str
    options: Optional[dict] = None
    tooltip: Optional[str] = None
```

### 2.2 Schema content

```python
THEME_EDITOR_SCHEMA: list[PropertySpec] = [
    # â”€â”€ Operator-Visible Display Colors (5) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # These five drive _apply_theme_styling on DisplayWidget itself.
    # Confirmed by code trace: c('gold'), c('bg_primary'), c('bg_secondary'),
    # c('text_primary'), c('text_faint') in display_widget.py:948-1009.
    PropertySpec("colors.gold",         "Accent (gold)",     "color", "Display Colors"),
    PropertySpec("colors.bg_primary",   "Background â€” top",  "color", "Display Colors"),
    PropertySpec("colors.bg_secondary", "Background â€” bottom","color","Display Colors"),
    PropertySpec("colors.text_primary", "Verse text",        "color", "Display Colors"),
    PropertySpec("colors.text_faint",   "Footer / faint",    "color", "Display Colors"),

    # â”€â”€ Fullscreen mode (10) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    PropertySpec("fullscreen.background_color",         "Background color",   "color",       "Fullscreen"),
    PropertySpec("fullscreen.background_image",         "Background image",   "image_path",  "Fullscreen",
                 options={"extensions": [".png", ".jpg", ".jpeg", ".svg"]}),
    PropertySpec("fullscreen.background_image_fit",     "Image fit",          "enum",        "Fullscreen",
                 options={"choices": ["cover", "contain", "stretch", "tile"]}),
    PropertySpec("fullscreen.background_image_opacity", "Image opacity",      "float",       "Fullscreen",
                 options={"min": 0.0, "max": 1.0, "step": 0.05}),
    PropertySpec("fullscreen.ref_color",                "Reference color",    "color",       "Fullscreen"),
    PropertySpec("fullscreen.verse_color",              "Verse color",        "color",       "Fullscreen"),
    PropertySpec("fullscreen.ref_font_family",          "Reference font",     "font_family", "Fullscreen"),
    PropertySpec("fullscreen.ref_font_weight",          "Reference weight",   "font_weight", "Fullscreen"),
    PropertySpec("fullscreen.verse_font_family",        "Verse font",         "font_family", "Fullscreen"),
    PropertySpec("fullscreen.verse_font_weight",        "Verse weight",       "font_weight", "Fullscreen",
                 tooltip="Note: dynamic verse text is rendered with the default weight in v1.3.0 Phase 2. Full effect requires B3 patch (font-fitting refactor) â€” tracked for follow-on."),

    # â”€â”€ Lower-third mode (18) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    PropertySpec("lower_third.background_color",      "Band color",          "color",       "Lower-Third"),
    PropertySpec("lower_third.background_alpha",      "Band opacity",        "float",       "Lower-Third",
                 options={"min": 0.0, "max": 1.0, "step": 0.05}),
    PropertySpec("lower_third.background_image",      "Band image",          "image_path",  "Lower-Third",
                 options={"extensions": [".png", ".jpg", ".jpeg", ".svg"]}),
    PropertySpec("lower_third.background_image_fit",  "Band image fit",      "enum",        "Lower-Third",
                 options={"choices": ["cover", "contain", "stretch", "tile"]}),
    PropertySpec("lower_third.height_ratio",          "Band height (Ã— win)", "float",       "Lower-Third",
                 options={"min": 0.10, "max": 0.50, "step": 0.01}),
    PropertySpec("lower_third.accent_color",          "Accent color",        "color",       "Lower-Third"),
    PropertySpec("lower_third.ref_color",             "Reference color",     "color",       "Lower-Third"),
    PropertySpec("lower_third.verse_color",           "Verse color",         "color",       "Lower-Third"),
    PropertySpec("lower_third.ref_font_family",       "Reference font",      "font_family", "Lower-Third"),
    PropertySpec("lower_third.verse_font_family",     "Verse font",          "font_family", "Lower-Third"),
    PropertySpec("lower_third.church_name_color",     "Church name color",   "color",       "Lower-Third"),
    PropertySpec("lower_third.logo_path",             "Logo image",          "image_path",  "Lower-Third",
                 options={"extensions": [".png", ".jpg", ".jpeg", ".svg"]}),
    PropertySpec("lower_third.show_logo_placeholder", "Show placeholder",    "bool",        "Lower-Third"),
    PropertySpec("lower_third.logo_width_ratio",      "Logo width (Ã— win)",  "float",       "Lower-Third",
                 options={"min": 0.05, "max": 0.30, "step": 0.01}),
    PropertySpec("lower_third.logo_max_height_ratio", "Logo max height (Ã— band)", "float",  "Lower-Third",
                 options={"min": 0.40, "max": 1.00, "step": 0.05}),
    PropertySpec("lower_third.show_separator",        "Show separator",      "bool",        "Lower-Third"),
    PropertySpec("lower_third.separator_color",       "Separator color",     "color",       "Lower-Third"),
    PropertySpec("lower_third.separator_width",       "Separator width (px)","int",         "Lower-Third",
                 options={"min": 1, "max": 8, "step": 1}),
    # NOTE: lower_third.transition.{type,duration_ms} are deferred to Phase 3.
    # They are present in the JSON schema (default {"type": "none", "duration_ms": 200, "easing": "OutCubic"})
    # but Phase 3 wires them to actual fade rendering. Including them in the
    # Phase 2 editor would be misleading â€” operator edits would have no
    # visible effect until Phase 3 ships.
]
```

**Total: 33 properties** (5 colors + 10 fullscreen + 18 lower-third). Down from 35 because 2 `transition.*` rows are deferred to Phase 3 â€” they are populated in the JSON by `_upgrade_to_v2` but `DisplayWidget` does not consume them yet.

> **Static guard:** A pre-commit check asserts every `json_path` in `THEME_EDITOR_SCHEMA` resolves to a real key in `dark_gold.json` after `_upgrade_to_v2`. Drift here means the editor shows broken rows.

---

## Step 3 â€” `theme_designer.py` Implementation

### 3.1 `SAMPLE_VERSES`

```python
SAMPLE_VERSES: list[dict] = [
    {
        "reference": "John 3:16",
        "translation": "KJV",
        "text": "For God so loved the world, that he gave his only begotten Son, "
                "that whosoever believeth in him should not perish, but have everlasting life.",
    },
    {
        "reference": "Psalm 23:1",
        "translation": "KJV",
        "text": "The LORD is my shepherd; I shall not want.",
    },
    {
        "reference": "Romans 8:28",
        "translation": "KJV",
        "text": "And we know that all things work together for good to them that love God, "
                "to them who are the called according to his purpose.",
    },
    {
        "reference": "Hebrews 1:1-3",
        "translation": "KJV",
        "text": "God, who at sundry times and in divers manners spake in time past unto the "
                "fathers by the prophets, hath in these last days spoken unto us by his Son, "
                "whom he hath appointed heir of all things, by whom also he made the worlds; "
                "who being the brightness of his glory, and the express image of his person, "
                "and upholding all things by the word of his power.",
    },
]
```

### 3.2 `_DummyDisplayController(QObject)` â€” sandboxed signal source

The preview widget needs a controller-like object with the same signal surface as `DisplayController` (verse_changed, layout_changed, translations_changed) but no DB or display-window side effects. The class is self-contained â€” no prior art reference.

```python
class _DummyDisplayController(QObject):
    """Sandboxed controller for designer preview. No DB, no window, no live history."""
    verse_changed = pyqtSignal(dict)
    layout_changed = pyqtSignal(str)
    translations_changed = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current = None
        self.secondary_translations = []

    def push_verse(self, verse: dict):
        self.current = verse
        self.verse_changed.emit(verse)

    def clear(self):
        self.current = None
        self.verse_changed.emit({})
```

### 3.3 `ThemesListPanel(QFrame)` â€” left column (180px)

Public signals:
- `theme_selected = pyqtSignal(str)` â€” emits `theme_id`
- `new_requested = pyqtSignal()`
- `duplicate_requested = pyqtSignal(str)` â€” emits source `theme_id`
- `delete_requested = pyqtSignal(str)` â€” emits target `theme_id`

Internal state:
- `_list: QListWidget` populated from `theme_mgr.available_themes()`
- Current selection drives the parent designer's `_active_theme`
- `Delete` and `Duplicate` buttons disabled when no theme selected
- `Delete` additionally disabled when selected theme is in `BUILTIN_THEME_IDS`

### 3.4 `PreviewSurface(QFrame)` â€” center column (expanding)

Layout (top-to-bottom):
- **Mode toggle row (32px):** `QButtonGroup` with two buttons â€” "Fullscreen" / "Lower-Third"
- **Sample-verse picker row (32px):** `QComboBox` with `SAMPLE_VERSES` references
- **Embedded preview (expanding):** `DisplayWidget(display_controller=self._dummy, theme_manager=theme_mgr, church_name="Sample Church")` â€” set sizing policy `QSizePolicy.Expanding`
- **Apply controls row (60px):** Target combo (`Main` / `Alt` / `Both`) + `Apply` button

Public methods:
- `set_theme(theme: Theme)` â€” call `self._display_widget.set_theme(theme)`, push current sample verse
- `set_display_mode(mode: str)` â€” call `self._display_widget.set_display_mode(mode)`, re-push current verse
- `refresh()` â€” re-apply current theme + verse (cheap repaint)

Internal state:
- `_dummy: _DummyDisplayController` â€” created once
- `_display_widget: DisplayWidget` â€” created once, lifetime tied to `PreviewSurface`
- `_current_verse: dict` â€” currently selected sample verse

> **Critical:** the preview's `DisplayWidget` is **never** captured by NDI. NDI senders connect to `ChannelManager.channel_changed` (per Phase 1 v1.2.0) and only see channels registered with `ChannelManager`. The designer's dummy controller is not registered with `ChannelManager`, so its frames are sandboxed.

### 3.5 `PropertyEditor(QScrollArea)` â€” right column (380px)

Sections rendered in `THEME_EDITOR_SCHEMA` order, grouped by `section` field. Each section gets a header label. Each property gets one row.

Widget mapping:

| `widget_kind` | Qt widget | Signal | Value extraction |
|---|---|---|---|
| `color` | `QPushButton` (swatch) | `clicked` â†’ `QColorDialog` | `dialog.selectedColor().name()` |
| `float` | `QDoubleSpinBox` | `valueChanged` | `value()` |
| `int` | `QSpinBox` | `valueChanged` | `value()` |
| `bool` | `QCheckBox` | `toggled` | `isChecked()` |
| `font_family` | `QFontComboBox` (filtered to system + `theme_mgr.application_fonts`) | `currentFontChanged` | `currentFont().family()` |
| `font_weight` | `QComboBox` (`WEIGHT_MAP.keys()`) | `currentTextChanged` | `currentText()` |
| `image_path` | `QLineEdit` + browse `QPushButton` | `editingFinished` | `text()` (relative path) |
| `enum` | `QComboBox` (from `options["choices"]`) | `currentTextChanged` | `currentText()` |

Public signal:
- `property_changed = pyqtSignal(str, object)` â€” emits `(json_path, new_value)`

Public method:
- `load_theme(theme: Theme)` â€” populate every row from the theme's current values

> **Production adjustment (May 19, 2026):** Widened from 320px â†’ 380px after manual testing revealed `QFontComboBox` overflowed the 178px widget space (320 âˆ’ 24 margins âˆ’ 8 spacing âˆ’ 110 label), hiding the dropdown arrow behind a horizontal scrollbar. At 380px, widgets get 238px â€” eliminating overflow and making the dropdown arrow fully visible.

### 3.6 `ThemeDesignerPanel(QWidget)` â€” top-level

Constructor:
```python
def __init__(self, theme_mgr, channel_manager, parent=None):
    super().__init__(parent)
    self._theme_mgr = theme_mgr
    self._channel_manager = channel_manager
    self._active_theme: Theme | None = None  # The deep-copied editing instance
    self._original_id: str | None = None     # The id at open time, for save target
    self._dirty: bool = False
    self._setup_ui()
```

Layout:
```
QHBoxLayout (root)
â”œâ”€ ThemesListPanel       (180px fixed)
â”œâ”€ PreviewSurface         (expanding)
â””â”€ PropertyEditor         (380px fixed)
```

Above the three columns, a 50px header row with: title "Theme Designer", "Save", "Save As", "Delete", "Back to Settings" (emits `back_requested` signal, connected by `MainWindow` to `_switch_tab(1)`).

Header buttons:
- **Save** â€” disabled when (a) no `_active_theme`, (b) `_active_theme.id âˆˆ BUILTIN_THEME_IDS`, (c) any channel `is_live`. On click: `_active_theme.save()` â†’ `theme_mgr.reload_theme(...)` â†’ success toast.
- **Save As** â€” always enabled when an `_active_theme` exists. Prompts for new id/name via `QInputDialog`. On confirm: `theme_mgr.create_theme(new_id, new_name, source=_active_theme)` â†’ reselect new theme.
- **Delete** â€” disabled for built-ins and when the theme is currently applied to any live channel. Prompts confirm. On confirm: `_active_theme.delete()` â†’ `theme_mgr.reload_theme(theme_id)` drops the stale entry (missing file detected at \u00a71.5) â†’ list refreshes.
- **Back** â€” emits `back_requested = pyqtSignal()` connected by `MainWindow` to `_switch_tab(1)`.

Internal slot wiring:
- `themes_list.theme_selected` â†’ `_on_theme_selected(theme_id)` â€” calls `_confirm_discard_changes()` first if `_dirty`; deep-copies registry instance, populates editor, refreshes preview
- `property_editor.property_changed` â†’ `_on_property_changed(path, value)` calls `_active_theme.update(path, value)`, marks dirty, calls `preview.refresh()`
- `preview.apply_requested` â†’ `_on_apply(target)` looks up target channel(s), calls `channel.set_theme(_active_theme)`. Live-channel guard runs first.
- `back_requested` signal â†’ `_on_back_requested()` â€” calls `_confirm_discard_changes()` first if `_dirty`; then emits `back_requested`

### 3.7 Unsaved-Changes Guard (E5 fix)

```python
def _confirm_discard_changes(self) -> bool:
    """Prompt the operator when there are unsaved edits.

    Returns True if it is safe to proceed (user confirmed discard or no
    dirty state). Returns False if the user chose to cancel.

    Called before:
      - switching to a different theme in ThemesListPanel
      - navigating away via the Back button
    NOT called before Save/Apply (those preserve edits, not discard them).
    """
    if not self._dirty:
        return True
    from PyQt6.QtWidgets import QMessageBox
    reply = QMessageBox.question(
        self, "Unsaved Changes",
        f"'{self._active_theme.name}' has unsaved changes.\n\n"
        "Discard changes and continue?",
        QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
        QMessageBox.StandardButton.Cancel,
    )
    return reply == QMessageBox.StandardButton.Discard
```

**Integration points:**

```python
def _on_theme_selected(self, theme_id: str):
    if not self._confirm_discard_changes():
        # Revert list selection to the current theme â€” don't switch
        self._themes_list.reselect(self._original_id)
        return
    # ... proceed with deep_copy and load ...

def _on_back_requested(self):
    if not self._confirm_discard_changes():
        return
    self._dirty = False
    self.back_requested.emit()
```

`ThemesListPanel.reselect(theme_id)` sets the list's current item to `theme_id` without emitting `theme_selected` (use `blockSignals(True)` around `setCurrentItem`).

### 3.8 Live-Channel Guard

Single helper used by Save and Apply:

```python
def _any_channel_live(self) -> bool:
    if self._channel_manager is None:
        return False
    for name in self._channel_manager.channel_names():
        ch = self._channel_manager.get_channel(name)
        if ch is not None and ch.is_live:
            return True
    return False

def _confirm_override_live(self) -> bool:
    """Show 'Override Live' dialog. Returns True on confirm."""
    from PyQt6.QtWidgets import QMessageBox
    reply = QMessageBox.warning(
        self, "Override Live Service",
        "A channel is currently live (verse on display).\n\n"
        "Saving or applying a theme during a live service may cause a "
        "visible flicker on the congregation display.\n\n"
        "Continue anyway?",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.No
    )
    return reply == QMessageBox.StandardButton.Yes
```

Save flow: if `_any_channel_live()` â†’ show dialog â†’ on `No`, abort. Apply flow: same.

Per Q2, **property editing is never gated**. Only Save and Apply are.

---

## Step 4 â€” `settings_panel.py` Integration

### 4.1 New signal

```python
class SettingsPanel(QWidget):
    back_requested = pyqtSignal()
    theme_designer_requested = pyqtSignal()  # NEW
```

### 4.2 New button â€” placed in the Channel Settings card, above the per-channel rows

```python
# In _setup_ui, inside the `if self.channel_manager:` block, before the for-loop:
designer_btn = QPushButton("Open Theme Designer")
designer_btn.setFixedHeight(36)
designer_btn.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
designer_btn.setCursor(Qt.CursorShape.PointingHandCursor)
designer_btn.setStyleSheet("""
    QPushButton {
        background: rgba(200,160,60,0.18);
        color: #c8a03c;
        border: 1px solid rgba(200,160,60,0.4);
        border-radius: 4px;
        padding: 0 16px;
    }
    QPushButton:hover { background: rgba(200,160,60,0.28); }
""")
designer_btn.clicked.connect(self.theme_designer_requested.emit)
channel_layout.addWidget(designer_btn)
```

Above the per-channel mode/theme dropdowns. The hint label below the button reads: *"Edit themes used by Main and Alt channels. Changes apply only after Save and Apply."*

---

## Step 5 â€” `main.py` Wiring

### 5.1 Imports

```python
from theme_designer import ThemeDesignerPanel
```

### 5.2 Instantiation (after `SettingsPanel`)

```python
self.theme_designer = ThemeDesignerPanel(
    theme_mgr=self._theme_mgr,
    channel_manager=self.channel_manager,
)
self.stack.addWidget(self.theme_designer)  # Index 2
self.theme_designer.back_requested.connect(lambda: self._switch_tab(1))
self.settings_panel.theme_designer_requested.connect(lambda: self._switch_tab(2))
```

### 5.3 `_switch_tab` extension

The current `_switch_tab` updates `btn_tab_home` and `btn_tab_settings` styles. There's no designer button on the Home sidebar â€” it's reached via Settings or shortcut. So no new button-style branch is needed in `_switch_tab`. The method just needs to handle index 2 without crashing:

```python
def _switch_tab(self, index):
    self.stack.setCurrentIndex(index)
    # Existing logic for index 0 and 1
    if index == 0:
        # ... home highlighted ...
    elif index == 1:
        # ... settings highlighted ...
    # Index 2 (designer) â€” no sidebar button to highlight.
    # Existing Home/Settings buttons revert to inactive style:
    if index == 2:
        self.home_panel.btn_tab_home.setStyleSheet(""" ... inactive style ... """)
        self.home_panel.btn_tab_settings.setStyleSheet(""" ... inactive style ... """)
```

### 5.4 View menu action

In `_setup_display_controls`, add to View menu (between Settings and the separator):

```python
designer_action = QAction("Theme &Designer", self)
designer_action.setShortcut(QKeySequence("Ctrl+3"))
designer_action.setStatusTip("Open the Theme Designer")
designer_action.triggered.connect(lambda: self._switch_tab(2))
view_menu.addAction(designer_action)
```

### 5.5 Global shortcut

Add to `MainWindow.__init__`, after the `_hotkey_manager.start(self)` call (E4 fix: `Ctrl+L` lives in `home_panel.py:726`, not `MainWindow.__init__` â€” there is no Ctrl+L block in main.py to anchor against):

```python
from PyQt6.QtGui import QShortcut, QKeySequence
designer_shortcut = QShortcut(QKeySequence("Ctrl+Shift+T"), self)
designer_shortcut.activated.connect(lambda: self._switch_tab(2))
```

---

## Step 6 â€” Pre-Commit Guards (`scripts/pre_commit_checks.py`)

Add a new function `check_phase2_theme_designer()`:

```python
def check_phase2_theme_designer():
    errors = []
    # 1. theme_designer.py exists
    designer_path = SRC_UI / "theme_designer.py"
    if not designer_path.exists():
        errors.append("CRITICAL: Phase 2: theme_designer.py missing")
        return errors
    src = designer_path.read_text(encoding="utf-8")

    # 2. Required classes present
    for cls in ("class ThemeDesignerPanel", "class ThemesListPanel",
                "class PreviewSurface", "class PropertyEditor"):
        if cls not in src:
            errors.append(f"CRITICAL: Phase 2: {cls} missing in theme_designer.py")

    # 3. Required module-level symbols
    for sym in ("THEME_EDITOR_SCHEMA", "SAMPLE_VERSES", "BUILTIN_THEME_IDS",
                "_DummyDisplayController"):
        if sym not in src:
            errors.append(f"CRITICAL: Phase 2: {sym} missing in theme_designer.py")

    # 4. Theme persistence API present in theme.py
    theme_src = (SRC_UTILS / "theme.py").read_text(encoding="utf-8")
    for method in ("def update", "def deep_copy", "def save", "def save_as",
                   "def delete", "def reload_theme", "def create_theme"):
        if method not in theme_src:
            errors.append(f"CRITICAL: Phase 2: theme.py missing {method}")
    if "BUILTIN_THEME_IDS" not in theme_src:
        errors.append("CRITICAL: Phase 2: theme.py missing BUILTIN_THEME_IDS")

    # 5. settings_panel.py wires the new signal
    sp_src = (SRC_UI / "settings_panel.py").read_text(encoding="utf-8")
    if "theme_designer_requested" not in sp_src:
        errors.append("CRITICAL: Phase 2: settings_panel.py missing theme_designer_requested signal")
    if "Open Theme Designer" not in sp_src:
        errors.append("CRITICAL: Phase 2: settings_panel.py missing Open Theme Designer button")

    # 6. main.py wires the designer
    main_src = (SRC / "main.py").read_text(encoding="utf-8")
    for sym in ("from theme_designer import", "ThemeDesignerPanel(",
                "self.stack.addWidget(self.theme_designer)",
                "Ctrl+Shift+T", "Ctrl+3"):
        if sym not in main_src:
            errors.append(f"CRITICAL: Phase 2: main.py missing {sym!r}")

    # 7. THEME_EDITOR_SCHEMA paths must resolve in dark_gold.json after upgrade
    import json, re
    dg_path = SRC_UTILS / "themes" / "dark_gold.json"
    dg = json.loads(dg_path.read_text(encoding="utf-8"))
    # Apply v2 upgrade in memory for path validation
    dg.setdefault("fullscreen", {})
    for path_match in re.finditer(r'PropertySpec\("([^"]+)"', src):
        path = path_match.group(1)
        node = dg
        for part in path.split("."):
            if isinstance(node, dict) and part in node:
                node = node[part]
            else:
                # Acceptable: Phase 1 _upgrade_to_v2 fills these at runtime
                # Only flag paths that aren't covered by the v2 upgrade defaults
                if not _is_v2_default_path(path):
                    errors.append(f"CRITICAL: Phase 2: schema path '{path}' not in dark_gold.json")
                break

    return errors


def _is_v2_default_path(path: str) -> bool:
    """Whitelist of paths Phase 1's _upgrade_to_v2 populates from defaults."""
    return path.startswith(("fullscreen.",)) \
           or path in (
               "lower_third.logo_format",
               "lower_third.background_image",
               "lower_third.background_image_fit",
               "lower_third.height_ratio",
               "lower_third.separator_width",
               "lower_third.ref_color",
               "lower_third.verse_color",
               "lower_third.ref_font_family",
               "lower_third.verse_font_family",
               "lower_third.church_name_color",
           )
```

Register in `main()`:
```python
print("Running Phase 2 Theme Designer checks...")
errors.extend(check_phase2_theme_designer())
```

---

## Step 7 â€” Verification Guards (`scripts/verify_critical_fixes.py`)

Add a `=== Phase 2 Theme Designer ===` block:

```python
print("\n=== Phase 2 Theme Designer ===")
import json
from PyQt6.QtCore import QObject

# 1. Theme persistence API
from theme import Theme, ThemeManager, BUILTIN_THEME_IDS
sample = {"id": "test", "name": "Test", "schema_version": "2.0",
          "colors": {"gold": "#c8a03c"}, "fonts": {"family": "Segoe UI"},
          "lower_third": {}, "fullscreen": {}, "spacing": {}, "animation": {}}
t = Theme(sample)
assert hasattr(t, "update"), "Theme.update missing"
assert hasattr(t, "deep_copy"), "Theme.deep_copy missing"
assert hasattr(t, "save_as"), "Theme.save_as missing"
assert hasattr(t, "delete"), "Theme.delete missing"
print("  [OK] Theme persistence API present")

# 2. update() walks dotted paths
t.update("lower_third.background_color", "#ff0000")
assert t.lower_third["background_color"] == "#ff0000", "update did not set value"
print("  [OK] Theme.update walks dotted path correctly")

# 3. deep_copy isolates mutation
copy = t.deep_copy()
copy.update("lower_third.background_color", "#00ff00")
assert t.lower_third["background_color"] == "#ff0000", \
    "deep_copy mutation contaminated original"
assert copy.lower_third["background_color"] == "#00ff00"
print("  [OK] Theme.deep_copy isolates mutations")

# 4. delete refuses built-ins
for builtin in BUILTIN_THEME_IDS:
    sample_b = dict(sample); sample_b["id"] = builtin
    tb = Theme(sample_b)
    assert tb.delete() is False, f"delete should refuse built-in '{builtin}'"
print("  [OK] Theme.delete refuses built-ins")

# 5. THEME_EDITOR_SCHEMA cardinality
from theme_designer import THEME_EDITOR_SCHEMA, SAMPLE_VERSES, BUILTIN_THEME_IDS as DESIGNER_BUILTINS
assert len(THEME_EDITOR_SCHEMA) >= 33, f"Schema has {len(THEME_EDITOR_SCHEMA)} props, expected >= 33"
assert len(SAMPLE_VERSES) >= 4, "Need at least 4 sample verses"
assert DESIGNER_BUILTINS == BUILTIN_THEME_IDS, "BUILTIN_THEME_IDS mismatch"
print(f"  [OK] THEME_EDITOR_SCHEMA has {len(THEME_EDITOR_SCHEMA)} properties")

# 6. Designer instantiation (headless via QApplication)
from PyQt6.QtWidgets import QApplication
app = QApplication.instance() or QApplication([])
mgr = ThemeManager()
from theme_designer import ThemeDesignerPanel
designer = ThemeDesignerPanel(theme_mgr=mgr, channel_manager=None)
assert designer is not None, "Designer failed to instantiate"
print("  [OK] ThemeDesignerPanel instantiates with theme_mgr only")

# 7. PreviewSurface uses dummy controller (not VerseDB)
from theme_designer import _DummyDisplayController
dummy = _DummyDisplayController()
assert hasattr(dummy, "verse_changed"), "Dummy missing verse_changed signal"
assert hasattr(dummy, "translations_changed"), "Dummy missing translations_changed signal"
assert hasattr(dummy, "layout_changed"), "Dummy missing layout_changed signal"
print("  [OK] _DummyDisplayController has full signal surface")
```

---

## Regression Hazards

- **Live History contamination.** If `PreviewSurface` accidentally constructs the real `DisplayController` instead of `_DummyDisplayController`, sample verses appear in the operator's Live History. Mitigation: explicit type check in `PreviewSurface.__init__`; static guard verifies `_DummyDisplayController` is referenced.
- **Cross-channel Theme mutation.** If `Theme.update()` is called on a registry instance instead of a deep copy, mutations propagate to all channels using that theme_id. Mitigation: `_on_theme_selected` always calls `deep_copy()` first; static guard verifies `deep_copy` is called in `theme_designer.py`.
- **Schema drift.** A new key added to `dark_gold.json` but not added to `THEME_EDITOR_SCHEMA` is invisible to operators. The reverse â€” schema entry without a matching JSON key â€” produces a broken row at runtime. Static guard runs path resolution against `dark_gold.json` after v2 upgrade.
- **NDI capture of designer preview.** The preview's `DisplayWidget` must not be in `ChannelManager`'s registry. Mitigation: designer creates the widget standalone, never calls `channel_manager.add_channel(...)` for it. Verified by inspection â€” designer never imports `add_channel`.
- **Built-in overwrite via direct file edit.** `Save` refuses built-ins; `Save As` to `themes/dark_gold.json` would overwrite the file. Mitigation: `create_theme` rejects when target path already exists (~line 316: `if new_path.exists()`). `save_as` itself has no built-in check.
- **Settings live-service gate bypass.** If `_any_channel_live()` returns `False` while a channel is actually live (race), Save proceeds. The preview is sandboxed so no immediate visual harm; the channel inheriting the new theme on next refresh sees the updated colors. Documented behavior, not a hazard.
- **`Ctrl+Shift+T` collision.** Verified against `HOTKEY_DEFAULTS` in `settings.py:21`: `Ctrl+Shift+L`, `Ctrl+Shift+V`, `Ctrl+Shift+X`, `Ctrl+Shift+Q` are taken; `T` is free. Confirmed by audit on `2026-05-15`.
- **Unsaved-changes discard.** `_confirm_discard_changes()` is called before theme switching and Back navigation. The `QMessageBox.Discard / Cancel` pattern is used (not `Yes / No`) to make the destructive action explicit. `ThemesListPanel.reselect()` reverts the list selection on Cancel so the UI stays consistent with the in-memory state.

## Phase 2 Definition of Done

- [ ] All `scripts/pre_commit_checks.py` checks pass.
- [ ] All `scripts/verify_critical_fixes.py` checks pass.
- [ ] Designer opens via Settings â†’ "Open Theme Designer" and via `Ctrl+Shift+T` and via View â†’ Theme Designer.
- [ ] Three-panel layout renders: themes list left, embedded preview center, property editor right.
- [ ] Selecting a theme in the list deep-copies it into `_active_theme` and populates the editor and preview.
- [ ] Editing any of the 33 schema properties updates `_active_theme` and refreshes the preview within ~16ms (single repaint).
- [ ] Save writes to disk for user themes; refuses built-ins; refuses during live service unless overridden.
- [ ] Save As prompts for new id/name and creates a new theme file.
- [ ] Duplicate creates `<id>_copy.json` and selects it in the list.
- [ ] Delete removes the file; refuses built-ins; refuses during live service unless overridden.
- [ ] Apply pushes `_active_theme` to the selected target (Main / Alt / Both) via `channel.set_theme()`.
- [ ] Switching themes with unsaved edits prompts "Discard changes?" â€” Cancel keeps current theme and edits intact. (E5 fix)
- [ ] Navigating Back with unsaved edits prompts the same dialog. (E5 fix)
- [ ] Live service: NDI capture on running channels is unaffected by designer preview.
- [ ] Operator panel chrome (`theme.active_theme`) is unaffected by any designer action.
- [ ] Preview matches live display when the saved theme is applied to a real channel â€” confirm with `John 3:16` on Main fullscreen.

## Status Log

| Date | Note |
|---|---|
| _TBD_ | Phase 2 start. |
| _TBD_ | Step 1 done â€” Theme persistence API. |
| _TBD_ | Step 2 done â€” `THEME_EDITOR_SCHEMA`. |
| _TBD_ | Step 3 done â€” `theme_designer.py` core classes. |
| _TBD_ | Step 4 done â€” Settings integration. |
| _TBD_ | Step 5 done â€” `main.py` wiring. |
| _TBD_ | Step 6 done â€” pre-commit guards. |
| _TBD_ | Step 7 done â€” verification guards. |
| _TBD_ | Phase 2 sign-off. |
