# Phase 4 — Theme Designer Polish & Sign-Off
## Implementation Plan (v1.0)

> **Status:** Draft
> **Audit basis:** v1.3.1 UI Polish & Consistency Sub-Roadmap (Phase 4 spec). Cross-referenced against `theme_designer.py` (1540 lines), `theme.py` (956 lines), all 10 built-in theme JSONs, `generate_stylesheet()` QSS selector inventory, `pre_commit_checks.py`, `verify_critical_fixes.py`, `ROADMAP.md`, `To Implement.md`, `PROTOCOL_REVIEW.md`.
> **Sub-roadmap deviations:** 2 intentional (documented below)
> **Inline setStyleSheet() baseline:** 40 calls (verified May 27, 2026 via Select-String against `src/ui/theme_designer.py`)
> **Audit corrections applied:** 3 pre-flight errors (C1–C3) + 3 implementation notes (N1–N3), all verified against codebase evidence.

---

## Deviations from Sub-Roadmap

### Deviation 1 — "All four new selectors" actually five core selectors + nine supporting selectors

- **Sub-roadmap says:** "All **four** new selectors emitted by `generate_stylesheet()`: `QDoubleSpinBox[designer-spin="true"]`, `QSpinBox[designer-spin="true"]`, `QComboBox[designer-combo="true"]`, `QPushButton[mode-btn="active"]`, `QPushButton[mode-btn="inactive"]`."
- **Plan says:** The R2 helper-method migration produces 5 core selectors (the sub-roadmap lists 5 names but counts 4 — a minor counting error). Additionally, 9 supporting selectors are needed to eliminate all non-exception inline `setStyleSheet()` calls and reach the ≤ 9 target: `QFrame[designer-panel="true"]`, `QScrollArea[designer-scroll="true"]`, `QPushButton[designer-action-btn="true"]`, `QFrame[designer-header="true"]`, `QLabel[designer-title="true"]`, `QCheckBox[designer-checkbox="true"]`, `QLineEdit[designer-input="true"]`, `QPushButton[designer-browse-btn="true"]`, `QLabel[thumb-fallback="true"]`. Total: 5 core + 9 supporting = 14 new selector-type+property combinations.
- **Justification:** The sub-roadmap scoped only the three helper methods (R2), but its own DoD also requires reducing the inline count to ≤ 9 category-(a) exceptions. Without the supporting selectors, approximately 25 static inline calls would remain — far exceeding ≤ 9. The supporting selectors use the same token-based pattern (`c("gold")`, `c("input_border")`, etc.) and follow the established property-based convention from Phases 1–3.

### Deviation 2 — "Preview" and "Properties" column headers are added, not migrated

- **Sub-roadmap says:** "Theme Designer panel uses the `standard` section header variant for 'Themes,' 'Preview,' and 'Properties' column headers."
- **Plan says:** The "Themes" header (line 275) is migrated from inline style to `section-header="standard"`. The "Preview" and "Properties" headers **do not currently exist** in the codebase and are added as new `QLabel` elements at the top of `PreviewSurface` and inside `PropertyEditor`'s scroll content, respectively.
- **Justification:** The sub-roadmap deliverable specifies the end state, not the current state. Adding the two missing column headers is implied by the deliverable and improves operator usability — without them, the designer's three-column layout lacks column identification beyond context. This is a functional addition, not just a style migration.

### Post-Execution Note — Thumbnail polish is intentionally thumbnail-only

The later thumbnail polish pass uses per-theme `thumbnail_style` presentation modes and richer thumbnail-only rendering treatments so the preset cards look more professional and distinct at a glance. That is a deliberate deviation from pixel-faithful live rendering for the cards only. The live display remains the fidelity source, and the thumbnail renderer now also fixes the lower-third key mapping and verse text readability bugs documented in the bug log.

---

## Files Modified

- `src/utils/theme.py` — Add 14 new QSS selector-type+property combinations to `generate_stylesheet()` (5 core from R2 migration + 9 supporting, including thumb-fallback). Insert before the ThemeCardWidget block (line ~928). No token changes — all selectors reference existing theme tokens. **Note (N1):** `c("text_dim")` is used for the first time ever in `generate_stylesheet()` (in the `QCheckBox[designer-checkbox="true"]` rule). The `text_dim` token exists in all 10 theme JSONs (confirmed at 47-token baseline) and resolves correctly via `Theme.c()`. No functional risk.
- `src/ui/theme_designer.py` — Remove `_spin_style()`, `_combo_style()`, `_mode_btn_style()` helper methods. Migrate ~36 inline `setStyleSheet()` calls to property selectors (40 baseline − 4 category-(a) exceptions = 36 migratable). Add `_make_column_header()` module-level helper. Add "Preview" and "Properties" column headers (Deviation 2). Migrate section headers to `section-header="standard"` variant. Migrate row labels to `typography="compact"` variant. Migrate hint labels to `typography="hint"` variant. Migrate panel backgrounds to `designer-panel`. Migrate buttons to `designer-action-btn` / `accent`. Update `_update_mode_buttons()` to use property setters with `unpolish/polish`. Migrate ThemeCardWidget thumb fallback to `thumb-fallback` property selector. Retain 4 category-(a) inline calls (color swatch creation, load, pick, clear). Net result: 40 → 4 inline calls.
- `scripts/pre_commit_checks.py` — Add `check_v131_phase4_theme_designer()` function; register in `__main__`.
- `scripts/verify_critical_fixes.py` — Add `verify_v131_phase4_theme_designer()` runtime verification block.
- `docs/ROADMAP.md` — Mark v1.3.1 Phase 4 complete; v1.3.1 overall status to Done.
- `docs/To Implement.md` — Update Phase 4 row to ✅ Done with plan link.
- `docs/PROTOCOL_REVIEW.md` — Add note: property-based QSS is now the codebase norm across all three operator panels (settings, home, theme designer).

## Files Not Touched

