# Phase 1 — Settings Panel Polish Closeout
## Implementation Plan (v1.3.1)

> **Status:** ✅ Completed
> **Audit basis:** v1.3.1 UI Polish & Consistency Sub-Roadmap (May 22 revision). Cross-referenced against `settings_panel.py` (508 lines), `theme.py` (791 lines), all 10 built-in theme JSONs, `icons.py`, `pre_commit_checks.py`, `verify_critical_fixes.py`.
> **Sub-roadmap deviations:** 3 intentional (documented below)
> **Audit findings:** 5 issues (F1–F5) identified and fixed in this draft.

---

## Deviations from Sub-Roadmap

### Deviation 1 — `red_text` in all 10 built-in themes, not 3

- **Sub-roadmap says:** "New `red_text` token in all **3** built-in theme JSONs (`dark_gold`, `light`, `high_contrast`)."
- **Plan says:** `red_text` token is added to **all 10** built-in theme JSONs.
- **Justification:** The sub-roadmap text was written before v1.3.0 Phase 4 shipped 7 additional preset themes. `BUILTIN_THEME_IDS` now contains 10 entries. The sub-roadmap's own Decision 6 principle ("Status text colors become theme tokens, not inline literals") applies equally to all 10. Adding it only to 3 would leave 7 themes with no `red_text` — any theme switch would silently lose error label coloring. The token-count check in both guard scripts (`EXPECTED_COLOR_TOKENS = 46`) confirms all themes currently have the same token count, and adding `red_text` to all 10 preserves that invariant at the new count of 47.

### Deviation 2 — `QFrame[panel="true"]:hover` removal in Phase 1

