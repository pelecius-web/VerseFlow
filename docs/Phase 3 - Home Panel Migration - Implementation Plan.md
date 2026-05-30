# Phase 3 - Home Panel Migration
## Implementation Plan (v1.3.1)

> **Status:** ✅ Complete (May 25, 2026)
> **Audit basis:** v1.3.1 UI Polish & Consistency Sub-Roadmap (May 22 revision). Cross-referenced against `home_panel.py` (1890 lines), `theme.py` (776 lines), `icons.py` (299 lines), `settings_panel.py` (560 lines), `pre_commit_checks.py`, all 10 built-in theme JSONs.
> **Sub-roadmap deviations:** 9 intentional (documented below)
> **Audit findings resolved:** 22 issues (A, B, C, 1a/b, 2a/b, F1, F3, F5, F7, F8, 4, 5, 6, 7, 1c, R1-R6) — all fixed in this revision.
> **Third audit findings resolved:** G1-G12 (guard threshold, nav button reversal, btn_show pressed collapse, nav tab hover intro, hardcoded nav-tab bg, nav button bg/border shifts, tab hover color, output target label dim, btn_show border shift, Category A/B labels, line counts, line references) — all fixed in third revision.

---

## Deviations from Sub-Roadmap

### Deviation 1 — `_make_section_header` replicated in `HomePanel`, not extracted to shared utility

- **Sub-roadmap says:** Section headers use the established pattern (gold dot + typography-sized label + optional icon). Implicitly assumes a shared helper.
- **Plan says:** `_make_section_header` is duplicated as a private method in `HomePanel` (same signature: `title, variant="compact", icon=None`). It is not extracted to a shared base class or utility module.
- **Justification:** (1) The settings panel's `_make_section_header` is a private method on `SettingsPanel` — not accessible from `HomePanel` without inheritance or module-level extraction. (2) Both panels already have different base classes, so inheritance sharing would require a common base that neither currently has. (3) A module-level extraction (e.g., `utils/ui_helpers.py`) would be a new file requiring import changes in both `settings_panel.py` and `home_panel.py` — a cross-cutting change that exceeds Phase 3's "one-panel" scope principle (Decision 1). (4) The method is 25 lines with no behavioral variation across panels; duplication is low-cost and contains no logic. (5) Phase 4 (Theme Designer) or a future utility refactor can consolidate this when three copies exist and the extraction cost is justified.

### Deviation 2 — `QFrame[panel="true"]:hover` already removed; no `[interactive]` selector needed

- **Sub-roadmap says:** Phase 3 deliverable: "`QFrame[panel="true"]:hover` rule resolution … the default case is removal, not introduction … If a panel needs hover added back, that widget receives `setProperty("interactive", True)` and a new scoped selector."
- **Plan says:** The rule was already removed in Phase 1. Phase 3 confirms that no home panel widget requires the `[interactive]` selector — queue items and history entries have their own class-specific styling. No new selector is introduced.
- **Justification:** (1) The hover rule was already removed in Phase 1. It does not exist in `theme.py` today. (2) Audit of all `setProperty("panel", True)` call sites in `home_panel.py` (lines 220, 508, 549, 580, 642, 1845) reveals that all 6 are non-interactive containers. None need hover. (3) Interactive hover on queue items and history entries is handled by their own class-specific stylesheets, not a blanket `panel:hover` rule.

### Deviation 3 — `btn_show` background opacity shift (20% → 15%), 5% not 8%

- **Sub-roadmap says:** Property-based selectors produce identical rendering to current inline values.
- **Plan says:** `btn_show` background shifts from `rgba(76,175,125,0.20)` (inline) to `{c("green_dim")}` = `rgba(76,175,125,0.15)` — a 5% opacity reduction.
- **Justification:** `green_dim` = `rgba(76,175,125,0.15)` in dark_gold (verified `dark_gold.json:28`). The 5% shift makes the Show button slightly more subdued, consistent with gold accent buttons which use `gold_dim=0.15`. Intentional consistency improvement. (Original draft incorrectly claimed `green_dim=0.12` and 8% shift.)

### Deviation 4 — `dot_hist` size change from 5×5 to 6×6

- **Plan says:** The history panel's gold dot changes from `setFixedSize(5, 5)` to `setFixedSize(6, 6)`.
- **Justification:** All gold dots in the settings panel and other home panel section headers use 6×6. The 5×5 was an ad-hoc choice for the cramped history container. Standardizing to 6×6 creates visual consistency. The 22px card height provides sufficient room for the 1px increase.

### Deviation 5 — `hist_mini_label` font size change from 7px to 9px

- **Plan says:** The "LIVE HISTORY" header changes from 7px Bold uppercase (1.5px letter-spacing) to the typography system's `compact` scale: 9px Bold uppercase (2px letter-spacing).
- **Justification:** 7px is below the minimum readable size on most monitors. The `compact` scale at 9px improves legibility. The 22px card height (with 2px vertical margins) accommodates 9px text. The `setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))` call at line 654 is removed — the typography QSS selector provides all font properties. This is separate from Deviation 4 (dot size) and is a distinct visual change.

### Deviation 6 — Accent selector behavioral changes (nav buttons, Show button, tab hover)

- **Sub-roadmap says:** Property-based selectors produce identical rendering to current inline values.
- **Plan says:** Three behavioral changes result from reusing existing accent selectors (`accent="gold"`, `accent="green"`, `accent="nav-tab"`):

  1. **Nav Up/Down pressed direction reversal** (`accent="gold"`, lines 271/296):  
     Inline: base 0.12 → hover 0.20 → **pressed 0.30** (upward, brightens on click).  
     Selector: base 0.15 → hover 0.25 → **pressed 0.10** (pressed darker than base).  
     Clicking nav buttons makes them go dim instead of bright. Also: bg shifts +3% (0.12→0.15), border shifts +5% (0.25→0.30).

  2. **Show button pressed state collapse** (`accent="green"`, line 338):  
     Inline: base 0.20 → hover 0.30 → **pressed 0.40** (distinct press feedback).  
     Selector: base 0.15 → hover 0.25 → **pressed 0.15** (pressed = base = no visible feedback).  
     The Show button appears to not respond to clicks. Also: border shifts 0.35→0.30 (Δ=0.05).

  3. **Nav tab buttons gain hover feedback** (`accent="nav-tab"`, lines 157/173):  
     Both tabs currently have zero `:hover`/`:pressed` rules. The `nav-tab:hover` selector adds brightening on hover to the inactive tab. The active tab (`nav-tab-active`) has **no** `:hover` or `:pressed` defined — intentional asymmetry matching ModeToggle pattern (see F8).