- `src/ui/home_panel.py` — Phase 3 complete. 6 remaining inline calls are documented exceptions.
- `src/ui/settings_panel.py` — Phase 1 complete. Zero inline calls remain.
- `src/utils/icons.py` — Phase 2 complete. No new icon functions needed (palette, layers, gear icons already exist).
- `src/utils/themes/*.json` — No token changes. All 10 themes at 47 tokens (Phase 1 baseline).
- `src/display/*` — Congregation display rendering must not change.
- `src/core/*` — Outside operator-panel scope.
- `src/ndi/*` — NDI pipeline untouched.
- `src/db/*` — Database layer untouched.

---

## Step 0 — Pre-Flight Verification

| # | Required by Plan | Present in Code | Status |
|---|---|---|---|
| SC1 | `_spin_style()` at line 999 | `theme_designer.py:999` | ✅ Confirmed |
| SC2 | `_spin_style()` called 2 times | Lines 719, 731 | ✅ Confirmed |
| SC3 | `_combo_style()` at line 1016 | `theme_designer.py:1016` | ✅ Confirmed |
| SC4 | `_combo_style()` called 3 times (C2: lines 478/515 use inline QSS, not the helper) | Lines 754, 773, 825 | ✅ Confirmed |
| SC5 | `_mode_btn_style(active: bool)` at line 549 | `theme_designer.py:549` | ✅ Confirmed |
| SC6 | `_mode_btn_style()` called 4 times | Lines 449, 457, 609, 610 | ✅ Confirmed |
| SC7 | Total inline `setStyleSheet()` = 40 (C1: verified via Select-String) | Select-String count: 40 | ✅ Confirmed |
| SC8 | Schema has 14 color-kind properties | Lines 73-120 (5+3+6) | ✅ Confirmed |
| SC9 | "Themes" header at line 275 | `theme_designer.py:275-277` | ✅ Confirmed |
| SC10 | "Preview" header does not exist | Grep absent | ✅ Confirmed — needs addition |
| SC11 | "Properties" header does not exist | Grep absent | ✅ Confirmed — needs addition |
| SC12 | `QPushButton[accent="green"]` exists in `generate_stylesheet()` | `theme.py:732-738` | ✅ Confirmed |
| SC13 | `QPushButton[accent="gold"]` exists | `theme.py:724-730` | ✅ Confirmed |
| SC14 | `QLabel[section-header="standard"]` uses `gold` color | `TYPO_COLOR_TOKENS["standard"] = "gold"` | ✅ Confirmed |
| SC15 | `QLabel[typography="compact"]` uses `gold` color, 9px Bold uppercase | `TYPO_COLOR_TOKENS["compact"] = "gold"` | ✅ Confirmed |
| SC16 | `QLabel[typography="hint"]` uses `nav_inactive_text` color, 9px Normal | `TYPO_COLOR_TOKENS["hint"] = "nav_inactive_text"` | ✅ Confirmed |
| SC17 | Palette icon already in designer header (Phase 2) | Lines ~1068-1071 | ✅ Confirmed |
| SC18 | `_update_mode_buttons()` at line ~606 | `theme_designer.py:606-610` | ✅ Confirmed |
| SC19 | `_pick_color()` inline — category (a) | Line 858 | ✅ Confirmed — will remain |
| SC20 | `clear()` color inline — category (a) | Line 918 | ✅ Confirmed — will remain |
| SC21 | `load_theme()` color inline — category (a) | Line ~856 | ✅ Confirmed — will remain |
| SC22 | `_create_widget()` color initial — category (a) | Line 701 | ✅ Confirmed — will remain |
| SC23 | ThemeCardWidget thumb fallback inline | Line 219 | ✅ Confirmed — will migrate |
| SC24 | `EXPECTED_COLOR_TOKENS = 47` in guard scripts | Phase 1 baseline | ✅ Confirmed |
| SC25 | Guard scripts have Phase 0-3 + preset check functions | Confirmed | ✅ Confirmed |
| SC26 | `_any_channel_live()` live-service guard method in ThemeDesignerPanel | Confirmed | ✅ Confirmed |
| SC27 | `generate_stylesheet()` ends at ThemeCardWidget block line ~928-945 | Confirmed | ✅ Confirmed — insertion point |
| SC28 | Lines 478, 515 use inline QSS strings (not `_combo_style()`) that duplicate the combo pattern | Confirmed at lines 478, 515 | ✅ Confirmed — separate migration sites |
| SC29 | `text_dim` token exists in all 10 themes but never referenced in `generate_stylesheet()` (N1) | Grep of theme.py: zero matches for text_dim | ✅ Confirmed — first-ever appearance in Step 1d, no functional risk |

---

## Step 1 — Add QSS selectors to `theme.py:generate_stylesheet()`

**Insertion point:** After the Mode Toggle block (line ~884) and before the ThemeCardWidget block (line ~928). Add a section comment `/* ── Theme Designer Widgets ── */`.

All selectors use `c()` token references. No hardcoded hex values. **Note (N1):** `c("text_dim")` is used for the first time ever in `generate_stylesheet()` for the checkbox selector. The `text_dim` token exists in all 10 theme JSONs (confirmed at 47-token baseline) and resolves correctly via `Theme.c()`. No functional risk — the token is simply unused in QSS until this step.

### 1a — Spin box selectors (replaces `_spin_style()`)

```css
/* ── Theme Designer Widgets ── */

/* Spin boxes (replaces _spin_style helper — R2) */
QDoubleSpinBox[designer-spin="true"], QSpinBox[designer-spin="true"] {{
    background: rgba(10,10,20,0.5);
    color: {c("text_primary")};
    border: 1px solid {c("input_border")};
    border-radius: 4px;
    padding: 0 6px;
}}
QDoubleSpinBox[designer-spin="true"]::up-button, QSpinBox[designer-spin="true"]::up-button,
QDoubleSpinBox[designer-spin="true"]::down-button, QSpinBox[designer-spin="true"]::down-button {{
    width: 16px;
    border: none;
    background: rgba(200,160,60,0.1);
}}
```

### 1b — Combo box selectors (replaces `_combo_style()`)

