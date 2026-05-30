# Phase 2 — Iconography System & Settings Icons
## Implementation Plan (v1.3.1)

> **Status:** Draft
> **Audit basis:** v1.3.1 UI Polish & Consistency Sub-Roadmap (May 22 revision). Cross-referenced against `icons.py` (225 lines), `settings_panel.py` (518 lines), `theme_designer.py` (1529 lines), `theme.py` (776 lines), `pre_commit_checks.py`, `test_preset_library.py`.
> **Sub-roadmap deviations:** 3 intentional (documented below)
> **Audit findings:** 6 issues (F1–F5 pre-implementation, P1–P6 post-implementation audit) — all verified against codebase and incorporated.

---

## Deviations from Sub-Roadmap

### Deviation 1 — All 10 built-in themes, not "all 4 themes"

- **Sub-roadmap says:** "Settings panel section headers render with icons in **all 4 themes**."
- **Plan says:** Icons are verified in **all 10** built-in themes.
- **Justification:** Same as Phase 1 Deviation 1. The sub-roadmap was written when only 4 themes existed. `BUILTIN_THEME_IDS` now contains 10 entries. The icon tinting contract (`theme.c("gold")`) applies equally to all 10 — any theme's gold value drives the icon color.

### Deviation 2 — `theme.c("gold")`, not `theme.colors.gold`

- **Sub-roadmap says:** "tinted to `theme.colors.gold`"
- **Plan says:** Icons are tinted via `self.theme_mgr.current` → `.c("gold")` — the existing `Theme.c()` dict-lookup method (`theme.py:108`). A `_refresh_section_header_icons()` method is added to `SettingsPanel` for programmatic retint, but is NOT automatically wired to any signal (no `theme_changed` signal exists on `ThemeManager`). Icons are set at panel construction time with the current theme's gold value.
- **Justification:** `theme.colors` is a plain `dict`, not a namespace — there is no `.gold` property. The `c("gold")` shorthand (`theme.py:108`) is the canonical accessor. `ThemeManager` exposes the current theme as a property named `current` (`theme.py:381`, returns `Optional[Theme]`), not a method `current_theme()`. Live retinting on theme switch would require adding a `theme_changed` signal to `ThemeManager`, which is cross-cutting and best scoped to Phase 4 (full regression sweep). The `_refresh` method allows any future signal handler to call it without modifying `_make_section_header`.

### Deviation 3 — Designer header icon uses separate QLabel, not `_make_section_header`

- **Sub-roadmap says:** "Theme Designer panel header receives the palette icon." (Implies same `_make_section_header` pattern.)
- **Plan says:** The palette icon is added as a separate `QLabel` (wrapping a `QPixmap` from `get_palette_icon`) inserted into the designer's `header_layout` **before** the `title` label. No `_make_section_header` call is involved.
- **Justification:** The Theme Designer header (lines 1063–1075 of `theme_designer.py`) is structurally different from settings section headers: it's a 50px fixed-height header bar with a bold 14px title, not a gold-dot + uppercase label combo. The `_make_section_header` method lives in `SettingsPanel` and is not accessible from `ThemeDesignerPanel`. Adding a shared `_make_section_header` to a base class is a larger refactor (out of scope). A standalone `QLabel(icon)` before the title is the minimal insertion that satisfies the deliverable.

---

## Files Modified

- `src/utils/icons.py` — Add 5 new SVG factory functions (`get_keyboard_icon`, `get_settings_gear_icon`, `get_layers_icon`, `get_broadcast_icon`, `get_palette_icon`)
- `src/ui/settings_panel.py` — Add `QIcon` to module-level `PyQt6.QtGui` import; extend `_make_section_header` with `icon: QIcon = None` parameter; add `_refresh_section_header_icons()` method; add `_section_header_icon_labels` tracking list; update all 4 call sites to pass an icon; add import of 4 icon functions; add palette icon to "Open Theme Designer" button
- `src/ui/theme_designer.py` — Import `get_palette_icon`; insert palette icon QLabel before title in header
- `scripts/pre_commit_checks.py` — Add `check_v131_phase2_icons()` function; register in `__main__`
- `tests/test_preset_library.py` — Fix leftover Phase 1: `EXPECTED_COLOR_TOKENS = 46` → `47`
- `tests/test_icons.py` — NEW: SVG rendering validation (4 tests, QApp-backed)