- **Sub-roadmap says:** Phase 1 deliverables (sub-roadmap §Phase 1) list `QFrame[card="true"]:hover` removal. The panel hover is discussed in Phase 3's scope note (sub-roadmap §Phase 3 deliverable item 6) as a Phase 3 action: *"`QFrame[panel="true"]:hover` rule removed"*.
- **Plan says:** Both `QFrame[card="true"]:hover` AND `QFrame[panel="true"]:hover` are removed in Phase 1.
- **Justification:** (1) `settings_panel.py` contains zero widgets with `panel="true"` — grep confirms 0 matches for `panel.*true` in the file. The rule has no effect on the settings panel today. (2) The sub-roadmap §Phase 3 explicitly says *"the default case is removal, not introduction"* for panel hover — this plan is implementing that default early. (3) Removing now rather than in Phase 3 prevents a subtle cascade bug: if Phase 1 adds a `panel="true"` widget (it doesn't, but the rule would mask the mistake during testing), the hover would falsely suggest interactivity. (4) The `panel_border_hover` token becomes dead (see F3 hazard), but this is harmless and can be cleaned in a future token audit pass.

### Deviation 3 — Separator inside Channel Settings card

- **Sub-roadmap says:** "Channel Settings card reorders to put primary controls before navigation." No mention of adding a visual separator element.
- **Plan says:** A thin gold separator (`_make_separator()`) is inserted between the per-channel controls block and the demoted "Open Theme Designer" button within the card.
- **Justification:** The reorder creates two visual groups: (a) per-channel mode/theme controls and (b) the secondary designer-access action. Without a separator, the 12px card spacing alone is insufficient to visually distinguish these groups — the designer button blends into the per-channel sections. The 1px gold-dim separator signals a hierarchy boundary (primary controls above, secondary action below), matching the visual language already established for section headers in `content_layout`. This is a design refinement, not a functional change.

---

## Files Modified

- `src/utils/themes/dark_gold.json` — Add `red_text` token after `red_dim`
- `src/utils/themes/light.json` — Same
- `src/utils/themes/high_contrast.json` — Same
- `src/utils/themes/midnight_blue.json` — Same
- `src/utils/themes/forest_green.json` — Same
- `src/utils/themes/warm_amber.json` — Same
- `src/utils/themes/royal_purple.json` — Same
- `src/utils/themes/crimson_red.json` — Same
- `src/utils/themes/slate_gray.json` — Same
- `src/utils/themes/pastel_calm.json` — Same
- `src/utils/theme.py` — Add `QLabel[error="true"]` QSS rule; remove `QFrame[card="true"]:hover`; remove `QFrame[panel="true"]:hover`; remove deprecated `QLabel[section-header="true"]` alias
- `src/ui/settings_panel.py` — Migrate `_make_section_header` to `variant="standard"`; migrate inline error stylesheet to property; restructure NDI row layout; reflow hotkey buttons side-by-side; reorder Channel Settings card with separator
- `scripts/pre_commit_checks.py` — Add `check_v131_phase1_settings_panel()` function; update `EXPECTED_COLOR_TOKENS` from 46 to 47
- `scripts/verify_critical_fixes.py` — Update `EXPECTED_COLOR_TOKENS` from 46 to 47

## Files Not Touched

- `src/ui/home_panel.py` — Phase 3 scope. Its 43 inline `setStyleSheet()` calls remain untouched.
- `src/ui/theme_designer.py` — Phase 4 scope. Its 40 inline `setStyleSheet()` calls remain.
- `src/utils/icons.py` — Phase 2 scope. Icon factory extension not yet needed.
- `src/core/channel_manager.py` — Outside v1.3.1 operator-panel scope.
- `src/display/*` — Congregation display rendering must not change.
- `src/core/navigator.py` — Outside scope.
- `src/db/db_layer.py` — Outside scope.
- `src/main.py` — No settings panel instantiation changes needed.

---

## Step 0 — Pre-Flight Verification

| Required by Plan | Present in Code | Status |
|---|---|---|
| `settings_panel.py` has exactly 1 inline `setStyleSheet()` call | Line 469: `error_label.setStyleSheet("color: rgba(224,92,75,0.7);")` | ✅ Confirmed |
| `settings_panel.py:244` uses `setProperty("section-header", True)` | Single call site at `_make_section_header` | ✅ Confirmed |
| `_make_section_header` called 5 times across all code paths | Lines 71, 114, 163, 199, 214 | ✅ Confirmed |
| `theme.py:530-532` has `QFrame[panel="true"]:hover` rule | Present in `generate_stylesheet()` | ✅ Confirmed |
| `theme.py:665-667` has `QFrame[card="true"]:hover` rule | Present in `generate_stylesheet()` | ✅ Confirmed |
| `theme.py:482-496` has deprecated `section-header="true"` alias | Present in `generate_stylesheet()` | ✅ Confirmed |
| `theme.py` has no `QLabel[error="true"]` selector | Grep confirms absent | ✅ Confirmed — needs addition |
| `dark_gold.json` colors end with `draft_text` as entry 46 | `draft_text` is last color token | ✅ Confirmed |
| All 10 built-in themes have 46 color tokens (`EXPECTED_COLOR_TOKENS`) | Guard scripts verify this | ✅ Confirmed |
| `QFrame[card="true"]` used in settings_panel.py | All 4 card frames (diagnostics, general, channel, ndi) use `setProperty("card", True)` | ✅ Confirmed |
| Hotkey buttons test_btn + details_btn stacked vertically | Lines 94-109: both added directly to diagnostics_layout | ✅ Confirmed |
| Channel card has designer_btn before per-channel sections | Line 173 (designer_btn) before line 191 (for loop) | ✅ Confirmed |
| NDI row error_label in same HBoxLayout as controls | Line 471: `layout.addWidget(error_label, 1)` — same HBox as controls | ✅ Confirmed |
| `settings_panel.py` has zero `panel="true"` widgets | Grep `panel.*true` returns 0 matches | ✅ Confirmed |
| ThemeCardWidget:hover uses `card_hover_bg`/`card_hover_border` independent of QFrame | theme.py:771-772: separate `ThemeCardWidget:hover` selector | ✅ Confirmed |
| `c()` returns `"#000000"` for missing keys | `self.colors.get(key, "#000000")` at theme.py:110 | ✅ Confirmed |
| QLabel[hint="true"] uses `font-size: 9px` (px not pt) | theme.py:687: `font-size: 9px` | ✅ Confirmed — guides error selector convention |

---

## Step 1 — Add `red_text` token to all 10 built-in theme JSONs

**Insertion point for every theme:** After `red_dim` entry, before `scrollbar` (the next token after `red_dim` in all themes).

**Value derivation:** Each theme's `red_text` is its `red` color at 70% opacity.

| Theme | red value | → | red_text | Insert after `red_dim` (line varies) |
|-------|-----------|---|----------|--------------------------------------|
| dark_gold | `#e05c4b` | → | `rgba(224,92,75,0.7)` | ~line 30 |
| light | `#c94435` | → | `rgba(201,68,53,0.7)` | ~line 30 |
| high_contrast | `#ff4444` | → | `rgba(255,68,68,0.7)` | ~line 30 |
| midnight_blue | `#ef4444` | → | `rgba(239,68,68,0.7)` | ~line 30 |
| forest_green | `#ef4444` | → | `rgba(239,68,68,0.7)` | ~line 30 |
| warm_amber | `#ef4444` | → | `rgba(239,68,68,0.7)` | ~line 30 |
| royal_purple | `#ef4444` | → | `rgba(239,68,68,0.7)` | ~line 30 |
| crimson_red | `#ef4444` | → | `rgba(239,68,68,0.7)` | ~line 30 |
| slate_gray | `#ef4444` | → | `rgba(239,68,68,0.7)` | ~line 30 |
| pastel_calm | `#c62828` | → | `rgba(198,40,40,0.7)` | ~line 30 |

**Code to insert** (after each theme's `red_dim` line, before `scrollbar`):
```json
    "red_text": "rgba(224,92,75,0.7)",
```

---

## Step 2 — Add `QLabel[error="true"]` selector to `theme.py:generate_stylesheet()`

**Insertion point:** After `QLabel[hint="true"]` block (theme.py:684-689), before `QLabel[result="true"]` (theme.py:692).

**Code to add:**
```python
/* ── Error Labels (Phase 1: token-based red_text) ── */
QLabel[error="true"] {{
    color: {c("red_text")};
    background: transparent;
}}
```

**Design rationale:** No `font-size` override — the error label inherits its `QFont("Segoe UI", 9)` (9pt, ≈12px at 96dpi) rather than being overridden to 9px. Error text is operational-alert level ("NDI send failed", "connection dropped") and should read at normal small-label size, not the compressed 9px used for passive hint labels. Color comes from `c("red_text")`. User themes without `red_text` fall back via QSS cascade (parent QWidget color) — not a crash, just degraded coloring. If future audit finds the 9pt→9px mismatch in `QLabel[hint="true"]` is a bug, that fix is scoped separately.

---

## Step 3 — Migrate inline error_label stylesheet to property-based selector

**File:** `settings_panel.py`
**Location:** `_create_ndi_section` method, lines 467-471

**Before:**
```python
        error_label = QLabel("")
        error_label.setFont(QFont("Segoe UI", 9))
        error_label.setStyleSheet("color: rgba(224,92,75,0.7);")
        error_label.setWordWrap(True)
        layout.addWidget(error_label, 1)
```

**After:**
```python
        error_label = QLabel("")
        error_label.setFont(QFont("Segoe UI", 9))
        error_label.setProperty("error", True)
        error_label.setWordWrap(True)
        layout.addWidget(error_label, 1)
```

**Verification:** `grep "setStyleSheet" src/ui/settings_panel.py` returns no results.

---

## Step 4 — Remove `QFrame[card="true"]:hover` rule from theme.py

**File:** `theme.py:generate_stylesheet()`
**Lines to remove:** 665-667

```python
QFrame[card="true"]:hover {{
    border: 1px solid {c("panel_border_hover")};
}}
```

**What remains:** The `QFrame[card="true"]` base rule at lines 658-664 (no border change on hover). The `ThemeCardWidget:hover` selector at lines 770-773 is a separate rule for the theme-designer grid cards and is not affected.

**Rationale per Decision 4:** Hover is a reserved signal for interactivity. Non-interactive settings cards (diagnostics readout, NDI configuration) should not change border on hover, as that falsely suggests clickability.

**Breadcrumb comment:** Replace the removed lines with a single-line breadcrumb to prevent accidental reanimation:
```python
# panel_border_hover intentionally dead after Phase 1 hover removal
```
This comment stays in the code (not scoped for removal). It signals to future developers that the token exists but has no consumer by design.

---

## Step 5 — Remove `QFrame[panel="true"]:hover` rule from theme.py

**File:** `theme.py:generate_stylesheet()`
**Lines to remove:** 530-532

```python
QFrame[panel="true"]:hover {{
    border: 1px solid {c("panel_border_hover")};
}}
```

**Justification (per Deviation 2):** No widget in `settings_panel.py` uses `panel="true"` (0 matches verified). This is a proactive cleanup: the sub-roadmap §Phase 3 explicitly says "the default case is removal" for panel hover. Removing it now prevents cascade issues. The `panel_border_hover` color token becomes unused (see F3 hazard note in Regression Hazards) but remains in theme JSONs for backward compatibility — a future token cleanup pass can remove it.

**Breadcrumb comment:** Replace the removed lines with a single-line breadcrumb (same as Step 4):
```python
# panel_border_hover intentionally dead after Phase 1 hover removal
```
This comment stays in the code (same comment, not duplicated — one instance in the theme.py section near the former hover rules).

---

## Step 6 — Remove deprecated `QLabel[section-header="true"]` alias

**File:** `theme.py:generate_stylesheet()`
**Lines to remove:** 482-496

```python
    # Deprecated alias: section-header="true" renders as compact.
    # Removed in Phase 1 DoD after _make_section_header migration.
    # F9 fix: use .get() with fallback to prevent KeyError on partial dicts.
    compact_spec = theme.typography.get("compact", TYPOGRAPHY_DEFAULTS["compact"])
    typo_rules.append(
        f'QLabel[section-header="true"] {{\n'
        ...
    )
```

**Safety precondition:** Step 7 must complete first — the single call site at `settings_panel.py:244` must be migrated from `setProperty("section-header", True)` to `setProperty("section-header", variant)` before the alias is removed. Otherwise section headers lose all QSS styling.

**In-code guard comment:** Add the following comment above the deprecated alias block in `theme.py:482` to prevent edit-time confusion:
```python
# REMOVE ONLY AFTER _make_section_header migration to variant parameter (Plan Step 7)
```
This comment is removed along with the alias during Step 6 — it must not survive in the final code.

---

## Step 7 — Migrate `_make_section_header` to typography system

**File:** `settings_panel.py`
**Method:** `_make_section_header` (lines 230-247)
**Call sites:** 5 (lines 71, 114, 163, 199, 214)

### 7a — Update `_make_section_header` method signature and body

**Before:**
```python
    def _make_section_header(self, title: str) -> QWidget:
        """Gold dot + uppercase label, wrapped in a QWidget for use with addWidget()."""
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
        label.setProperty("section-header", True)
        header.addWidget(label)
        header.addStretch()
        return container
```

**After:**
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

**Changes:** Added `variant: str = "compact"` parameter; changed `setProperty("section-header", True)` to `setProperty("section-header", variant)`. Default preserves backward compatibility for any callers not passing variant.

### 7b — Update all 5 call sites to pass `variant="standard"`

```python
# Line 71:
content_layout.addWidget(self._make_section_header("Hotkey Diagnostics", variant="standard"))
# Line 114:
content_layout.addWidget(self._make_section_header("General", variant="standard"))
# Line 163:
content_layout.addWidget(self._make_section_header("Channel Settings", variant="standard"))
# Line 199:
content_layout.addWidget(self._make_section_header("NDI Output", variant="standard"))
# Line 214:
content_layout.addWidget(self._make_section_header("NDI Output", variant="standard"))
```

**Why all use `standard`:** The settings panel is a full-width scroll area (32px side margins). All section headers are full-width titles that should dominate their content. The `compact` variant (9px uppercase letterspaced) is reserved for cramped contexts — home panel sidebar, Phase 3.

---

## Step 8 — Restructure Hotkey Diagnostics buttons (side-by-side)

**File:** `settings_panel.py`
**Location:** Lines 93-110

**Before:**
```python
        # Test Hotkeys button
        test_btn = QPushButton("Test Hotkeys")
        test_btn.setFixedHeight(36)
        test_btn.setFont(QFont("Segoe UI", 10))
        test_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        test_btn.setProperty("accent", "green")
        test_btn.clicked.connect(self._test_hotkeys)
        diagnostics_layout.addWidget(test_btn)

        # View Full Details button
        details_btn = QPushButton("View Full Details")
        details_btn.setFixedHeight(36)
        details_btn.setFont(QFont("Segoe UI", 10))
        details_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        details_btn.setProperty("accent", "subtle")
        details_btn.clicked.connect(self._show_full_details)
        diagnostics_layout.addWidget(details_btn)
```

**After:**
```python
        # Button row — side by side
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        test_btn = QPushButton("Test Hotkeys")
        test_btn.setFixedHeight(36)
        test_btn.setFont(QFont("Segoe UI", 10))
        test_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        test_btn.setProperty("accent", "green")
        test_btn.clicked.connect(self._test_hotkeys)
        btn_row.addWidget(test_btn)

        details_btn = QPushButton("View Full Details")
        details_btn.setFixedHeight(36)
        details_btn.setFont(QFont("Segoe UI", 10))
        details_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        details_btn.setProperty("accent", "subtle")
        details_btn.clicked.connect(self._show_full_details)
        btn_row.addWidget(details_btn)

        diagnostics_layout.addLayout(btn_row)
```

**Rationale:** Two action buttons placed horizontally (primary green action left, secondary subtle action right). 8px spacing matches the card's internal spacing. Eliminates the stacked-button vertical waste.

---

## Step 9 — Reorder Channel Settings card (with separator)

**File:** `settings_panel.py`
**Location:** Lines 166-195

**Before:**
```python
            channel_frame = QFrame()
            channel_frame.setProperty("card", True)
            channel_layout = QVBoxLayout(channel_frame)
            channel_layout.setContentsMargins(20, 20, 20, 20)
            channel_layout.setSpacing(12)

            # Theme Designer button — opens the three-panel designer UI
            designer_btn = QPushButton("Open Theme Designer")
            designer_btn.setFixedHeight(36)
            designer_btn.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            designer_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            designer_btn.setProperty("accent", "gold")
            designer_btn.clicked.connect(self.theme_designer_requested.emit)
            channel_layout.addWidget(designer_btn)

            # Hint label for the designer button
            designer_hint = QLabel(
                "Edit themes used by Main and Alt channels. "
                "Changes apply only after Save and Apply."
            )
            designer_hint.setFont(QFont("Segoe UI", 9))
            designer_hint.setProperty("hint", True)
            designer_hint.setWordWrap(True)
            channel_layout.addWidget(designer_hint)

            for ch_name, ch_label in [("main", "Main Channel"), ("alt", "Alt Channel")]:
                section = self._create_channel_section(ch_name, ch_label)
                channel_layout.addWidget(section)

            content_layout.addWidget(channel_frame)
```

**After:**
```python
            channel_frame = QFrame()
            channel_frame.setProperty("card", True)
            channel_layout = QVBoxLayout(channel_frame)
            channel_layout.setContentsMargins(20, 20, 20, 20)
            channel_layout.setSpacing(12)

            for ch_name, ch_label in [("main", "Main Channel"), ("alt", "Alt Channel")]:
                section = self._create_channel_section(ch_name, ch_label)
                channel_layout.addWidget(section)

            # Separator before secondary action (Deviation 3: visual group boundary)
            channel_layout.addWidget(self._make_separator())

            # Theme Designer button — demoted to secondary action
            designer_btn = QPushButton("Open Theme Designer")
            designer_btn.setFixedHeight(36)
            designer_btn.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            designer_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            designer_btn.setProperty("accent", "gold")
            designer_btn.clicked.connect(self.theme_designer_requested.emit)
            channel_layout.addWidget(designer_btn)

            # Hint label for the designer button
            designer_hint = QLabel(
                "Edit themes used by Main and Alt channels. "
                "Changes apply only after Save and Apply."
            )
            designer_hint.setFont(QFont("Segoe UI", 9))
            designer_hint.setProperty("hint", True)
            designer_hint.setWordWrap(True)
            channel_layout.addWidget(designer_hint)

            content_layout.addWidget(channel_frame)
```

**Rationale (Deviation 3):** Two visual groups — per-channel controls (primary) above separator, designer link (secondary) below. The separator uses the existing `self._make_separator()` method — same 1px gold-dim line used between sections, now reused inside the card to delineate primary controls from the secondary designer action.

---

## Step 10 — Restructure NDI row layout for reflow

**File:** `settings_panel.py`
**Method:** `_create_ndi_section` (lines 428-481)

**Before:**
```python
    def _create_ndi_section(self, channel_name: str, label: str):
        """Create NDI settings controls for a single channel."""
        from settings import SettingsManager

        section = QFrame()
        layout = QHBoxLayout(section)
        layout.setContentsMargins(0, 4, 0, 4)

        name_label = QLabel(label)
        name_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        name_label.setFixedWidth(120)
        layout.addWidget(name_label)

        ch_settings = SettingsManager().get_channel_settings(channel_name)
        enable_cb = QCheckBox("Enabled")
        enable_cb.setChecked(ch_settings.ndi_enabled)
        enable_cb.setFont(QFont("Segoe UI", 9))
        enable_cb.toggled.connect(lambda checked, n=channel_name: self._on_ndi_enabled_toggled(n, checked))
        layout.addWidget(enable_cb)

        source_input = QLineEdit()
        source_input.setText(ch_settings.ndi_source_name)
        source_input.setPlaceholderText("NDI source name")
        source_input.setFixedWidth(180)
        source_input.setFixedHeight(28)
        source_input.setFont(QFont("Segoe UI", 9))
        source_input.editingFinished.connect(lambda n=channel_name, w=source_input: self._on_ndi_source_name_changed(n, w.text()))
        layout.addWidget(source_input)

        fps_label = QLabel("-- fps")
        fps_label.setFont(QFont("Segoe UI", 9))
        fps_label.setProperty("hint", True)
        fps_label.setFixedWidth(50)
        layout.addWidget(fps_label)

        error_label = QLabel("")
        error_label.setFont(QFont("Segoe UI", 9))
        error_label.setStyleSheet("color: rgba(224,92,75,0.7);")
        error_label.setWordWrap(True)
        layout.addWidget(error_label, 1)

        sender = self.ndi_manager.get_sender(channel_name) if self.ndi_manager else None
        if sender is not None:
            sender.frame_sent.connect(lambda _ch, _fps, lbl=fps_label: lbl.setText(f"{_fps} fps"))
            sender.sender_error.connect(lambda _ch, err, lbl=error_label: lbl.setText(err))
            sender.frame_sent.connect(lambda _ch, _fps, lbl=error_label: lbl.setText(""))

        return section
```

**After:**
```python
    def _create_ndi_section(self, channel_name: str, label: str):
        """Create NDI settings controls for a single channel."""
        from settings import SettingsManager

        section = QFrame()
        outer_layout = QVBoxLayout(section)
        outer_layout.setContentsMargins(0, 4, 0, 4)
        outer_layout.setSpacing(4)

        # Top row: controls
        controls_row = QHBoxLayout()
        controls_row.setSpacing(8)

        name_label = QLabel(label)
        name_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        name_label.setFixedWidth(120)
        controls_row.addWidget(name_label)

        ch_settings = SettingsManager().get_channel_settings(channel_name)
        enable_cb = QCheckBox("Enabled")
        enable_cb.setChecked(ch_settings.ndi_enabled)
        enable_cb.setFont(QFont("Segoe UI", 9))
        enable_cb.toggled.connect(lambda checked, n=channel_name: self._on_ndi_enabled_toggled(n, checked))
        controls_row.addWidget(enable_cb)

        source_input = QLineEdit()
        source_input.setText(ch_settings.ndi_source_name)
        source_input.setPlaceholderText("NDI source name")
        source_input.setFixedWidth(180)
        source_input.setFixedHeight(28)
        source_input.setFont(QFont("Segoe UI", 9))
        source_input.editingFinished.connect(lambda n=channel_name, w=source_input: self._on_ndi_source_name_changed(n, w.text()))
        controls_row.addWidget(source_input)

        fps_label = QLabel("-- fps")
        fps_label.setFont(QFont("Segoe UI", 9))
        fps_label.setProperty("hint", True)
        fps_label.setFixedWidth(50)
        controls_row.addWidget(fps_label)

        outer_layout.addLayout(controls_row)

        # Bottom row: error text (wraps independently — eliminates 480px clip)
        error_label = QLabel("")
        error_label.setFont(QFont("Segoe UI", 9))
        error_label.setProperty("error", True)
        error_label.setWordWrap(True)
        outer_layout.addWidget(error_label)

        # Wire live FPS/error updates from sender signals
        sender = self.ndi_manager.get_sender(channel_name) if self.ndi_manager else None
        if sender is not None:
            sender.frame_sent.connect(lambda _ch, _fps, lbl=fps_label: lbl.setText(f"{_fps} fps"))
            sender.sender_error.connect(lambda _ch, err, lbl=error_label: lbl.setText(err))
            sender.frame_sent.connect(lambda _ch, _fps, lbl=error_label: lbl.setText(""))

        return section
```

**Key structural change:** The error label moves to its own row below the controls in a VBoxLayout. When the window narrows to 480px, the controls row can shrink without clipping the error text. Signal closures capture `error_label` by object reference — moving it to a different layout position does not affect signal delivery.

---

## Step 11 — Update guard scripts

### 11a — `pre_commit_checks.py`

Update `EXPECTED_COLOR_TOKENS` in `check_phase4_preset_library_polish()`:
```python
    EXPECTED_COLOR_TOKENS = 47   # Was 46; +1 for red_text (Phase 1)
```

Add new function `check_v131_phase1_settings_panel()`:
```python
def check_v131_phase1_settings_panel():
    """Verify Phase 1 settings panel polish closeout."""
    errors = []

    THEMES_DIR = SRC_UTILS / 'themes'
    EXPECTED_TOKEN_COUNT = 47

    # 1. All 10 built-in themes have red_text token
    for builtin_id in BUILTIN_THEME_IDS:
        path = THEMES_DIR / f"{builtin_id}.json"
        if not path.exists():
            errors.append(f"CRITICAL: Built-in theme {builtin_id}.json missing")
            continue
        with open(path, encoding='utf-8') as f:
            data = json.load(f)
        if "red_text" not in data.get("colors", {}):
            errors.append(f"CRITICAL: {builtin_id}.json missing red_text token")
        if len(data.get("colors", {})) != EXPECTED_TOKEN_COUNT:
            errors.append(f"CRITICAL: {builtin_id}.json has {len(data['colors'])} tokens, expected {EXPECTED_TOKEN_COUNT}")

    # 2. theme.py has error selector and no hover rules or deprecated alias
    theme_path = SRC_UTILS / 'theme.py'
    with open(theme_path, encoding='utf-8') as f:
        theme_content = f.read()
    if 'QLabel[error="true"]' not in theme_content:
        errors.append('CRITICAL: theme.py missing QLabel[error="true"] selector')
    if 'QFrame[card="true"]:hover' in theme_content:
        errors.append("CRITICAL: theme.py still has card hover rule (should be removed)")
    if 'QFrame[panel="true"]:hover' in theme_content:
        errors.append("CRITICAL: theme.py still has panel hover rule (should be removed)")
    if 'section-header="true"' in theme_content:
        errors.append("CRITICAL: theme.py still has deprecated section-header=true alias (should be removed)")

    # 3. settings_panel.py has zero inline setStyleSheet() calls
    sp_path = SRC_UI / 'settings_panel.py'
    with open(sp_path, encoding='utf-8') as f:
        sp_content = f.read()
    set_style_count = sp_content.count("setStyleSheet")
    if set_style_count > 0:
        errors.append(f"CRITICAL: settings_panel.py has {set_style_count} inline setStyleSheet() calls, expected 0")

    # 4. _make_section_header uses variant parameter
    if 'variant: str = "compact"' not in sp_content:
        errors.append("CRITICAL: _make_section_header missing variant parameter")
    call_sites = [line for line in sp_content.split('\n') if '_make_section_header(' in line]
    standard_sites = [l for l in call_sites if 'variant="standard"' in l]
    if len(standard_sites) < 5:
        errors.append(f"CRITICAL: Only {len(standard_sites)}/5 _make_section_header call sites use variant='standard'")

    return errors
```

Register in `__main__` between the Phase 0 check and Preset Library check:
```python
    print("Checking v1.3.1 Phase 1 settings panel polish...")
    all_errors.extend(check_v131_phase1_settings_panel())
```

### 11b — `verify_critical_fixes.py`

Update `EXPECTED_COLOR_TOKENS`:
```python
    EXPECTED_COLOR_TOKENS = 47   # Was 46; +1 for red_text
```

---

## Regression Hazards

| Hazard | Risk | Mitigation |
|--------|------|------------|
| **F1: Deprecated alias removed before all call sites migrated** — If Step 7 (section-header migration) is done AFTER Step 6 (alias removal), section headers lose styling and render as plain black text. | Medium impact — broken headers visually obvious, caught immediately on app launch. | **Ordering enforced:** Step 7 must precede Step 6. Steps are ordered correctly in this plan. |
| **F2: `red_text` missing in user-created themes** — Theme switch to a user theme without `red_text` causes error text to render as `#000000` (QSS cascade default). | Low impact — degraded rendering, not a crash. `c("red_text")` returns `"#000000"` for missing keys. | QLabel[error="true"] inherits from parent QWidget color via cascade if `red_text` token missing. Fallback rendering is readable, just not error-colored. |
| **F3: `panel_border_hover` becomes dead token** — After Steps 4+5 remove both card:hover and panel:hover, `panel_border_hover` has zero QSS consumers. Token remains in all 10 theme JSONs but is never referenced. | No runtime impact — unused tokens don't crash or degrade performance. Produces theme bloat (+1 token per theme, ~16 bytes each). | Acceptable. Dead tokens in theme data are harmless at current scale (47 tokens vs 46). A future token audit pass can remove unreferenced tokens across all themes. |
| **F4: `QFrame[card="true"]:hover` removal does not affect ThemeCardWidget** — ThemeCardWidget has its own hover rules (`ThemeCardWidget:hover` at lines 770-773) that are independent selectors. | No risk — separate selectors, no cascade conflict. | Pre-flight verified: `ThemeCardWidget:hover` uses `card_hover_bg`/`card_hover_border` from the same theme tokens, but the selector is `ThemeCardWidget:hover`, not `QFrame[card="true"]:hover`. |
| **F5: NDI row reflow changes widget hierarchy** — Moving error_label from HBox to its own VBox layer changes parent-child layout. Signal connections via `lbl=error_label` closures capture the label object reference, not its layout position. | Low risk — PyQt closures capture object references. | Verified by code analysis: `sender.frame_sent.connect(lambda _ch, _fps, lbl=error_label: lbl.setText(...))` — the `lbl` default argument binds the label object at closure creation time. Moving it to a different layout doesn't affect signal delivery. |
| **F6: (RESOLVED) 9pt → 9px font-size unit difference** — Initial plan included `font-size: 9px` in the error selector, which would shrink error labels ~25% vs standard labels. | N/A — resolved. | Audit Issue 1 removed `font-size` from Step 2. Error labels now inherit `QFont("Segoe UI", 9)` (9pt, ≈12px at 96dpi) — no size override. |
| **F7: Inline separator inside card (Deviation 3)** — Creating a `QFrame(separator=True)` inside the channel card is a design choice not vetted in the sub-roadmap ADR. Might cause visual inconsistency if the separator style diverges from the section-level separators. | Low risk — the separator uses the same QSS selector (`separator="true"`) as section-level separators, guaranteeing visual consistency. The 1px gold-dim line renders identically regardless of layout depth. | Documented as Deviation 3. No QSS changes needed — the selector already exists. |
| **F8: Guard scripts fail due to token count mismatch** — If Step 1 (add red_text to 10 JSONs) is committed before Step 11b (update `EXPECTED_COLOR_TOKENS` from 46→47), CI fails because the token count check expects 46 but finds 47. | Medium impact — guard scripts block CI but don't affect runtime. | **Batch Steps 1+11 in a single commit.** Both guard scripts expect 47 tokens; the theme JSONs and the constants must agree at every commit boundary. If separate commits are necessary, commit Step 11b FIRST (set EXPECTED_COLOR_TOKENS to 47 while themes still have 46 tokens — a < actual count passes the `!=` check and produces warnings but not CI failures), then Step 1. The reverse order (Step 1 first) is what breaks. |

---

## Definition of Done

- [ ] All 10 built-in theme JSONs have `red_text` token at 70% opacity of their `red` value, inserted after `red_dim`. Token count increased from 46 to 47 in all themes.
- [ ] `QLabel[error="true"]` selector exists in `theme.py:generate_stylesheet()` with `color: {c("red_text")}`, `background: transparent`.
- [ ] `settings_panel.py` has **zero** inline `setStyleSheet()` calls. The last remaining call (line 469) migrated to `setProperty("error", True)`.
- [ ] `QFrame[card="true"]:hover` rule removed from `theme.py`. ThemeCardWidget:hover is unaffected.
- [ ] `QFrame[panel="true"]:hover` rule removed from `theme.py`.
- [ ] Deprecated `QLabel[section-header="true"]` alias removed from `theme.py` (after Step 7 migration).
- [ ] `_make_section_header()` accepts `variant: str = "compact"` parameter. All 5 settings panel call sites pass `variant="standard"`.
- [ ] Settings panel section headers render at `standard` size (13px Bold), visibly larger than internal content.
- [ ] Hotkey Diagnostics buttons (Test Hotkeys, View Full Details) placed side-by-side in a horizontal row.
- [ ] Channel Settings card: per-channel controls first, then separator, then Theme Designer button + hint below.
- [ ] NDI row: two-row layout (controls top, error label bottom independently wrapping).
- [ ] `EXPECTED_COLOR_TOKENS` updated from 46 to 47 in both `pre_commit_checks.py` and `verify_critical_fixes.py`.
- [ ] `check_v131_phase1_settings_panel()` added to `pre_commit_checks.py` and registered in `__main__`.
- [ ] All 10 themes render the settings panel without visual regression in unchanged areas.
- [ ] Cards do not respond to hover (no border change on hover).
- [ ] Error label renders in red_text color matching the active theme.
- [ ] `scripts/pre_commit_checks.py` passes with 0 errors.
- [ ] `scripts/verify_critical_fixes.py` passes with 0 errors.

---

## Status Log

| Date | Note |
|------|------|
| May 25, 2026 | Phase 1 implementation plan drafted. 3 deviations documented (10 themes, panel:hover removal, separator inside card). 11 execution steps. Audit findings F1–F5 addressed: F1 (dead ndi-section removed), F2 (Deviation 3 added), F3 (hazard note), F4 (justification strengthened), F5 (hazard note). |
| May 25, 2026 | Second audit (Audit #2) found 6 issues. All 6 verified and applied: (1) font-size:9px removed from error selector + design rationale updated + DoD item fixed; (2) guard threshold <4→<5; (3) F8 hazard updated with commit-order guidance; (4) in-code guard comment added to Step 6; (5) breadcrumb comments added to Steps 4+5; (6) Deviation 3 inline QFrame replaced with self._make_separator() + rationale updated. F6 hazard marked RESOLVED. |

---

*This document is part of the VerseFlow v1.3.1 implementation plan hierarchy. Parent: [v1.3.1 UI Polish & Consistency — Sub-Roadmap.md](./v1.3.1%20UI%20Polish%20%26%20Consistency%20%E2%80%94%20Sub-Roadmap.md). Predecessor: [Phase 0 — Typography System Foundation — Implementation Plan.md](./Phase%200%20%E2%80%94%20Typography%20System%20Foundation%20%E2%80%94%20Implementation%20Plan.md).*