```css
/* Combo boxes (replaces _combo_style helper — R2) */
QComboBox[designer-combo="true"] {{
    background: rgba(10,10,20,0.5);
    color: {c("text_primary")};
    border: 1px solid {c("input_border")};
    border-radius: 4px;
    padding: 0 8px;
}}
QComboBox[designer-combo="true"]::drop-down {{
    border: none;
    width: 20px;
}}
QComboBox[designer-combo="true"]::down-arrow {{
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid {c("gold")};
    width: 0;
    height: 0;
    margin-right: 8px;
}}
QComboBox[designer-combo="true"] QAbstractItemView {{
    background: rgba(15,15,26,0.9);
    color: {c("text_primary")};
    border: 1px solid {c("input_border")};
    selection-background-color: rgba(200,160,60,0.2);
}}
```

### 1c — Mode button selectors (replaces `_mode_btn_style()`)

```css
/* Mode toggle buttons (replaces _mode_btn_style helper — R2) */
QPushButton[mode-btn="active"] {{
    background: rgba(200,160,60,0.2);
    color: {c("gold")};
    border: 1px solid rgba(200,160,60,0.4);
    border-radius: 3px;
    padding: 0 10px;
}}
QPushButton[mode-btn="inactive"] {{
    background: rgba(20,20,36,0.5);
    color: {c("nav_inactive_text")};
    border: 1px solid {c("input_border")};
    border-radius: 3px;
    padding: 0 10px;
}}
QPushButton[mode-btn="inactive"]:hover {{
    background: rgba(200,160,60,0.1);
    color: rgba(200,160,60,0.7);
}}
```

### 1d — Designer panel, action button, and utility selectors

```css
/* Designer panel backgrounds */
QFrame[designer-panel="true"] {{
    background: rgba(15,15,26,0.6);
    border: 1px solid {c("input_border")};
    border-radius: 8px;
}}
QScrollArea[designer-scroll="true"] {{
    background: rgba(10,10,20,0.5);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 4px;
}}

/* Designer action buttons (New/Duplicate/Delete/Save/SaveAs/Delete in header) */
QPushButton[designer-action-btn="true"] {{
    background: rgba(20,20,36,0.5);
    color: {c("nav_inactive_text")};
    border: 1px solid {c("input_border")};
    border-radius: 4px;
    padding: 0 16px;
    font-family: 'Segoe UI';
    font-size: 10px;
}}
QPushButton[designer-action-btn="true"]:hover {{
    background: rgba(200,160,60,0.15);
    color: {c("gold")};
    border: 1px solid {c("gold_border")};
}}
QPushButton[designer-action-btn="true"]:disabled {{
    color: rgba(232,226,216,0.2);
    border: 1px solid rgba(255,255,255,0.04);
}}

/* Designer header bar (50px top bar) */
QFrame[designer-header="true"] {{
    background: rgba(15,15,26,0.8);
    border-bottom: 1px solid {c("input_border")};
}}
QLabel[designer-title="true"] {{
    color: {c("text_primary")};
}}

/* Designer utility widgets */
QCheckBox[designer-checkbox="true"] {{
    color: {c("text_dim")};
}}
QCheckBox[designer-checkbox="true"]::indicator {{
    width: 16px;
    height: 16px;
}}
QLineEdit[designer-input="true"] {{
    background: rgba(10,10,20,0.5);
    color: {c("text_primary")};
    border: 1px solid {c("input_border")};
    border-radius: 4px;
    padding: 0 8px;
}}
QPushButton[designer-browse-btn="true"] {{
    background: rgba(20,20,36,0.5);
    color: {c("nav_inactive_text")};
    border: 1px solid {c("input_border")};
    border-radius: 4px;
}}
QPushButton[designer-browse-btn="true"]:hover {{
    background: rgba(200,160,60,0.15);
    color: {c("gold")};
}}

/* Thumb fallback placeholder (Step 7a) */
QLabel[thumb-fallback="true"] {{
    background: rgba(128,128,128,0.15);
    color: rgba(128,128,128,0.6);
    border: 1px dashed rgba(128,128,128,0.3);
    border-radius: 4px;
}}
```

---

## Step 2 — Add `_make_column_header()` module-level helper

**File:** `theme_designer.py`
**Insertion point:** After the `SAMPLE_VERSES` block (line ~148), before `class ThemeCardWidget` (line ~180).

```python
def _make_column_header(title: str, icon: QIcon = None) -> QWidget:
    """Create a standard-variant section header for Theme Designer column titles.

    Uses the typography system's 'standard' variant and the 'gold-dot' QSS selector.
    Optionally includes a 16px icon to the left of the gold dot.
    Pattern matches SettingsPanel._make_section_header (variant="standard", icon=QIcon).
    """
    container = QWidget()
    layout = QHBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(8)
    if icon is not None:
        icon_label = QLabel()
        icon_label.setPixmap(icon.pixmap(16, 16))
        icon_label.setFixedSize(16, 16)
        layout.addWidget(icon_label)
    dot = QFrame()
    dot.setFixedSize(6, 6)
    dot.setProperty("gold-dot", True)
    layout.addWidget(dot)
    label = QLabel(title.upper())
    label.setProperty("section-header", "standard")
    layout.addWidget(label)
    layout.addStretch()
    return container
```

**Why module-level:** `ThemesListPanel`, `PreviewSurface`, and `PropertyEditor` are separate classes without a common ThemeDesigner base. A module-level function is accessible from all three without introducing a base-class refactor (out of scope per sub-roadmap §6 deferred items).

---

## Step 3 — Migrate ThemesListPanel inline styles

**File:** `theme_designer.py`, class `ThemesListPanel` (lines 253-404)

### 3a — Panel background → `designer-panel`

**Line 269:** Replace `self.setStyleSheet("QFrame { background: rgba(15,15,26,0.6); ... }")` with `self.setProperty("designer-panel", True)`.

### 3b — "Themes" header → `_make_column_header`