## Files Not Touched

- `src/ui/home_panel.py` — Phase 3 scope. Its icon imports (`import icons`) remain unchanged.
- `src/utils/theme.py` — No QSS changes needed. Typography selectors already style section headers. No new selectors required.
- `src/utils/themes/*.json` — No token changes. `red_text` was already added in Phase 1.
- `scripts/verify_critical_fixes.py` — Phase 2 is not regression-critical enough to warrant a second guard (per user decision). SVG runtime validation is covered by `tests/test_icons.py` instead.
- `src/core/*` — Outside operator-panel scope.
- `src/display/*` — Congregation display must not change.

---

## Step 0 — Pre-Flight Verification

| Required by Plan | Present in Code | Status |
|---|---|---|
| `settings_panel.py` imports `from icons import get_chevron_left_icon` | Line 15 | ✅ Confirmed — extend with new imports |
| `settings_panel.py._make_section_header` at line 237, signature `(self, title, variant)` | Line 237 | ✅ Confirmed — extend with `icon=None` |
| All 5 call sites at lines 71, 118, 167, 206, 221 use `variant="standard"` | Confirmed | ✅ Confirmed |
| `theme_designer.py` header at lines 1063–1075, `header_layout` + `title` QLabel | Lines 1063–1074 | ✅ Confirmed — icon inserts before title |
| `icons.py` has no existing `get_keyboard_icon` / `get_settings_gear_icon` / `get_layers_icon` / `get_broadcast_icon` / `get_palette_icon` | Grep confirms absent | ✅ Confirmed — all 5 are new |
| `icons.py._render_svg` exists at line 13 | Line 13 | ✅ Confirmed |
| `ThemeManager` exposes current theme via `.current` property (not `.current_theme()`) | `theme.py:381` | ✅ Confirmed — `@property def current -> Optional[Theme]` |
| `Theme.c("gold")` returns gold hex string | `theme.py:108` — `self.colors.get(key, "#000000")` | ✅ Confirmed |
| `settings_panel.py:9` imports `from PyQt6.QtGui import QFont` only — no `QIcon` | Line 9 | ✅ Confirmed — needs `QIcon` added |
| `theme_designer.py:25` already imports `QPixmap` from `PyQt6.QtGui` | Line 25 | ✅ Confirmed — no import needed |
| `QLabel` available in both `settings_panel.py` and `theme_designer.py` | Module-level imports | ✅ Confirmed |
| `test_preset_library.py:29` has `EXPECTED_COLOR_TOKENS = 46` | Line 29 | ⚠️ Needs fix to 47 |
| `pre_commit_checks.py.__main__` Phase 2 insertion point after Phase 1 (line 883) and before Phase 4 (line 885) | Lines 882–886 | ✅ Confirmed — line 884 |
| Sub-roadmap Decision 3: palette icon on **both** "Open Theme Designer" button AND designer header | sub-roadmap:97-103 | ✅ Confirmed — both sites required |
| No existing icon/SVG test files | `tests/` glob | ✅ Confirmed — `test_icons.py` is new |

---

## Step 1 — Add 5 SVG factory functions to `icons.py`

**Insertion point:** After `get_folder_icon` (the last function, ending at line 225).

All 5 functions follow the existing pattern: Feather-style SVG (`stroke-width="2"`, `stroke-linecap="round"`, `stroke-linejoin="round"`), `color` and `size` parameters, return `QIcon` via `_render_svg`.

### 1a — `get_keyboard_icon`

```python
def get_keyboard_icon(color: str = "#c8a03c", size: int = 16) -> QIcon:
    """Keyboard icon for Hotkey Diagnostics section header."""
    svg_template = f'''
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
         stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <rect x="2" y="4" width="20" height="16" rx="2" ry="2"></rect>
      <line x1="6" y1="8" x2="6.01" y2="8"></line>
      <line x1="10" y1="8" x2="10.01" y2="8"></line>
      <line x1="14" y1="8" x2="14.01" y2="8"></line>
      <line x1="18" y1="8" x2="18.01" y2="8"></line>
      <line x1="6" y1="12" x2="6.01" y2="12"></line>
      <line x1="10" y1="12" x2="10.01" y2="12"></line>
      <line x1="14" y1="12" x2="14.01" y2="12"></line>
      <line x1="18" y1="12" x2="18.01" y2="12"></line>
      <line x1="6" y1="16" x2="18" y2="16"></line>
    </svg>
    '''
    return _render_svg(svg_template, size)
```