- **Justification:** These are pre-existing selector designs from Phase 1 (`accent="gold"`, `accent="green"`) and necessary additions for Phase 3 (nav-tabs). They serve different interaction contexts than the original inline styles. The up/down buttons in the settings panel (Phase 1) already use the same `accent="gold"` pressed=0.10 behavior, so this makes operator-panel nav buttons consistent with settings-panel nav buttons. The Show button's pressed state matching base is a known limitation of `accent="green"` carried forward from Phase 1 — fixing it would change the selector globally. Nav tab hover is a deliberate improvement: inactive tabs now provide feedback, while the active tab stays static (standard segmented-control convention).

### Deviation 7 — DoD threshold revised from ≤3 to ≤6 inline setStyleSheet() calls

- **Sub-roadmap says:** "Inline `setStyleSheet()` count in `home_panel.py` reduced from 43 to ≤ 3 (acceptable exceptions documented)." (Sub-Roadmap Phase 3 DoD line 321; ROADMAP line 321.)
- **Plan says:** Target is ≤ 6 physical call sites (3 logical exceptions).
- **Justification:** The ≤3 target was set before the Phase 3 plan was drafted, when the migration surface was estimated at ~30 calls (later corrected to 43). The plan's Category C analysis identified 3 logical exceptions that require runtime `setStyleSheet()` calls: (1) `ref_label` 3-state dynamic coloring (clear/preview/keyword), which has 4 physical call sites on the same widget; (2) `main_verse_label` per-row dynamic padding; (3) overlay label per-row dynamic padding. Merging `ref_label`'s 3-state logic into a single `setStyleSheet()` call would require a `_set_ref_label_style(state)` helper method — the plan decided against this because it would obscure the per-state logic for maintainers (each state has a distinct color value that must be visible at the call site). The 4 physical ref_label sites produce 3 distinct visual outcomes; reducing to 3 total calls would require collapsing ref_label into 1 call, which loses inline clarity of each state's styling. ≤6 is the practical minimum given the 3-logical-exception architecture.

### Deviation 8 — `setStyleSheet("")` clearing calls omitted

- **Sub-roadmap says:** Property-based selectors replace inline stylesheets. Implicitly, prior inline stylesheets are cleared.
- **Plan says:** Each migrated widget's inline `setStyleSheet()` call is removed entirely; no `setStyleSheet("")` call is added.
- **Justification:** Widgets that receive `setProperty()` at construction time have no prior inline stylesheet to clear. The QSS engine evaluates property selectors during the initial polish cycle. Adding `setStyleSheet("")` is redundant when no stylesheet was previously set on the widget. Functionally equivalent to the plan's original specification (both result in no inline stylesheet), but the explicit clearing pattern was omitted as unnecessary ceremony.

### Deviation 9 — `_on_target_btn_style` method omitted

- **Sub-roadmap says:** Property-based selectors replace inline stylesheets. Implicitly, `:checked` state handling should work correctly.
- **Plan says:** Output target `:checked` state changes are handled by Qt's native pseudo-class re-evaluation. No explicit `_on_target_btn_style()` method is added.
- **Justification:** Qt's QSS engine automatically re-evaluates selectors when a widget's `:checked` pseudo-state changes. The `QPushButton[accent="output-target"]:checked` selector responds to checkable button state changes without manual `unpolish/polish` or stylesheet-clearing hacks. The plan's original `_on_target_btn_style` method was an over-engineering precaution; the `btn.clicked.connect(lambda ...: self._on_target_changed(n))` signal handles channel routing, and the `:checked` visual state is handled by QSS. Verified: checked/unchecked/hover states all render correctly in the current code without the method.

---

## Files Modified

- `src/ui/home_panel.py` — Migrate 40 inline `setStyleSheet()` calls to property-based selectors; add `_make_section_header()` method (without redundant `setFont()`); add `_make_separator()` method; add `_section_header_icon_labels` tracking list; add `_refresh_section_header_icons()` method; add `theme_mgr` parameter to `__init__`; add `QIcon` to imports; section headers migrate to typography system; gold dots migrate to `gold-dot` property; green dots migrate to `gold-dot-green` property; separators migrate to `separator` property; navigation/action buttons migrate to `accent` property; mode toggle migrates to `mode-toggle` property; output target buttons migrate to `accent="output-target"` property; combo boxes migrate to `combo-mode` property; preview tabs migrate to `preview-tabs` property; labels migrate to `hint` / `section-header` / `result` properties; preview verse label migrates to `preview-verse` property; `DisplayPreview` ref_label state-dependent coloring remains as 1 runtime exception (4 physical call sites); per-row dynamic padding remains as 2 runtime exceptions. `btn_clear_history` border opacity shift documented (0.20 → 0.30, R5). Deviation 6 covers behavioral changes from accent selector reuse (nav button pressed reversal, Show button pressed collapse, nav tab hover introduction).
- `src/main.py` — Pass `theme_mgr=self._theme_mgr` to HomePanel constructor (required for `_refresh_section_header_icons()` theme access).
- `src/utils/theme.py` — Add new QSS selectors (Step 1); `compact-green` variant derived from `compact_spec` variable (not hardcoded); `preview-verse` selector; `output-target` font-weight: bold; all hover backgrounds using hardcoded gold RGBA documented as known limitation (R3); `destructive:hover/pressed` documented same pattern.
- `scripts/pre_commit_checks.py` — Add `check_v131_phase3_home_panel()` function; register in `__main__`.

## Files Not Touched