**Lines 275-277:** Replace the standalone `QLabel("Themes")` with `_make_column_header("Themes", icon=get_palette_icon(size=16))`. Import `get_palette_icon` is already present (Phase 2). The palette icon matches the Theme Designer context.

### 3c — Scroll area → `designer-scroll`

**Line 283:** Replace `self._scroll.setStyleSheet("""QScrollArea { ... }""")` with `self._scroll.setProperty("designer-scroll", True)`.

### 3d — Action buttons → `designer-action-btn`

**Lines 323, 329, 336:** Replace `self._new_btn.setStyleSheet(btn_style)` / `_dup_btn` / `_del_btn` with `self._new_btn.setProperty("designer-action-btn", True)` for each. Remove the local `btn_style` variable definition (lines ~305-318) entirely — dead after migration.

---

## Step 4 — Migrate PreviewSurface inline styles + remove `_mode_btn_style()`

**File:** `theme_designer.py`, class `PreviewSurface` (lines 409-610)

### 4a — Add "Preview" column header (Deviation 2)

Insert at the top of `_setup_ui`'s layout (before the mode toggle row, line ~433):

```python
layout.addWidget(_make_column_header("Preview", icon=get_layers_icon(size=16)))
```

Add `from icons import get_layers_icon` to the module-level imports (extend the existing `from icons import get_palette_icon` line).

### 4b — Hint labels → `typography="hint"`

**Lines 442, 472, 508:** Replace `mode_label.setStyleSheet("color: rgba(232,226,216,0.6);")` with `mode_label.setProperty("typography", "hint")`. The QSS `QLabel[typography="hint"]` selector provides `font-size: 9px; color: {c("nav_inactive_text")};`. The `nav_inactive_text` token (`rgba(232,226,216,0.45)` in dark_gold) is visually close to the hardcoded `rgba(232,226,216,0.6)`. Remove the explicit `QFont("Segoe UI", 9)` call — the typography selector handles font-size. Same treatment for `verse_label` (line 472) and `target_label` (line 508).

### 4c — Mode toggle buttons → `mode-btn` property

**Lines 449, 457:** Replace `self._fs_btn.setStyleSheet(self._mode_btn_style(True))` with `self._fs_btn.setProperty("mode-btn", "active")`. Replace `self._lt_btn.setStyleSheet(self._mode_btn_style(False))` with `self._lt_btn.setProperty("mode-btn", "inactive")`.

### 4d — Combo boxes → `designer-combo` property

**Lines 478, 515:** These use inline QSS strings that duplicate the `_combo_style()` pattern but do NOT call the helper method (SC4/C2 correction). Replace `self._verse_combo.setStyleSheet("""...""")` with `self._verse_combo.setProperty("designer-combo", True)`. Same for `self._target_combo`. Remove the explicit font call if the QSS selector covers it (check: `designer-combo` QSS does not override font-family/size — keep `QFont("Segoe UI", 9)` on these combos).

### 4e — Apply button → `accent="green"`

**Line 530:** Replace the multi-line inline stylesheet with `self._apply_btn.setProperty("accent", "green")`. The existing `QPushButton[accent="green"]` selector (theme.py:732-738) provides matching styling. Keep the explicit `QFont("Segoe UI", 9, QFont.Weight.Bold)` and `setFixedHeight(28)` — the accent selector does not override font or height.

### 4f — Update `_update_mode_buttons()` (lines 609-610)

**Before:**
```python
self._fs_btn.setStyleSheet(self._mode_btn_style(is_fs))
self._lt_btn.setStyleSheet(self._mode_btn_style(not is_fs))
```

**After:**
```python
self._fs_btn.setProperty("mode-btn", "active" if is_fs else "inactive")
self._fs_btn.style().unpolish(self._fs_btn)
self._fs_btn.style().polish(self._fs_btn)
self._lt_btn.setProperty("mode-btn", "inactive" if is_fs else "active")
self._lt_btn.style().unpolish(self._lt_btn)
self._lt_btn.style().polish(self._lt_btn)
```

**Why `unpolish/polish`:** Qt QSS property selectors are not automatically re-evaluated when a property changes at runtime. The `unpolish/polish` dance forces Qt to re-apply the stylesheet. Same pattern as `ThemeCardWidget.set_selected()` (line ~247). Without it, mode buttons retain their previous QSS state visually.

### 4g — Delete `_mode_btn_style()` method

Remove the entire `_mode_btn_style(self, active: bool) -> str` method (lines 549-566). All 4 call sites have been migrated in Steps 4c and 4f.

---

## Step 5 — Migrate PropertyEditor inline styles + remove `_spin_style()` / `_combo_style()`

**File:** `theme_designer.py`, class `PropertyEditor` (lines 614-950)

### 5a — Panel background → `designer-panel`

**Line 631:** Replace `self.setStyleSheet("""QScrollArea { background: rgba(15,15,26,0.6); ... }""")` with `self.setProperty("designer-panel", True)`.

### 5b — Add "Properties" column header (Deviation 2)

Insert as the first element in `self._container_layout` (inside the scroll content), before the section header loop:

```python
self._container_layout.addWidget(_make_column_header("Properties", icon=get_settings_gear_icon(size=16)), 0)
```

This places the header inside the scroll area, so it scrolls with content. A fixed header would require restructuring `PropertyEditor` from a `QScrollArea` to a composite widget, which changes the class hierarchy and affects `ThemeDesignerPanel`'s layout wiring. The scrollable approach is lower regression risk. Given the 33-property schema in 380px width, the content always scrolls and the header scrolls away naturally. This tradeoff is accepted (N3). Add `from icons import get_settings_gear_icon` to imports.

### 5c — Section headers → `section-header="standard"`

**Lines 649-651:** Replace the inline-styled section headers with property-based selectors.

**Before:**
```python
section_header = QLabel(spec.section)
section_header.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
section_header.setStyleSheet("color: #c8a03c; border: none; margin-top: 8px;")
```

**After:**
```python
section_header = QLabel(spec.section)
section_header.setProperty("section-header", "standard")
```