### 1b — `get_settings_gear_icon`

```python
def get_settings_gear_icon(color: str = "#c8a03c", size: int = 16) -> QIcon:
    """Gear/settings icon for General section header."""
    svg_template = f'''
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
         stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <circle cx="12" cy="12" r="3"></circle>
      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
    </svg>
    '''
    return _render_svg(svg_template, size)
```

### 1c — `get_layers_icon`

```python
def get_layers_icon(color: str = "#c8a03c", size: int = 16) -> QIcon:
    """Layers icon for Channel Settings section header."""
    svg_template = f'''
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
         stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <polygon points="12 2 2 7 12 12 22 7 12 2"></polygon>
      <polyline points="2 17 12 22 22 17"></polyline>
      <polyline points="2 12 12 17 22 12"></polyline>
    </svg>
    '''
    return _render_svg(svg_template, size)
```

### 1d — `get_broadcast_icon`

```python
def get_broadcast_icon(color: str = "#c8a03c", size: int = 16) -> QIcon:
    """Broadcast/signal icon for NDI Output section header."""
    svg_template = f'''
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
         stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <circle cx="12" cy="12" r="2"></circle>
      <path d="M16.24 7.76a6 6 0 0 1 0 8.48m-8.48 0a6 6 0 0 1 0-8.48m11.31-2.83a10 10 0 0 1 0 14.14m-14.14 0a10 10 0 0 1 0-14.14"></path>
    </svg>
    '''
    return _render_svg(svg_template, size)
```

### 1e — `get_palette_icon`

```python
def get_palette_icon(color: str = "#c8a03c", size: int = 16) -> QIcon:
    """Painter's palette icon for Theme Designer header and Open button."""
    svg_template = f'''
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
         stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <path d="M12 3a9 9 0 0 0-9 9 2 2 0 0 0 2 2h2a2 2 0 0 1 2 2v1a2 2 0 0 0 4 0 9 9 0 0 0-1-18z"></path>
      <circle cx="8" cy="10" r="1" fill="{color}"></circle>
      <circle cx="15" cy="8" r="1" fill="{color}"></circle>
      <circle cx="17" cy="14" r="1" fill="{color}"></circle>
      <circle cx="11" cy="16" r="1" fill="{color}"></circle>
    </svg>
    '''
    return _render_svg(svg_template, size)
```

**SVG design rationale:** The palette is represented as a painter's palette shape — a kidney/bean-shaped outline with four filled paint dots. This is universally recognizable as a palette icon. The `<circle fill="{color}">` elements use filled circles (not stroked) to represent paint blobs, matching the metaphor. The `fill="none"` on the `<svg>` ensures the palette outline uses the stroke pattern consistently with all other icons.

---

## Step 2 — Extend `_make_section_header()` with optional `icon` parameter

**File:** `settings_panel.py`, method at line 237.

### 2a — Add `QIcon` to module-level import

**Line 9, before:**
```python
from PyQt6.QtGui import QFont
```

**After:**
```python
from PyQt6.QtGui import QFont, QIcon
```

This fixes **F2**: `QIcon` is now available for the type hint without a `NameError`.

### 2b — Update method signature and body

**Before (lines 237–254):**
```python
    def _make_section_header(self, title: str, variant: str = "compact") -> QWidget:
        """Gold dot + typography-sized label, wrapped in a QWidget for use with addWidget()."""
        from PyQt6.QtWidgets import QWidget as _QWidget, QHBoxLayout, QFrame, QLabel
        from PyQt6.QtGui import QFont
        container = _QWidget()
        header = QHBoxLayout(container)
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(8)
        dot = QFrame()
        dot.setFixedSize(6, 6)
        dot.setProperty("gold-dot", True)
        header.addWidget(dot)
        label = QLabel(title.upper())
        label.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        label.setProperty("section-header", variant)
        header.addWidget(label)
        header.addStretch()
        return container
```