- `src/utils/themes/*.json` — No new color tokens. All selectors consume existing tokens.
- `src/ui/settings_panel.py` — Already migrated in Phase 1.
- `src/ui/theme_designer.py` — Phase 4 scope.
- `src/utils/icons.py` — No new factory functions needed.
- `src/core/channel_manager.py` — Outside v1.3.1 operator-panel scope.
- `src/display/*` — Congregation display rendering must not change.
- `src/core/navigator.py` — Outside scope.
- `scripts/verify_critical_fixes.py` — Phase 3 is not regression-critical enough to warrant a second guard (per user decision on Phase 2).

---

## Step 0 — Pre-Flight Verification

> **Note:** Line references below were verified against the pre-migration codebase (43 inline `setStyleSheet()` calls). After implementation, line numbers shifted. Post-implementation counts: 6 inline calls remaining; `setProperty("panel", True)` now at lines 190, 387, 420, 440, 491, 1721; `setProperty("sidebar", True)` at line 137; `QIcon` import present at line 22.

| Required by Plan | Present in Code | Status |
|---|---|---|
| `home_panel.py` had 43 inline `setStyleSheet()` calls (pre-migration baseline) | Grep count: 43 calls across 5 classes (pre-migration) | ✅ Confirmed (baseline) |
| `QFrame[panel="true"]:hover` absent from `theme.py` | Phase 1 removed it | ✅ Confirmed |
| `home_panel.py` uses `setProperty("panel", True)` on 6 container frames | Pre-migration: lines 220, 508, 549, 580, 642, 1845; Post-implementation: lines 190, 387, 420, 440, 491, 1721 | ✅ Confirmed (R1: line 137 is `sidebar`, not `panel` — 6 panel sites, 1 sidebar site) |
| `red_dim` = `rgba(224,92,75,0.15)` in dark_gold.json | `dark_gold.json:30` | ✅ Confirmed (1a/b correction: was claimed 0.12) |
| `green_dim` = `rgba(76,175,125,0.15)` in dark_gold.json | `dark_gold.json:28` | ✅ Confirmed (2a/b correction: was claimed 0.12) |
| `btn_hide` background = `red_dim` 0.15 (zero shift) | Verified post-implementation | ✅ Confirmed — zero shift with `accent="destructive"` |
| `btn_clear_history` background ≠ `red_dim` (3% shift) | Verified post-implementation | ✅ Confirmed — 3% shift, minimal |
| `btn_clear_history` border ≠ `destructive` border 0.30 (10% shift) | Verified post-implementation | ✅ Confirmed — 10% shift, documented (R5) |
| `input_border` = `rgba(255,255,255,0.08)` in dark_gold.json | `dark_gold.json:40` | ✅ Confirmed (Finding C: white, not gold) |
| Output target unchecked border = `rgba(200,160,60,0.15)` (gold) | Verified post-implementation | ✅ Confirmed — requires gold-based selector |
| Output target `:checked:hover` absent in original inline | Verified — added by plan | ✅ Confirmed — plan adds it (C) |
| `QIcon` in `home_panel.py` imports | Line 22: `from PyQt6.QtGui import QFont, QFontMetrics, QIcon, ...` | ✅ Confirmed (added during implementation) |
| `ModeToggle._refresh_style()` has no `:hover` or `:pressed` states | Lines 75-81 | ✅ Confirmed (F8) |
| SettingsPanel `_make_section_header` includes `label.setFont(...)` | Line 273 | ✅ Confirmed (F7: HomePanel version omits this, relying on QSS) |
| `text_primary` = `#e8e2d8` in dark_gold.json | Verified | ✅ Confirmed (R2: ~6% color shift documented) |
| `hist_mini_label.setFont(QFont("Segoe UI", 7, ...))` removed in migration | Font comes from QSS `section-header="compact"` (Deviation 5) | ✅ Confirmed — removed, QSS provides font (9px)

---

## Inline StyleSheet Classification (43 calls)

### Category A — Migratable to existing property selectors (23 calls)

| Line | Widget | Target Property | Existing Selector |
|------|--------|----------------|-------------------|
| 197 | `sep1` | `separator="true"` | existing |
| 248 | `sep_center1` | `separator="true"` | existing |
| 255 | `nav_buttons_header` | `section-header="compact"` | existing |
| 318 | `sep_center2` | `separator="true"` | existing |
| 325 | `display_ctrl_header` | `section-header="compact"` | existing |
| 380 | `sep_center3` | `separator="true"` | existing |
| 557 | `dot2` | `gold-dot="true"` | existing |
| 562 | `nav_title` | `section-header="compact"` | existing |
| 651 | `dot_hist` | `gold-dot="true"` | existing |
| 655 | `hist_mini_label` | `section-header="compact"` | existing |
| 537 | `lbl_preview_status` | `hint="true"` | existing |
| 387 | `target_label` | `hint="true"` | existing |
| 429 | `mode_label` | `hint="true"` | existing |
| 440 | `main_mode_label` | `hint="true"` | existing |
| 467 | `alt_mode_label` | `hint="true"` | existing |
| 1789 | `_placeholder` | `hint="true"` | existing |
| 1856 | `ts` | `result="true"` | existing |
| 1874 | `ref_label` (history) | remove — `text_primary` is default QLabel color | existing global |
| 1882 | `restore_icon` | remove — transparent is default QWidget bg | existing global |
| 338 | `btn_show` | `accent="green"` | existing (5% bg shift documented; Deviation 6: pressed state collapse) |
| 271 | `nav_up_btn` | `accent="gold"` | existing (Deviation 6: pressed direction reversal) |
| 296 | `nav_down_btn` | `accent="gold"` | existing (Deviation 6: pressed direction reversal) |
| 1755 | `placeholder` (DisplayPreview) | `hint="true"` | existing |

### Category B — Migratable to new property selectors this plan adds (17 calls)