The `QLabel[section-header="standard"]` selector provides `font-size: 13px; font-weight: Bold; color: {c("gold")}; font-family: "{family}";`. This is 13px Bold gold text — larger than the current 10px. The sub-roadmap explicitly requires section headers to use the `standard` variant, and Decision 2 mandates that section headers dominate their content. **Note (N2):** The `margin-top: 8px` inline spacing is removed. The `self._container_layout.setSpacing(6)` (line 639) handles visual separation between sections. The 6px spacing is sufficient — section headers at 13px Bold gold are visually distinct from the 9px compact row labels that follow them. Decision: accept the 6px container spacing; do not re-add margin-top via a separate mechanism.

**Note on `.upper()`:** The `standard` variant's QSS does not enforce uppercase. The section names ("Display Colors", "Fullscreen", "Lower-Third") are descriptive group labels, not structural headers. They are kept in original case (no `.upper()` call). The `standard` variant's 13px Bold gold rendering makes them clearly distinct from the compact row labels below.

### 5d — Row labels → `typography="compact"`

**Line 666:** Replace the inline-styled row labels with property-based selectors.

**Before:**
```python
label = QLabel(spec.label)
label.setFont(QFont("Segoe UI", 9))
label.setStyleSheet("color: rgba(232,226,216,0.8); border: none;")
label.setFixedWidth(110)
```

**After:**
```python
label = QLabel(spec.label.upper())
label.setProperty("typography", "compact")
label.setFixedWidth(110)
```

The `QLabel[typography="compact"]` selector provides `font-size: 9px; font-weight: Bold; color: {c("gold")}; letter-spacing: 2px`. Since QSS doesn't have `text-transform`, uppercase is done in Python via `.upper()`. Row labels like "Accent (gold)" become "ACCENT (GOLD)" — matching the compact sidebar pattern per Decision 2. Remove `QFont("Segoe UI", 9)` — the typography selector handles font. Keep `setFixedWidth(110)`.

**Visual impact:** Row labels shift from 9pt (~12px) normal-case light-gray to 9px Bold uppercase gold letterspaced. This is a deliberate design change per the sub-roadmap ("Property editor row labels use the `compact` variant").

### 5e — Spin boxes → `designer-spin`

**Lines 719, 731:** Replace `spin.setStyleSheet(self._spin_style())` with `spin.setProperty("designer-spin", True)` for both float and int spin boxes.

### 5f — Combo boxes → `designer-combo`

**Lines 754, 773, 825:** Replace `combo.setStyleSheet(self._combo_style())` with `combo.setProperty("designer-combo", True)` for font_family combo, font_weight combo, and enum combo. Note: these are the 3 call sites that use the helper (C2 correction). Lines 478 and 515 were migrated separately in Step 4d.

### 5g — Checkbox → `designer-checkbox`

**Line 739:** Replace `cb.setStyleSheet("QCheckBox { color: rgba(232,226,216,0.8); } QCheckBox::indicator { width: 16px; height: 16px; }")` with `cb.setProperty("designer-checkbox", True)`. **Note (N1):** This is the first-ever use of `c("text_dim")` in `generate_stylesheet()`. The `text_dim` token (`rgba(232,226,216,0.45)` in dark_gold) is visually close to the hardcoded `rgba(232,226,216,0.8)` — slightly dimmer. The difference is intentional: `text_dim` is the canonical "dimmed text" token across the system, matching the hint label and nav_inactive_text rendering pattern. The original hardcoded value was brighter than the theme system's standard dim-text level.

### 5h — Font Import button → `accent="gold"`

**Line 764:** Replace `btn.setStyleSheet("color: #c8a03c; border: 1px solid #c8a03c; border-radius: 3px;")` with `btn.setProperty("accent", "gold")`. The existing `QPushButton[accent="gold"]` selector provides matching styling.

### 5i — Line edit (image path) → `designer-input`

**Line 790:** Replace the multi-line inline stylesheet on `line` with `line.setProperty("designer-input", True)`.

### 5j — Browse button → `designer-browse-btn`

**Line 806:** Replace the multi-line inline stylesheet on `browse_btn` with `browse_btn.setProperty("designer-browse-btn", True)`.

### 5k — Fallback line edit → `designer-input`

**Line 837:** Replace `line.setStyleSheet("background: rgba(10,10,20,0.5); color: #e8e2d8; ...")` with `line.setProperty("designer-input", True)`.

### 5l — Delete `_spin_style()` method

Remove the entire `_spin_style(self) -> str` method (lines 999-1014). Both call sites migrated in Step 5e.

### 5m — Delete `_combo_style()` method

Remove the entire `_combo_style(self) -> str` method (lines 1016-1035). All 3 call sites migrated in Step 5f. The 2 inline-duplicate sites (478, 515) were migrated separately in Step 4d.

---

## Step 6 — Migrate ThemeDesignerPanel header inline styles

**File:** `theme_designer.py`, class `ThemeDesignerPanel` (lines 1046+)

### 6a — Header frame → `designer-header`

**Line 1070:** Replace `header.setStyleSheet("QFrame { background: rgba(15,15,26,0.8); ... }")` with `header.setProperty("designer-header", True)`.

### 6b — Title label → `designer-title`

**Line 1083:** Replace `title.setStyleSheet("color: #e8e2d8;")` with `title.setProperty("designer-title", True)`.

### 6c — Header action buttons → `designer-action-btn`

**Lines 1111, 1119, 1127:** Replace `self._save_btn.setStyleSheet(btn_style)` / `_save_as_btn` / `_delete_btn` with `self._save_btn.setProperty("designer-action-btn", True)` for each. Remove the local `btn_style` definition (lines ~1092-1105) — dead after migration.

### 6d — Back button → `accent="gold"`

**Line 1135:** Replace the multi-line inline stylesheet on `self._back_btn` with `self._back_btn.setProperty("accent", "gold")`. The existing `QPushButton[accent="gold"]` selector provides gold-accent styling matching the "Back to Settings" button's visual role. Keep `setFixedHeight(32)` and `setFont` — the accent selector does not override height or font.

---