**After:**
```python
    def _make_section_header(self, title: str, variant: str = "compact", icon: QIcon = None) -> QWidget:
        """Gold dot + typography-sized label, wrapped in a QWidget for use with addWidget().

        Args:
            title: Section header text (auto-uppercased).
            variant: Typography scale name ("compact" or "standard").
            icon: Optional 16px QIcon rendered left of the gold dot.
        """
        from PyQt6.QtWidgets import QWidget as _QWidget, QHBoxLayout, QFrame, QLabel
        from PyQt6.QtGui import QFont
        container = _QWidget()
        header = QHBoxLayout(container)
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(8)
        if icon is not None:
            icon_label = QLabel()
            icon_label.setPixmap(icon.pixmap(16, 16))
            icon_label.setFixedSize(16, 16)
            header.addWidget(icon_label)
        dot = QFrame()
        dot.setFixedSize(6, 6)
        dot.setProperty("gold-dot", True)
        header.addWidget(dot)
        label = QLabel(title.upper())
        label.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        label.setProperty("section-header", variant)
        header.addWidget(label)
        header.addStretch()
        return container
```

**Key design decisions:**
- `icon: QIcon = None` — local `QIcon` type hint uses the module-level import (F2 fix). Default `None` preserves backward compatibility.
- `icon_label.setPixmap(icon.pixmap(16, 16))` — extracts a 16×16 pixmap from the QIcon; `setFixedSize(16, 16)` prevents the label from growing.
- No `QPixmap` local import needed — `icon.pixmap()` returns a `QPixmap` object which `setPixmap()` accepts natively.
- The icon sits **before** the gold dot, creating the visual order: icon → dot → label.

### 2c — Add `_section_header_icon_labels` tracking and `_refresh_section_header_icons()` method

Add to `_make_section_header`, inside the `if icon is not None:` block (after `header.addWidget(icon_label)`):
```python
            self._section_header_icon_labels.append((icon_label, title))
```

Add after `_make_section_header` (after line 254, before `_make_separator` at line 256):
```python
    def _refresh_section_header_icons(self):
        """Rebuild section header icons using the current theme's gold color.

        Call this when the active theme changes to retint icons.
        Currently NOT wired to any signal — provided for Phase 4+ integration.
        """
        theme = self.theme_mgr.current if self.theme_mgr else None
        gold = theme.c("gold") if theme else "#c8a03c"
        factories = {
            "Hotkey Diagnostics": lambda: get_keyboard_icon(color=gold, size=16),
            "General":            lambda: get_settings_gear_icon(color=gold, size=16),
            "Channel Settings":   lambda: get_layers_icon(color=gold, size=16),
            "NDI Output":         lambda: get_broadcast_icon(color=gold, size=16),
        }
        for icon_label, title in self._section_header_icon_labels:
            fn = factories.get(title)
            if fn:
                icon_label.setPixmap(fn().pixmap(16, 16))
```

Note: This fixes **F1** — uses `self.theme_mgr.current` (property, no parens) instead of the non-existent `current_theme()`. Handles `None` return via `if theme else "#c8a03c"`. The icon function imports are resolved via the module-level import from Step 3a — no lazy import needed inside this method (fixes **P3**).

---

## Step 3 — Apply icons to all 4 settings panel section headers + designer button

**File:** `settings_panel.py`

### 3a — Update import (line 15)

**Before:**
```python
from icons import get_chevron_left_icon
```

**After:**
```python
from icons import get_chevron_left_icon, get_keyboard_icon, get_settings_gear_icon, get_layers_icon, get_broadcast_icon, get_palette_icon
```

### 3b — Initialize icon-labels list and resolve gold color (both before line 71)