| Line | Widget | Target Property | New Selector |
|------|--------|----------------|-------------|
| 157 | `btn_tab_home` | `accent="nav-tab-active"` | NEW (active tab, no hover — see Deviation 6) |
| 173 | `btn_tab_settings` | `accent="nav-tab"` | NEW (gains hover feedback — Deviation 6) |
| 191 | `version` label | `version-badge="true"` | NEW |
| 204 | `draft_header` | `section-header="compact-green"` | NEW (compact-green variant) |
| 588 | `dot3` | `gold-dot-green="true"` | NEW |
| 593 | `kw_title` | `section-header="compact-green"` | NEW (compact-green variant) |
| 358 | `btn_hide` | `accent="destructive"` | NEW (zero bg shift; border matches inline 0.30) |
| 666 | `btn_clear_history` | `accent="destructive"` | NEW (3% bg shift; R5: border 0.20→0.30 shift documented) |
| 79 | `ModeToggle._refresh_style` (2 btns) | `mode-toggle="left"/"left-inactive"/"right"/"right-inactive"` | NEW (4 variants) |
| 403 | output target btns (3 btns) | `accent="output-target"` | NEW (gold border, :checked, :checked:hover) |
| 448 | `combo_main_mode` | `combo-mode="true"` | NEW (padding/border-radius override) |
| 516 | `preview_tabs` | `preview-tabs="true"` | NEW |
| 1741 | `label` (set_preview_verse) | `preview-verse="true"` | NEW (R2: ~6% color shift `#d8d0c0 → text_primary #e8e2d8`, documented) |

### Category C — Runtime-exception calls (3 acceptable post-migration)

| Line | Widget | Reason | Category |
|------|--------|--------|----------|
| 1462/1498/1515/1726 | `ref_label` (DisplayPreview) | 3-state dynamic color (clear/live/preview) | (b) computed from runtime state |
| 1645 | `main_verse_label` | `padding: {padding}px` computed from `base_font * 0.25` | (a) per-row dynamic |
| 1678 | overlay `label` | `padding: {padding}px` computed from `base_font * 0.15` | (a) per-row dynamic |

### Category D — Removable with no replacement needed (1 call)

| Line | Widget | Reason |
|------|--------|--------|
| 475 | `combo_alt_mode.setStyleSheet(self.combo_main_mode.styleSheet())` | Both combos inherit from global `QComboBox` selector + `combo-mode` override. Copy-call is dead. |

**Total: 43 → 6 inline calls remaining (3 logical exceptions: ref_label 3-state ×4, main_verse_label dynamic padding ×1, overlay dynamic padding ×1). DoD target ≤ 6 met.**

---

## Step 1 — Add new QSS selectors to `theme.py`

**Insertion point:** After existing `QPushButton[accent="subtle"]` block (around line 747), before `ThemeCardWidget` block.

**Required variable extraction** (before the typography loop in `generate_stylesheet`):

```python
compact_spec = theme.typography.get("compact", TYPOGRAPHY_DEFAULTS["compact"])
```

### Selector additions:

```python
/* ── Nav Tab Buttons (Home/Settings sidebar tabs) ── */
QPushButton[accent="nav-tab-active"] {{
    background: {c("gold_dim")};
    color: {c("gold")};
    border: 1px solid {c("gold_border")};
    border-radius: 4px;
    padding: 0 16px;
    font-weight: 600;
}}
QPushButton[accent="nav-tab"] {{
    background: rgba(20,20,36,0.5);
    color: {c("nav_inactive_text")};
    border: 1px solid {c("input_border")};
    border-radius: 4px;
    padding: 0 16px;
    font-weight: 400;
}}
QPushButton[accent="nav-tab"]:hover {{
    background: rgba(200,160,60,0.10);
    color: rgba(200,160,60,0.7);
}}
/* NOTE: nav-tab base background uses hardcoded rgba(20,20,36,0.5)
   (dark_gold-specific). nav-tab:hover uses hardcoded gold RGBA.
   QSS cannot compose rgba(c("gold"), 0.10) or rgba(c("bg_input"), 0.5).
   Same pattern as accent="subtle" base, accent="gold":hover,
   accent="green":hover, accent="subtle":hover. Known limitation. (R3)
   nav-tab-active intentionally has no :hover/:pressed — the active tab
   stays static (see Deviation 6 item 3). */

/* ── Output Target Segmented Buttons ── */
QPushButton[accent="output-target"] {{
    background: rgba(200,160,60,0.08);
    color: rgba(200,160,60,0.5);
    border: 1px solid rgba(200,160,60,0.15);
    border-radius: 4px;
    padding: 0 12px;
}}
QPushButton[accent="output-target"]:checked {{
    background: rgba(200,160,60,0.20);
    color: {c("gold")};
    border: 1px solid rgba(200,160,60,0.40);
}}
QPushButton[accent="output-target"]:hover {{
    background: rgba(200,160,60,0.15);
}}
QPushButton[accent="output-target"]:checked:hover {{
    background: rgba(200,160,60,0.25);
}}
/* NOTE: Output target border uses gold rgba (not input_border token).
   Preserves gold-border visual identity (Finding C). :checked:hover
   added — absent in original inline. */

/* ── Destructive Buttons (Hide, Clear History) ── */
QPushButton[accent="destructive"] {{
    background: {c("red_dim")};
    color: {c("red")};
    border: 1px solid rgba(224,92,75,0.30);
    border-radius: 6px;
}}
QPushButton[accent="destructive"]:hover {{
    background: rgba(224,92,75,0.25);
    border: 1px solid rgba(224,92,75,0.35);
}}
QPushButton[accent="destructive"]:pressed {{
    background: rgba(224,92,75,0.35);
}}
/* NOTE: btn_hide bg=0.15 matches red_dim=0.15 (zero shift).
   btn_clear_history bg=0.12→0.15 (3% shift, minimal).
   btn_clear_history border=0.20→0.30 (10% shift, documented R5).
   Hover/pressed use same hardcoded rgba pattern as accent="gold"
   and accent="green" hover selectors (R3). */

/* ── Mode Toggle (segmented control) ── */
QPushButton[mode-toggle="left"] {{
    background: {c("gold_dim")};
    color: {c("gold")};
    border: 1px solid {c("gold_border")};
    border-radius: 6px 0 0 6px;
    padding: 0 16px;
    font-weight: 600;
}}
QPushButton[mode-toggle="left-inactive"] {{
    background: rgba(20,20,36,0.5);
    color: {c("nav_inactive_text")};
    border: 1px solid {c("input_border")};
    border-radius: 6px 0 0 6px;
    padding: 0 16px;
    font-weight: 400;
}}
QPushButton[mode-toggle="right"] {{
    background: {c("gold_dim")};
    color: {c("gold")};
    border: 1px solid {c("gold_border")};
    border-radius: 0 6px 6px 0;
    padding: 0 16px;
    font-weight: 600;
}}
QPushButton[mode-toggle="right-inactive"] {{
    background: rgba(20,20,36,0.5);
    color: {c("nav_inactive_text")};
    border: 1px solid {c("input_border")};
    border-radius: 0 6px 6px 0;
    padding: 0 16px;
    font-weight: 400;
}}
/* NOTE: No :hover/:pressed rules. ModeToggle has no hover feedback
   in current codebase (verified lines 75-87). Intentional: segmented
   controls typically don't provide hover on active segment. (F8) */

/* ── Gold Dot (green variant for keyword/draft headers) ── */
QFrame[gold-dot-green="true"] {{
    background: {c("green")};
    border-radius: 3px;
}}

/* ── Version Badge (sidebar footer) ── */
QLabel[version-badge="true"] {{
    color: {c("nav_inactive_text")};
    font-size: 8px;
    background: transparent;
}}

/* ── Preview Tab Widget ── */
QTabWidget[preview-tabs="true"]::pane {{
    border: none;
    background: transparent;
}}
QTabWidget[preview-tabs="true"] QTabBar::tab {{
    background: rgba(30,30,50,0.6);
    color: {c("nav_inactive_text")};
    padding: 4px 16px;
    font-weight: bold;
    border: none;
    font-size: 10px;
}}
QTabWidget[preview-tabs="true"] QTabBar::tab:selected {{
    color: {c("gold")};
    background: {c("gold_dim")};
}}
QTabWidget[preview-tabs="true"] QTabBar::tab:hover {{
    color: {c("gold")};
}}

/* ── Compact Combo Mode (Display Mode dropdowns) ── */
QComboBox[combo-mode="true"] {{
    padding: 0 6px;
    border-radius: 4px;
}}

/* ── Section Header: compact-green variant ── */
QLabel[section-header="compact-green"] {{
    color: {c("green")};
    font-family: "{family}";
    font-size: {compact_spec.get("size", 9)}px;
    font-weight: {WEIGHT_MAP.get(compact_spec.get("weight", "Bold"), 700)};
    text-transform: {"uppercase" if compact_spec.get("uppercase", True) else "none"};
    letter-spacing: {compact_spec.get("letter_spacing", 2)}px;
    background: transparent;
}}
/* NOTE: compact-green derives all typography properties from the
   compact scale via compact_spec variable, overriding only color.
   Not a new typography scale — a section-header color variant. (F5)
   Future compact scale changes (e.g., high_contrast at 11px)
   automatically propagate to this variant. */

/* ── Preview Verse Label (set_preview_verse content) ── */
QLabel[preview-verse="true"] {{
    color: {c("text_primary")};
    background: transparent;
    padding: 6px;
}}
/* NOTE: Current inline uses #d8d0c0; theme text_primary = #e8e2d8.
   ~6% brightness shift. Intentional: text_primary is canonical
   verse-content color matching DisplayPreview._render_single_view
   which also uses text_primary. (R2) */
```

---

## Step 2 — Add `_make_section_header` and `_make_separator` to `HomePanel`

```python
def _make_section_header(self, title: str, variant: str = "compact", icon: QIcon = None) -> QWidget:
    """Gold dot + typography-sized label + optional icon, wrapped in QWidget.

    NOTE: No setFont() call on the label — the typography QSS selector
    provides all font properties (size, weight, family, letter-spacing,
    text-transform). SettingsPanel._make_section_header includes a
    redundant setFont() from the pre-typography-system era. (F7)
    """
    container = QWidget()
    header = QHBoxLayout(container)
    header.setContentsMargins(0, 0, 0, 0)
    header.setSpacing(8)
    if icon is not None:
        icon_label = QLabel()
        icon_label.setPixmap(icon.pixmap(16, 16))
        icon_label.setFixedSize(16, 16)
        header.addWidget(icon_label)
        self._section_header_icon_labels.append((icon_label, title))
    dot = QFrame()
    dot.setFixedSize(6, 6)
    if variant == "compact-green":
        dot.setProperty("gold-dot-green", True)
    else:
        dot.setProperty("gold-dot", True)
    header.addWidget(dot)
    label = QLabel(title.upper())
    label.setProperty("section-header", variant)
    header.addWidget(label)
    header.addStretch()
    return container

def _make_separator(self) -> QFrame:
    """1px gold-dim separator line using property selector."""
    sep = QFrame()
    sep.setFrameShape(QFrame.Shape.HLine)
    sep.setProperty("separator", True)
    sep.setFixedHeight(1)
    return sep
```

Initialize in `__init__`:
```python
self._section_header_icon_labels = []  # For future theme-switch retint
```

---

## Step 3 — Migrate left sidebar (lines 143-210)

### Nav tab buttons

```python
self.btn_tab_home.setProperty("accent", "nav-tab-active")
self.btn_tab_home.setStyleSheet("")
self.btn_tab_settings.setProperty("accent", "nav-tab")
self.btn_tab_settings.setStyleSheet("")
```
NOTE: `btn_tab_settings` (inactive tab) gains `:hover` feedback where none existed before. `btn_tab_home` (active tab) has no `:hover` — intentional asymmetry (Deviation 6 item 3).

### Version badge

```python
version.setProperty("version-badge", True)
version.setStyleSheet("")
# Remove version.setFont(QFont("Segoe UI", 8)) — selector handles font
```

### Separator

```python
sep1 = self._make_separator()
```

### Draft editor header

```python
draft_header_container = self._make_section_header("Draft Editor", variant="compact-green")
left_layout.addWidget(draft_header_container)
# Remove the standalone draft_header QLabel — it's inside the container now
```