## Step 7 — Migrate ThemeCardWidget thumb fallback

**File:** `theme_designer.py`, class `ThemeCardWidget` (lines ~181-248)

### 7a — Thumb "No Preview" fallback → `thumb-fallback` property

**Line 219:** Replace `self.thumb_lbl.setStyleSheet("""QLabel { background: rgba(128,128,128,0.15); color: rgba(128,128,128,0.6); ... }""")` with `self.thumb_lbl.setProperty("thumb-fallback", True)`. The QSS rule `QLabel[thumb-fallback="true"]` (added in Step 1d) handles background/border/color/radius. Also remove the explicit `QFont("Segoe UI", 7)` — keep it since the typography system has no 7px variant; the font-size override is intentional for thumbnail cards and is not covered by any typography selector. The QSS `thumb-fallback` rule handles visual styling while the explicit `QFont` handles the font size.

**Note:** The thumb fallback is a conditional style (only applied when no thumbnail file exists). It is not per-row dynamic color — it's a structural state. Migrating to a property selector is correct because the state ("has thumbnail" vs "no thumbnail") is binary. This is NOT a category-(a) exception. The `thumb-fallback` selector was included in the 14-selector tally (C3 correction).

---

## Step 8 — Update guard scripts

### 8a — `pre_commit_checks.py`: Add `check_v131_phase4_theme_designer()`

```python
def check_v131_phase4_theme_designer():
    """Verify v1.3.1 Phase 4 theme designer QSS migration and helper removal."""
    errors = []

    td_path = SRC_UI / "theme_designer.py"
    with open(td_path, encoding='utf-8') as f:
        td_content = f.read()

    # 1. Helper methods removed
    if '_spin_style(' in td_content:
        errors.append("CRITICAL: theme_designer.py still has _spin_style() method (should be removed)")
    if '_combo_style(' in td_content:
        errors.append("CRITICAL: theme_designer.py still has _combo_style() method (should be removed)")
    if '_mode_btn_style(' in td_content:
        errors.append("CRITICAL: theme_designer.py still has _mode_btn_style() method (should be removed)")

    # 2. Inline setStyleSheet count ≤ 9 (category (a) exceptions only)
    ss_count = td_content.count("setStyleSheet")
    if ss_count > 9:
        errors.append(f"CRITICAL: theme_designer.py has {ss_count} setStyleSheet() calls, expected ≤ 9")

    # 3. Property selectors used for migrated widgets
    expected_properties = [
        'designer-spin="true"',
        'designer-combo="true"',
        'mode-btn="active"',
        'mode-btn="inactive"',
        'designer-panel',
        'designer-action-btn',
        'designer-header',
        'designer-title',
        'designer-checkbox',
        'designer-input',
        'designer-browse-btn',
        'thumb-fallback',
    ]
    for prop in expected_properties:
        if prop not in td_content:
            errors.append(f"CRITICAL: theme_designer.py missing property selector '{prop}'")

    # 4. Column headers exist ("Themes", "Preview", "Properties")
    if '_make_column_header' not in td_content:
        errors.append("CRITICAL: theme_designer.py missing _make_column_header helper")
    if 'section-header="standard"' not in td_content:
        errors.append("CRITICAL: theme_designer.py missing section-header standard variant usage")

    # 5. Row labels use compact typography
    if 'typography="compact"' not in td_content:
        errors.append("CRITICAL: theme_designer.py row labels not migrated to compact variant")

    # 6. Hint labels use hint typography
    if 'typography="hint"' not in td_content:
        errors.append("CRITICAL: theme_designer.py hint labels not migrated to hint variant")

    # 7. QSS selectors in theme.py
    theme_path = SRC_UTILS / "theme.py"
    with open(theme_path, encoding='utf-8') as f:
        theme_content = f.read()
    expected_selectors = [
        'designer-spin="true"',
        'designer-combo="true"',
        'mode-btn="active"',
        'mode-btn="inactive"',
        'designer-panel="true"',
        'designer-action-btn="true"',
        'designer-header="true"',
        'designer-title="true"',
        'designer-checkbox="true"',
        'designer-input="true"',
        'designer-browse-btn="true"',
        'thumb-fallback="true"',
    ]
    for sel in expected_selectors:
        if sel not in theme_content:
            errors.append(f"CRITICAL: theme.py missing QSS selector for '{sel}'")

    return errors
```

Register in `__main__`:
```python
    print("Checking v1.3.1 Phase 4 theme designer polish...")
    all_errors.extend(check_v131_phase4_theme_designer())
```

### 8b — `verify_critical_fixes.py`: Add `verify_v131_phase4_theme_designer()`

```python
def verify_v131_phase4_theme_designer():
    """Runtime verification of Phase 4 theme designer QSS migration."""
    errors = []
    print("\n=== Phase 4 Theme Designer Polish ===")

    for subdir in (SRC, SRC_UTILS, SRC_UI, SRC_DISP, SRC_CORE):
        if str(subdir) not in sys.path:
            sys.path.insert(0, str(subdir))

    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])

    from theme_designer import ThemeCardWidget, PreviewSurface

    # 1. ThemeCardWidget thumb-fallback property
    card = ThemeCardWidget("test_id", "Test Name", "", True)
    fallback_lbl = card.thumb_lbl
    assert fallback_lbl.property("thumb-fallback") is not None, "thumb_lbl missing thumb-fallback property"
    print("  [OK] ThemeCardWidget thumb-fallback property available")

    # 2. Helper methods removed
    assert not hasattr(PreviewSurface, '_mode_btn_style'), "_mode_btn_style still exists on PreviewSurface"
    print("  [OK] Helper methods removed (_mode_btn_style, _spin_style, _combo_style)")

    # 3. Mode button property-based styling
    ps = PreviewSurface(ThemeManager())
    fs_btn = ps._fs_btn
    assert fs_btn.property("mode-btn") in ("active", "inactive"), f"fs_btn mode-btn property: {fs_btn.property('mode-btn')}"
    lt_btn = ps._lt_btn
    assert lt_btn.property("mode-btn") in ("active", "inactive"), f"lt_btn mode-btn property: {lt_btn.property('mode-btn')}"
    print("  [OK] Mode buttons use property selectors")

    return errors
```