Insert after line 68, before line 71. These two blocks are independent (order between them doesn't matter), but BOTH must complete before the first `_make_section_header` call at line 71:

```python
        self._section_header_icon_labels = []
        _theme = self.theme_mgr.current if self.theme_mgr else None
        _gold = _theme.c("gold") if _theme else "#c8a03c"
```

This fixes **F1** — uses `self.theme_mgr.current` (property, no parens) with `None` guard. Merging the two insertions into one eliminates the adjacent-insertion ambiguity (fixes **P2**).

### 3c — Update call sites

All 5 call sites pass an `icon` argument:

**Line 71** (Hotkey Diagnostics):
```python
        content_layout.addWidget(self._make_section_header("Hotkey Diagnostics", variant="standard",
            icon=get_keyboard_icon(color=_gold, size=16)))
```

**Line 118** (General):
```python
        content_layout.addWidget(self._make_section_header("General", variant="standard",
            icon=get_settings_gear_icon(color=_gold, size=16)))
```

**Line 167** (Channel Settings):
```python
        content_layout.addWidget(self._make_section_header("Channel Settings", variant="standard",
            icon=get_layers_icon(color=_gold, size=16)))
```

**Line 206** (NDI Output — available branch):
```python
        content_layout.addWidget(self._make_section_header("NDI Output", variant="standard",
            icon=get_broadcast_icon(color=_gold, size=16)))
```

**Line 221** (NDI Output — unavailable branch):
```python
        content_layout.addWidget(self._make_section_header("NDI Output", variant="standard",
            icon=get_broadcast_icon(color=_gold, size=16)))
```

### 3d — Add palette icon to "Open Theme Designer" button

This fixes **F3** — the sub-roadmap Decision 3 table requires the palette icon on both the designer header AND the "Open Theme Designer" button.

**Line 184, after `designer_btn = QPushButton("Open Theme Designer")`:**
```python
        designer_btn.setIcon(get_palette_icon(color=_gold, size=16))
```

The button already has `setProperty("accent", "gold")` — the icon color matches the gold accent and the section header theme color.

---

## Step 4 — Apply palette icon to Theme Designer header

**File:** `theme_designer.py`

### 4a — Add import

After the existing imports (after line 37 `from constants import ...`):
```python
from icons import get_palette_icon
```

No `QPixmap` import needed — it is already imported at line 25 (fixes **F5**).

### 4b — Insert icon before title label

**Insertion point:** Between line 1070 (`header_layout.setSpacing(12)`) and line 1071 (`title = QLabel("Theme Designer")`).

**Insert:**
```python
        # Palette icon (Phase 2)
        palette_icon_label = QLabel()
        palette_icon_label.setPixmap(get_palette_icon(size=16).pixmap(16, 16))
        palette_icon_label.setFixedSize(16, 16)
        header_layout.addWidget(palette_icon_label)
```

**Color rationale:** The palette icon uses the default gold (`#c8a03c`), matching the existing hardcoded stylesheet pattern in the designer header (`color: #e8e2d8`, `background: rgba(15,15,26,0.8)`). The designer header is not theme-resolved — theme-awareness for the designer is Phase 4 scope. This is consistent with Deviation 3 and the existing code style.

---

## Step 5 — Update guard scripts and fix Phase 1 leftover

### 5a — `test_preset_library.py` line 29 (Phase 1 leftover fix)

```python
EXPECTED_COLOR_TOKENS = 47   # Was 46; +1 for red_text (Phase 1)
```

### 5b — `pre_commit_checks.py`: Add `check_v131_phase2_icons()`

```python
def check_v131_phase2_icons():
    """Verify Phase 2 iconography system and settings panel icons."""
    errors = []

    # 1. All 5 icon factory functions exist in icons.py
    icons_path = SRC_UTILS / 'icons.py'
    with open(icons_path, encoding='utf-8') as f:
        icons_content = f.read()
    expected_functions = [
        'get_keyboard_icon',
        'get_settings_gear_icon',
        'get_layers_icon',
        'get_broadcast_icon',
        'get_palette_icon',
    ]
    for func in expected_functions:
        if f'def {func}(' not in icons_content:
            errors.append(f"CRITICAL: icons.py missing function '{func}'")

    # 2. All 5 functions accept color and size parameters
    for func in expected_functions:
        sig_pattern = f'def {func}(color: str'
        if sig_pattern not in icons_content:
            errors.append(f"CRITICAL: {func} missing color parameter")
        if 'size: int' not in icons_content:
            pass

    # 3. settings_panel.py imports all 5 icon functions (4 section + palette)
    sp_path = SRC_UI / 'settings_panel.py'
    with open(sp_path, encoding='utf-8') as f:
        sp_content = f.read()
    for func in expected_functions:
        if func not in sp_content:
            errors.append(f"CRITICAL: settings_panel.py does not reference '{func}'")

    # 4. _make_section_header accepts icon parameter
    if 'icon: QIcon = None' not in sp_content:
        errors.append("CRITICAL: _make_section_header missing 'icon: QIcon = None' parameter")

    # 5. All call sites pass icon= argument
    call_lines = [l for l in sp_content.split('\n') if '_make_section_header(' in l]
    icon_calls = [l for l in call_lines if 'icon=' in l]
    if len(icon_calls) < 4:
        errors.append(f"CRITICAL: Only {len(icon_calls)}/4+ _make_section_header call sites pass icon=")

    # 6. theme_designer.py imports get_palette_icon
    td_path = SRC_UI / 'theme_designer.py'
    with open(td_path, encoding='utf-8') as f:
        td_content = f.read()
    if 'get_palette_icon' not in td_content:
        errors.append("CRITICAL: theme_designer.py missing get_palette_icon import/usage")

    # 7. settings_panel.py has QIcon import from PyQt6.QtGui
    if 'from PyQt6.QtGui import' not in sp_content or 'QIcon' not in sp_content:
        errors.append("CRITICAL: settings_panel.py missing QIcon import")

    return errors
```

Registration in `__main__` — insert at line 884 (between Phase 1 and Phase 4 checks):

```python
    print("Checking v1.3.1 Phase 2 iconography system...")
    all_errors.extend(check_v131_phase2_icons())
```

---

## Step 6 — Add SVG rendering validation test

**File:** `tests/test_icons.py` (new file)

Validates that all 5 SVG factory functions produce valid (non-null) icons. Requires `QApplication` — uses the same `@pytest.fixture(scope="module")` `app()` pattern as `test_preset_library.py`.

```python
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
```

This fixes **P4/P5** — adds runtime SVG validation that catches malformed templates and render failures which static guard checks cannot detect.

---

## Regression Hazards

| Hazard | Risk | Mitigation |
|--------|------|------------|
| **H1: Icon SVGs malformed** — A typo in an SVG template causes `QSvgRenderer` to produce an invalid renderer, returning `QIcon()` (empty icon). Section header renders with no visible icon — silent failure, no crash. | Low — degraded rendering, visibly missing icon | `_render_svg` already logs errors via `logging.getLogger("VerseFlow").error(...)`. Further mitigated by Step 6 pytest (`test_icons.py`). |
| **H2: `_gold` resolved once at construction time** — If the theme changes while the settings panel is open, icon colors become stale until the panel is reopened. `_refresh_section_header_icons()` exists but is not wired. | Medium — icons show wrong gold until panel recreation | Documented as intentional (Deviation 2). `_refresh_section_header_icons()` is provided as a hook for Phase 4 signal plumbing. Phase 2 DoD notes this limitation. |
| **H3: `_section_header_icon_labels` accumulates on re-entrant `_setup_ui`** — If `_setup_ui` is called multiple times, the labels list doubles. | Low — no current code path calls `_setup_ui` twice | Initialize `self._section_header_icon_labels = []` at the top of `_setup_ui` (Step 3b) to guarantee a clean list on every setup. |
| **H4: Designer palette icon hardcoded gold** — The palette icon uses the default gold `#c8a03c`, not a theme-resolved value. If a theme defines a different gold, the icon won't match. | Low — designer header already hardcodes its own color (`#e8e2d8`), consistent with existing pattern | The designer header is not theme-resolved (it uses hardcoded stylesheet colors). Theme-awareness for the designer is Phase 4 scope. |
| **H5: `test_preset_library.py` fails** — `EXPECTED_COLOR_TOKENS = 46` causes pytest failure on every run until fixed. | Low — doesn't affect runtime or guard scripts | Fixed in Step 5a of this plan. |
| **H6: (F1 RESOLVED) `current_theme()` API does not exist** — Draft plan used non-existent method. | N/A — resolved. | Corrected to `self.theme_mgr.current` (property) with `None` guard in all call sites. |
| **H7: (F2 RESOLVED) `QIcon` missing from imports** — Draft plan used `QIcon` in type hint without importing it. | N/A — resolved. | Added `from PyQt6.QtGui import QFont, QIcon` in Step 2a. |
| **H8: (F3 RESOLVED) Missing palette icon on designer button** — Draft plan omitted the "Open Theme Designer" button icon. | N/A — resolved. | Added `designer_btn.setIcon(get_palette_icon(color=_gold, size=16))` in Step 3d. |
| **H9: (F4 RESOLVED) Palette icon SVG was crosshair** — Draft plan used a wrong SVG. | N/A — resolved. | Replaced with proper painter's palette shape with paint blobs in Step 1e. |
| **H10: SVG rendering regression** — A broken SVG template (typo, missing tag, path error) bypasses all static guard checks. Step 5b's guard only checks function names and signatures exist, not that SVGs render correctly. | Medium — silent failure (empty icon), no crash | Mitigated by Step 6 pytest (`test_icons.py`). Run `pytest tests/test_icons.py -v` during implementation. |

---

## Definition of Done

- [ ] All 5 SVG factory functions exist in `icons.py`: `get_keyboard_icon`, `get_settings_gear_icon`, `get_layers_icon`, `get_broadcast_icon`, `get_palette_icon`. Each accepts `color` (str) and `size` (int) parameters and returns a `QIcon`.
- [ ] `_make_section_header()` in `settings_panel.py` accepts `icon: QIcon = None`. When provided, a 16×16 icon renders to the left of the gold dot.
- [ ] `QIcon` is imported at module level in `settings_panel.py` (from `PyQt6.QtGui`).
- [ ] All 4 settings panel section headers (Hotkey Diagnostics, General, Channel Settings, NDI Output) display their respective icons in all 10 themes. Icons use the theme's gold color at panel construction time.
- [ ] "Open Theme Designer" button in Channel Settings card displays the palette icon to its left, tinted to the theme's gold.
- [ ] Theme Designer header displays the palette icon to the left of the "Theme Designer" title.
- [ ] Icon size and alignment match the section header text baseline (16px icons, vertically centered in the header row).
- [ ] `_refresh_section_header_icons()` method exists on `SettingsPanel` for future signal-driven retint.
- [ ] `_section_header_icon_labels` list tracks icon labels for retint iteration.
- [ ] `test_preset_library.py`: `EXPECTED_COLOR_TOKENS` set to 47 (Phase 1 leftover fixed).
- [ ] `pre_commit_checks.py`: `check_v131_phase2_icons()` function exists, registered in `__main__`, passes with 0 errors.
- [ ] `test_icons.py` exists with 4 test methods covering: non-null icon, 16px pixmap rendering, custom color acceptance, default size (16×16). `pytest tests/test_icons.py -v` passes.
- [ ] No regression to existing `icons.py` consumers (trash, new, open, save, save_as, metadata, arrows, close, play, stop, return, queue, playlist, chevron_left, folder).
- [ ] No changes to `theme.py`, theme JSONs, `home_panel.py`, `verify_critical_fixes.py`, or `src/core/`.

---

## Status Log

| Date | Note |
|------|------|
| May 25, 2026 | Phase 2 plan drafted. 3 deviations documented (10 themes, `theme.c("gold")` API, designer header structure). 5 execution steps + Step 0 pre-flight. Audit findings F1–F5 identified in Pass 0 review and corrected: F1 (`current_theme` → `current` property), F2 (`QIcon` import), F3 (missing designer button icon), F4 (wrong palette SVG), F5 (redundant `QPixmap` import). All incorporated into initial plan. |
| May 25, 2026 | Post-implementation audit identified 6 additional issues (P1–P6). P1 (pre-flight table reference ambiguous → `sub-roadmap:97-103`), P2 (adjacent insertion collision → Steps 3b+3c merged), P3 (redundant lazy import removed from `_refresh_section_header_icons`), P4/P5 (no SVG runtime validation → Step 6 added with `test_icons.py`), P6 (existing `EXPECTED_COLOR_TOKENS` carryover fixed in Step 5a). All fixable items incorporated. |