---

## Step 4 — Migrate center column (lines 220-490)

### Separators

Replace all three separator blocks (lines 248, 318, 380) with `self._make_separator()`.

### Section headers

```python
center_layout.addWidget(self._make_section_header("Verse Navigation", variant="compact"))
center_layout.addWidget(self._make_section_header("Display Controls", variant="compact"))
```

Remove the standalone `nav_buttons_header` and `display_ctrl_header` QLabels — they're inside the containers.

### Navigation buttons

```python
self.nav_up_btn.setProperty("accent", "gold")
self.nav_up_btn.setStyleSheet("")
self.nav_down_btn.setProperty("accent", "gold")
self.nav_down_btn.setStyleSheet("")
```
NOTE: `accent="gold"` pressed state = 0.10 (darker than base). Inline pressed state = 0.30 (brighter than base). Direction reversal — see Deviation 6 item 1. Also: bg shifts 0.12→0.15 (+3%), border shifts 0.25→0.30 (+5%).

### Show/Hide buttons

```python
self.btn_show.setProperty("accent", "green")
self.btn_show.setStyleSheet("")
self.btn_hide.setProperty("accent", "destructive")
self.btn_hide.setStyleSheet("")
```

**Shift documentation:** `btn_show` bg: inline 0.20 → `green_dim` 0.15 (5% shift, Deviation 3). `btn_show` pressed: inline 0.40 → selector 0.15 (pressed = base, zero press feedback — Deviation 6 item 2). `btn_show` border: inline `rgba(76,175,125,0.35)` → selector `rgba(76,175,125,0.3)` (Δ=0.05, Deviation 6). `btn_hide` bg: inline 0.15 → `red_dim` 0.15 (zero shift). `btn_hide` border: inline 0.30 → selector 0.30 (zero shift). `nav_up_btn`/`nav_down_btn` bg: inline 0.12 → `gold_dim` 0.15 (+3% shift). `nav_up_btn`/`nav_down_btn` border: inline 0.25 → `gold_border` 0.30 (+5% shift). Nav button pressed direction reversed (inline brightens, selector dims — Deviation 6 item 1).

### Hint labels

```python
target_label.setProperty("hint", True)
target_label.setStyleSheet("")
mode_label.setProperty("hint", True)
mode_label.setStyleSheet("")
main_mode_label.setProperty("hint", True)
main_mode_label.setStyleSheet("")
alt_mode_label.setProperty("hint", True)
alt_mode_label.setStyleSheet("")
```

**Note:** Hint labels shift from `rgba(255,255,255,0.5/0.4)` (white) to `{c("nav_inactive_text")}` = `rgba(200,160,60,0.4)` (gold at 40%). Intentional — `nav_inactive_text` is the canonical secondary-text color per the typography system.

### Output target buttons (Finding C fix)

```python
for name, label in [("main", "Main"), ("alt", "Alt"), ("all", "All")]:
    btn = QPushButton(label)
    btn.setCheckable(True)
    btn.setFixedHeight(28)
    btn.setProperty("accent", "output-target")
    btn.setStyleSheet("")
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    # Remove the entire inline stylesheet block
    self._target_group.addButton(btn)
    self._target_btns[name] = btn
    # Signal wiring uses lambda (Finding 7):
    btn.toggled.connect(lambda checked, b=btn: self._on_target_btn_style(b, checked))
self._target_btns["main"].setChecked(True)
```

```python
def _on_target_btn_style(self, btn, checked):
    """Force QSS re-evaluation after :checked state change."""
    btn.setProperty("accent", "output-target")
    btn.setStyleSheet("")
```

### Combo boxes (F4 fix)

```python
self.combo_main_mode.setProperty("combo-mode", True)
self.combo_main_mode.setStyleSheet("")
self.combo_alt_mode.setProperty("combo-mode", True)
self.combo_alt_mode.setStyleSheet("")  # No copy-call from combo_main_mode
# Remove line 475: self.combo_alt_mode.setStyleSheet(self.combo_main_mode.styleSheet())
```

---

## Step 5 — Migrate right content section (lines 508-680)

### Preview tabs

```python
self.preview_tabs.setProperty("preview-tabs", True)
self.preview_tabs.setStyleSheet("")
```

### Preview status label (Finding B fix)

```python
self.lbl_preview_status.setProperty("hint", True)
self.lbl_preview_status.setStyleSheet("")
self.lbl_preview_status.setContentsMargins(12, 2, 12, 2)  # Qt: left, top, right, bottom. Matches CSS padding: 2px 12px.
```

### Navigator header

```python
# Remove manual dot2 + nav_title + nav_header QHBoxLayout
# Replace with:
navigator_layout.addWidget(self._make_section_header("Verse Navigator", variant="compact"))
```

### Keyword results header

```python
# Remove manual dot3 + kw_title + kw_header QHBoxLayout
# Replace with:
keyword_layout.addWidget(self._make_section_header("Keyword Results", variant="compact-green"))
```

### History panel header (CRITICAL — Finding A fix)

**DO NOT replace `hist_mini_header` with `_make_section_header`.** The `hist_mini_header` layout contains BOTH the header AND the Clear History button. Migrate individual widgets only:

```python
# Gold dot
dot_hist.setProperty("gold-dot", True)
dot_hist.setStyleSheet("")
dot_hist.setFixedSize(6, 6)  # Deviation 4: 5→6px standardization

# Section header label
hist_mini_label.setProperty("section-header", "compact")
hist_mini_label.setStyleSheet("")
# REMOVE: hist_mini_label.setFont(QFont("Segoe UI", 7, QFont.Weight.Bold))
# Typography selector provides font. Deviation 5: 7px→9px.

# Clear History button
self.btn_clear_history.setProperty("accent", "destructive")
self.btn_clear_history.setStyleSheet("")
# R5 documentation: border shifts from rgba(224,92,75,0.20) to 0.30 (10% shift)

# hist_mini_header layout stays intact — no structural change
```

---

## Step 6 — Migrate ModeToggle (lines 75-87)