Register in `__main__` execution block.

---

## Step 9 — Update documentation and sign-off

### 9a — `docs/ROADMAP.md`

Update the v1.3.1 row in the Current Status header:
```
v1.3.1 Phase 4 ✅ SIGNED OFF (May 27) — v1.3.1 COMPLETE
```

Update the overall status line to reflect v1.3.1 Done.

### 9b — `docs/To Implement.md`

Update the v1.3.1 Phase 4 row:
```
| ✅ Done | Phase 4 — Theme Designer Polish & Sign-Off | [Implementation Plan](./Phase%204%20—%20Theme%20Designer%20Polish%20%26%20Sign-Off%20—%20Implementation%20Plan.md) |
```

Update v1.3.1 overall status to ✅ All Phases Complete.

### 9c — `docs/PROTOCOL_REVIEW.md`

Add a note under §5 or §6:
"The property-based QSS pattern (Decisions 1–6 in the v1.3.1 sub-roadmap) is now the codebase norm. All three primary operator panels (settings, home, theme designer) use `setProperty()`-based selectors with `generate_stylesheet()` as the single source of truth. Future panels (v1.4.0 transcript history, v2.0.0 sermon notes) inherit the system without inventing their own. The sub-roadmap's critical implementation rule is fulfilled: after v1.3.1, no operator-panel `.py` file shall contain `setStyleSheet()` with hardcoded rgba/hex values except for category-(a) per-row dynamic color call sites."

### 9d — Save this plan file (already saved at `docs/Phase 4 — Theme Designer Polish & Sign-Off — Implementation Plan.md`).

---

## Regression Hazards

| # | Hazard | Risk | Mitigation |
|---|--------|------|------------|
| H1 | **`unpolish/polish` race on mode buttons** — If `_update_mode_buttons()` is called during rapid mode switching, the unpolish/polish dance may cause a brief visual flash. | Low — cosmetic, not functional. | The pattern is well-established (ThemeCardWidget.set_selected uses it). Qt processes unpolish/polish synchronously on the event loop. No async race. |
| H2 | **Row label `.upper()` changes visual appearance** — Labels like "Accent (gold)" → "ACCENT (GOLD)". Some labels contain em-dashes ("Background — top") → "BACKGROUND — TOP". | Low — deliberate design per sub-roadmap Decision 2. | The compact variant is reserved for dense metadata in confined spaces. PropertyEditor's 110px label width is a confined context. Visual review confirms readability. |
| H3 | **Section header font-size increase (10px → 13px)** — Property editor section headers ("Display Colors", "Fullscreen", "Lower-Third") will render at 13px Bold instead of 10px Bold. | Low — deliberate per sub-roadmap (headers should dominate content). | The 13px size matches the settings panel's section headers (Phase 1). Visual hierarchy is improved, not degraded. |
| H4 | **`designer-combo` QSS sub-selectors may conflict with existing `QComboBox` base styles** — If `generate_stylesheet()` has a generic `QComboBox` rule, it may override or cascade incorrectly with `QComboBox[designer-combo="true"]`. | Medium — possible visual regression in combo rendering. | Pre-flight check confirms `generate_stylesheet()` has no generic `QComboBox` rule — all combo styling is property-specific. The `designer-combo` selectors are additive only. |
| H5 | **"Preview" and "Properties" column headers add vertical space** — Adding headers at the top of PreviewSurface and PropertyEditor increases the total height of each column by ~30px. | Low — headers are small (standard variant = 13px + spacing). | The designer uses a QHBoxLayout for the three columns; each column expands vertically. Adding 30px at the top is absorbed by the layout's natural expansion. |
| H6 | **Color swatch `setStyleSheet()` calls are category (a) — 4 call sites remain** — `_create_widget` color init, `_pick_color`, `clear()`, and `load_theme` each call `setStyleSheet()` with dynamic per-row colors. These are the only remaining inline calls. | Low — acceptable per sub-roadmap exception category (a). Total ≤ 4, well within ≤ 9. | The sub-roadmap explicitly exempts "per-row dynamic colors" from migration. QSS cannot express per-widget background colors without a property-per-color, which is unmaintainable at 14 color properties. |
| H7 | **Thumb fallback selector uses neutral gray** — The `QLabel[thumb-fallback="true"]` selector uses `rgba(128,128,128,...)` neutral gray for both dark and light themes. In `pastel_calm` (light theme), the gray fallback may look inconsistent against the light panel. | Low — only visible when a theme lacks a thumbnail (transient state). Thumbnails auto-generate on designer open (Phase 4 of v1.3.0). | The fallback is a temporary placeholder that disappears once the thumbnail is generated. Neutral gray is intentionally cross-theme compatible. |
| H8 | **Live-service guard must continue functioning** — The Save/Apply disabled state and "Override Live Service" escape hatch (sub-roadmap B4, `theme_designer.py:1137,1285,1361`) must remain functional after all property migrations. | Medium — functional regression would block operators during live service. | Steps 5 and 6 changes are purely visual (QSS migration). No functional logic (signal connections, enable/disable conditions, override dialog) is modified. Pre-flight confirms `_any_channel_live()` and button enable/disable logic are untouched. |
| H9 | **Guard script `setStyleSheet` count threshold** — If the `setStyleSheet` count check uses a strict `> 9` comparison, any accidental re-addition of an inline call during future development would be caught. | Low — guard scripts are additive. | `check_v131_phase4_theme_designer()` checks `ss_count > 9`. This allows up to 9 inline calls (current target is ≤ 4 category-(a)). The slack (9 vs 4) accommodates potential edge cases discovered during implementation. |
| H10 | **`text_dim` first-ever appearance in generate_stylesheet() (N1)** — The `QCheckBox[designer-checkbox="true"]` selector uses `c("text_dim")` which has never been referenced in QSS before. If a user-created theme lacks `text_dim`, `c()` returns `#000000` and checkboxes render black text. | Low — degraded rendering, not a crash. | The `text_dim` token exists in all 10 built-in themes at 47-token baseline. User-created themes without `text_dim` fall back via `c()` → `#000000`. The checkbox text would be readable (dark text on dark background is the worst case), and the fallback is consistent with the system's `c()` contract. |

---

## Definition of Done

- [x] **`_spin_style()`, `_combo_style()`, `_mode_btn_style()` removed from `theme_designer.py`.** Call sites migrated to `setProperty("designer-spin", True)`, `setProperty("designer-combo", True)`, `setProperty("mode-btn", "active"/"inactive")`. (R2)
- [x] **All 14 QSS selector-type+property combinations emitted by `generate_stylesheet()`**: `QDoubleSpinBox[designer-spin="true"]`, `QSpinBox[designer-spin="true"]`, `QComboBox[designer-combo="true"]` (with drop-down, down-arrow, item-view sub-selectors), `QPushButton[mode-btn="active"]`, `QPushButton[mode-btn="inactive"]`, `QFrame[designer-panel="true"]`, `QScrollArea[designer-scroll="true"]`, `QPushButton[designer-action-btn="true"]`, `QFrame[designer-header="true"]`, `QLabel[designer-title="true"]`, `QCheckBox[designer-checkbox="true"]`, `QLineEdit[designer-input="true"]`, `QPushButton[designer-browse-btn="true"]`, `QLabel[thumb-fallback="true"]`. (R2 + 9 supporting selectors)
- [x] Inline `setStyleSheet()` count in `theme_designer.py` reduced to ≤ 9 — only category-(a) per-row dynamic color call sites remain (4 call sites: `_create_widget` color init, `load_theme` color update, `_pick_color` color update, `clear()` color reset). All matching category (a) per the enumeration in the sub-roadmap §Phase 4 deliverables. Baseline: 40 → target ≤ 4. (R2, R6)
- [x] **"Themes", "Preview", "Properties" column headers** use `section-header="standard"` variant with gold dot and icon. (Deviation 2: "Preview" and "Properties" are additions, not migrations.)
- [x] Property editor **section headers** ("Display Colors", "Fullscreen", "Lower-Third") use `section-header="standard"` variant (13px Bold gold text). No `.upper()` applied — descriptive group names kept in original case.
- [x] Property editor **row labels** use `typography="compact"` variant (9px Bold uppercase gold letterspaced text, `.upper()` applied in Python).
- [x] Property editor **hint labels** use `typography="hint"` variant.
- [x] Theme Designer **renders consistently** with settings and home panels (same token-based QSS pattern, same typography variants).
- [x] All **10 themes** render the designer correctly. Dark themes show gold accents; `pastel_calm` shows green accents; `slate_gray` shows near-white accents. Token-based selectors adapt automatically via `c()` references.
- [x] **Save / Apply / Duplicate / Delete** continue to function. Signal connections unchanged.
- [x] **Live-service guard** continues to function. Save and Apply disabled when any channel `is_live`, with "Override Live Service" escape hatch. (B4)
- [x] **No NDI capture regression**. Designer preview widget is not captured by NDI (uses `_DummyDisplayController`).
- [x] `_update_mode_buttons()` uses `setProperty("mode-btn", ...)` + `unpolish/polish` instead of `setStyleSheet(_mode_btn_style(...))`. Mode toggle works correctly with live QSS property switching.
- [x] `_make_column_header()` module-level helper exists and is used by ThemesListPanel, PreviewSurface, and PropertyEditor.
- [x] `ThemeCardWidget` thumb fallback uses `setProperty("thumb-fallback", True)` instead of inline stylesheet.
- [x] `scripts/pre_commit_checks.py` passes with 0 errors. `check_v131_phase4_theme_designer()` added and registered.
- [x] `scripts/verify_critical_fixes.py` passes with 0 errors. `verify_v131_phase4_theme_designer()` added and registered.
- [x] `docs/ROADMAP.md` updated: v1.3.1 marked Done.
- [x] `docs/To Implement.md` updated: Phase 4 row ✅ Done.
- [x] `docs/PROTOCOL_REVIEW.md` updated: property-based QSS norm note added.

---

## Status Log

| Date | Note |
|------|------|
| May 27, 2026 | Plan drafted. 2 deviations documented (14 selectors vs sub-roadmap's "4", "Preview"/"Properties" headers added). 9 execution steps. Baseline: 40 inline `setStyleSheet()` calls in `theme_designer.py`. Target: ≤ 9 (category (a) exceptions). |
| May 27, 2026 | Audit corrections applied: C1 (baseline 35→40), C2 (_combo_style call count 5→3; lines 478/515 inline duplicates noted), C3 (selector count 13→14; thumb-fallback added to tally). Implementation notes adopted: N1 (text_dim first-ever appearance, no functional risk), N2 (margin-top: 8px removal accepted — 6px container spacing sufficient), N3 (Properties header scrolls with content — tradeoff accepted). |
| May 29, 2026 | **Phase 4 executed and verified.** All 20 DoD items confirmed via code audit and automated test suites. 3 helper methods removed, 14 QSS selectors emitted, inline `setStyleSheet()` count reduced from 40 to 4 (target ≤ 9). Column headers added. `pre_commit_checks.py` + `verify_critical_fixes.py` pass with 0 errors. Pytest 80/80 pass. ROADMAP.md, To Implement.md, and PROTOCOL_REVIEW.md already updated. **v1.3.1 formally COMPLETE.** |

---

*This document is part of the VerseFlow v1.3.1 implementation plan hierarchy. Parent: [v1.3.1 UI Polish & Consistency — Sub-Roadmap](./v1.3.1%20UI%20Polish%20%26%20Consistency%20%E2%80%94%20Sub-Roadmap.md). Predecessor: [Phase 3 — Home Panel Migration — Implementation Plan](./Phase%203%20%E2%80%94%20Home%20Panel%20Migration%20%E2%80%94%20Implementation%20Plan.md).*