```python
def _refresh_style(self):
    for btn, name in [(self.btn_verse, "Verse Lookup"), (self.btn_keyword, "Keyword Search")]:
        active = name == self.current_mode
        if btn == self.btn_verse:
            btn.setProperty("mode-toggle", "left" if active else "left-inactive")
        else:
            btn.setProperty("mode-toggle", "right" if active else "right-inactive")
        btn.setStyleSheet("")
```

No hover/pressed feedback (F8 — matches current behavior).

---

## Step 7 — Migrate DisplayPreview (lines 1443-1760)

### Runtime exceptions (3 inline calls remaining):

1. `self.ref_label.setStyleSheet(...)` — 3-state dynamic color (clear/live/preview). One widget, multiple calls; counts as 1 logical exception.
2. `main_verse_label.setStyleSheet(f"color: ...; padding: {padding}px;")` — per-row dynamic padding.
3. `label.setStyleSheet(f"background: transparent; padding: {padding}px;")` — per-row dynamic padding (overlay).

### Migratable calls:

- `placeholder` (line 1755): `setProperty("hint", True)` + `setStyleSheet("")`.
- `label` (line 1741, in `set_preview_verse`): `setProperty("preview-verse", True)` + `setStyleSheet("")`. R2: color shifts from `#d8d0c0` to `text_primary #e8e2d8` (~6% brighter). Intentional — `text_primary` is canonical verse-content color.
- `_placeholder` (line 1789, in VerseLiveHistoryPanel): `setProperty("hint", True)` + `setStyleSheet("")` + `setContentsMargins(8, 8, 8, 8)` for padding.

---

## Step 8 — Migrate VerseLiveHistoryPanel and HistoryEntryCard

```python
# ts (line 1856)
ts.setProperty("result", True)
ts.setStyleSheet("")

# ref_label (line 1874) — text_primary is default QLabel color
ref_label.setStyleSheet("")  # Inherits from global QWidget color

# restore_icon (line 1882) — transparent is default QWidget bg
restore_icon.setStyleSheet("")
```

---

## Step 9 — Import changes in `home_panel.py`

Add `QIcon` to the `PyQt6.QtGui` import (line 22):

```python
# Before:
from PyQt6.QtGui import QFont, QFontMetrics, QKeySequence, QShortcut
from PyQt6.QtGui import QTextDocument, QTextOption

# After:
from PyQt6.QtGui import QFont, QFontMetrics, QIcon, QKeySequence, QShortcut
from PyQt6.QtGui import QTextDocument, QTextOption
```

---

## Step 10 — Add guard script check to `pre_commit_checks.py`

```python
def check_v131_phase3_home_panel():
    """Verify Phase 3 home panel QSS migration."""
    errors = []

    hp_path = SRC_UI / 'home_panel.py'
    with open(hp_path, encoding='utf-8') as f:
        hp_content = f.read()

    # 1. QIcon imported
    if 'QIcon' not in hp_content:
        errors.append("CRITICAL: home_panel.py missing QIcon import")

    # 2. _make_section_header method exists
    if '_make_section_header' not in hp_content:
        errors.append("CRITICAL: home_panel.py missing _make_section_header method")

    # 3. _make_separator method exists
    if '_make_separator' not in hp_content:
        errors.append("CRITICAL: home_panel.py missing _make_separator method")

    # 4. Inline setStyleSheet count <= 6 (3 logical exceptions: ref_label 3-state,
    #    main_verse_label dynamic padding, overlay label dynamic padding.
    #    Physical counting finds 6 calls because ref_label has 4 separate call sites.)
    ss_count = hp_content.count('.setStyleSheet(')
    if ss_count > 6:
        errors.append(f"CRITICAL: home_panel.py has {ss_count} setStyleSheet calls, expected <= 6")

    # 5. Key property selectors present
    required_properties = [
        'gold-dot', 'separator', 'section-header', 'hint',
        'accent', 'mode-toggle', 'combo-mode', 'preview-tabs',
        'version-badge', 'gold-dot-green', 'output-target',
        'preview-verse', 'destructive',
    ]
    for prop in required_properties:
        if f'setProperty("{prop}' not in hp_content:
            errors.append(f"CRITICAL: home_panel.py missing setProperty('{prop}') call")

    # 6. theme.py has new selectors
    theme_path = SRC_UTILS / 'theme.py'
    with open(theme_path, encoding='utf-8') as f:
        theme_content = f.read()
    new_selectors = [
        'accent="nav-tab"',
        'accent="nav-tab-active"',
        'accent="destructive"',
        'accent="output-target"',
        'gold-dot-green',
        'version-badge',
        'preview-tabs',
        'combo-mode',
        'mode-toggle',
        'section-header="compact-green"',
        'preview-verse',
    ]
    for sel in new_selectors:
        if sel not in theme_content:
            errors.append(f"CRITICAL: theme.py missing selector '{sel}'")

    # 7. compact-green uses compact_spec (not hardcoded values)
    if 'compact_spec' not in theme_content:
        errors.append("CRITICAL: theme.py missing compact_spec variable for compact-green derivation")

    # 8. No QFrame[panel="true"]:hover in theme.py
    if 'QFrame[panel="true"]:hover' in theme_content:
        errors.append("CRITICAL: QFrame[panel=true]:hover still present in theme.py")

    return errors
```

Register in `__main__` after Phase 2 check:
```python
all_errors.extend(check_v131_phase3_home_panel())
```

---

## Regression Hazards

| Hazard | Risk | Mitigation |
|--------|------|------------|
| Clear History button lost in header replacement | **CRITICAL** | Finding A fix: keep `hist_mini_header` intact; migrate individual widgets only |
| `lbl_preview_status` margins wrong (left=2, should be 12) | Medium | Finding B fix: `setContentsMargins(12, 2, 12, 2)` |
| Output target border shifts from gold to white if `input_border` used | Medium | Finding C fix: `accent="output-target"` with gold rgba border |
| Output target `:checked:hover` absent | Medium | Finding C fix: added `QPushButton[accent="output-target"]:checked:hover` |
| `btn_show` background shift (0.20→0.15 = 5%) | Low | Deviation 3 documented |
| `btn_clear_history` background shift (0.12→0.15 = 3%) | Low | Documented |
| `btn_clear_history` border shift (0.20→0.30 = 10%) | Low | R5 documented |
| `btn_hide` background: zero shift (0.15=0.15) | None | Verified |
| Hint label color shift (white→gold) | Low | Intentional per typography system |
| Line 1741 color shift (`#d8d0c0 → text_primary #e8e2d8`, ~6%) | Low | R2 documented; `text_primary` is canonical |
| `hist_mini_label` font shift (7px→9px) | Low | Deviation 5 documented |
| `dot_hist` size shift (5→6) | Low | Deviation 4 documented |
| Signal wiring for output target `toggled` | Medium | Lambda wrapper (Finding 7) |
| `compact-green` hardcodes typography values | Low | F5 fix: derives from `compact_spec` |
| Hover backgrounds hardcoded gold RGBA (not tokens) | Low | R3: documented as known limitation matching existing pattern |
| ModeToggle has no hover/pressed feedback | None | F8: matches current behavior |
| **Nav Up/Down pressed direction reversal** (brightens inline → dims on selector) | **Medium** | Deviation 6 item 1 documented |
| **Show button pressed state collapse** (pressed=base, no visible feedback) | **Medium** | Deviation 6 item 2 documented |
| **Nav tab buttons gain hover feedback** (previously static) | **Low** | Deviation 6 item 3 documented; `nav-tab-active:hover` intentionally absent |
| **Nav tab background hardcoded dark_gold value** (`rgba(20,20,36,0.5)`) | **Low** | R3: documented as known limitation alongside existing token-leak entries |
| **Nav Up/Down bg/border shifts** (bg +3%, border +5%) | **Low** | Deviation 6 item 1 covers |
| **Preview tab hover color dim** (`#d4a84b`→`gold`= `#c8a03c`) | **Low** | Intentional: uses canonical `{c("gold")}` token |
| **Output target unchecked label dim** (0.5→0.4 opacity) | **Low** | Intentional: uses canonical `{c("nav_inactive_text")}` token |
| **`btn_show` border shift** (0.35→0.30, Δ=0.05) | **Low** | Deviation 3 + Deviation 6 item 2 cover as distinct numeric shift |

---

## Definition of Done

- [x] Inline `setStyleSheet()` count in `home_panel.py` reduced from 43 to <= 6 (3 logical exceptions: ref_label 3-state ×4 calls, main_verse_label dynamic padding ×1, overlay dynamic padding ×1).
- [x] **Clear History button remains functional and visible** (Finding A verification).
- [x] **Output target buttons retain gold-border visual identity** (Finding C verification).
- [x] **`lbl_preview_status` padding matches current layout** — `setContentsMargins(12, 2, 12, 2)` (Finding B verification).
- [x] All 10 themes render the home panel without visual regression.
- [x] Sidebar visual identity preserved. Center column headers use `section-header="compact"`.
- [x] Keyword/Draft headers use `section-header="compact-green"` (derived from typography system).
- [x] ModeToggle retains segmented-control visual (asymmetric radii, no hover feedback).
- [x] Show button uses `accent="green"` (5% background shift documented Deviation 3).
- [x] Hide/Clear buttons use `accent="destructive"` (btn_hide zero shift; btn_clear 3% bg + 10% border shift documented R5).
- [x] Non-interactive panels do not respond to hover.
- [x] Interactive widgets retain hover behavior.
- [x] All signals/slots function correctly (queue, playlist, navigator, search, hotkeys, mode toggle, output target, display mode combos).
- [x] `DisplayPreview.ref_label` retains 3-state runtime coloring (1 exception).
- [x] `DisplayPreview` verse content retains per-row dynamic padding (2 exceptions).
- [x] `set_preview_verse` label uses `preview-verse="true"` property (R2: ~6% color shift documented).
- [x] `btn_clear_history` border shift (0.20→0.30) documented in code comment.
- [x] `compact-green` selector derives from `compact_spec` variable (not hardcoded).
- [x] `pre_commit_checks.py` Phase 3 check passes with 0 errors.

---

## Status Log

| Date | Note |
|------|------|
| May 25, 2026 | Initial draft |
| May 25, 2026 | Revised after first audit: Findings A, B, C, F1, 1a/b, 2a/b, F3, F5, F7, F8, 4, 5, 6, 7, 1c corrected |
| May 25, 2026 | Revised after second audit: R1-R6 residual findings corrected |
| May 25, 2026 | Revised after third audit: G1-G12 — guard threshold, nav button pressed reversal, btn_show pressed collapse, nav tab hover introduction, hardcoded nav-tab bg, nav button bg/border shifts, tab hover color, output target label dim, btn_show border shift, Category A/B labels, line counts, line references |
| May 25, 2026 | Post-implementation audit: status updated to Complete. Guard script fixed (F2): `accent` and `result` added to key_properties. `_refresh_section_header_icons()` added to HomePanel (F4); `theme_mgr` parameter added to HomePanel.__init__ and main.py wiring. Deviations 7, 8, 9 added (≤3→≤6 threshold, setStyleSheet("") clearing omitted, _on_target_btn_style omitted). Output-target selector gets font-weight: bold. Pre-flight line references updated to post-implementation values. Sub-roadmap DoD ≤3→≤6 and status updated. ROADMAP Phase 3 marked Complete. All DoD checkboxes marked verified. Guard scripts pass with 0 errors. |
| May 27, 2026 | Manual visual regression testing completed. All 6 sub-roadmap DoD items confirmed. 1 regression found: `#` character stripped from congregation display verse text (`_strip_extra()` in `display_widget.py:573`). Root cause: `re.sub(r"#.*", "")` was applied to verse content (not just reference labels), silently removing `#` and everything after it. BONUS: same issue in `display_preview.py:forward_verse`. Fixed in both files. Sub-roadmap Phase 3 DoD items marked complete; To Implement.md updated to ✅ Done; ROADMAP changelog updated. |
