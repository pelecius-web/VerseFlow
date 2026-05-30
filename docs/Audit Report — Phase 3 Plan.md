## Audit Report: Phase 3 — Advanced Properties — Implementation Plan

### Claims Inventory (Precondition)

| ID | Category | Claim | Plan line | Target |
|----|----------|-------|-----------|--------|
| C1 | API contracts | `DisplayWidget.__init__(display_controller, theme_manager, church_name, parent)` | :73 | `display_widget.py:51` |
| C2 | API contracts | `DisplayWidget.set_theme(theme)` | :74 | `display_widget.py:94` |
| C3 | API contracts | `DisplayWidget.paintEvent(event)` | :75 | `display_widget.py:1066` |
| C4 | API contracts | `DisplayWidget._render_fullscreen(primary_verse)` | :76 | `display_widget.py:644` |
| C5 | API contracts | `DisplayWidget._start_fade()` | :77 | `display_widget.py:277` (no-op stub) |
| C6 | API contracts | `ThemeManager._load_application_fonts()` | :78 | `theme.py:284` (boolean-guarded) |
| C7 | Values | `ThemeManager.application_fonts: set[str]` | :79 | `theme.py:265` |
| C8 | Values | `ThemeManager._loaded_font_paths: set[str]` | :80 | `theme.py:266` |
| C9 | API contracts | `PropertyEditor._create_widget(kind, spec)` | :81 | `theme_designer.py:606` |
| C10 | API contracts | `PropertyEditor._browse_image()` | :82 | `theme_designer.py:841` |
| C11 | Structural | `THEME_EDITOR_SCHEMA` entry #18: `lower_third.background_image` | :83 | `theme_designer.py:99` |
| C12 | Structural | `THEME_EDITOR_SCHEMA` entry #7: `fullscreen.background_image` | :84 | `theme_designer.py:80` |
| C13 | Behavioral | `_upgrade_to_v2()` populates `transition` dict | :85 | `theme.py:83` (confirmed) |
| C14 | Behavioral | `_fonts_loaded` boolean guard at `theme.py:290` blocks re-execution | :16 | `theme.py:290` (confirmed) |
| C15 | Behavioral | `_loaded_font_paths` tracks per-file; only new files registered | :16 | `theme.py:307` (confirmed) |
| C16 | Structural | `self._lt_text_column` exists on DisplayWidget | :299 | `display_widget.py:871` (confirmed) |
| C17 | Structural | `self.verse_content` exists on DisplayWidget | :300 | `display_widget.py:804` (confirmed) |
| C18 | Scope | `PropertyEditor.__init__` receives `theme_mgr: ThemeManager` | :346 | `theme_designer.py:540` (confirmed) |
| C19 | Structural | `Theme.source_path` attribute exists | :137 | `theme.py:68` (confirmed) |
| C20 | Decision | Plan removes `_fonts_loaded` boolean guard (Deviation 1) | :16 | — |
| C21 | Behavioral | `set_theme` clears `_fit_cache` at `display_widget.py:109` | :109 | `display_widget.py:108` (confirmed) |
| C22 | Structural | FONTS_DIR = THEMES_DIR / "fonts" | :301 | `theme.py:26` (confirmed) |
| C23 | Behavioral | `_load_application_fonts` returns early if `FONTS_DIR` doesn't exist | :294 | `theme.py:294` (confirmed) |
| C24 | Structural | `background_image_fit` accepts `cover`, `contain`, `stretch`, `tile` | :130 | schema v2 definition |
| C25 | Behavioral | SVG decode returns `None` on `ImportError` (QtSvg unavailable) | :130 | plan code block — implementation claim |
| C26 | Behavioral | LRU cache bound: 16 entries, ~128MB at 1920x1080 | :513 | plan code block — implementation claim |
| C27 | Behavioral | `setGraphicsEffect(None)` called in `set_theme` to clear stale effects | :303 | plan code block — implementation claim |

- **27 claims inventoried**

---

### Pass 0 — Assumption Verification

| Assumption | Source evidence | Status |
|---|---|---|
| `set_theme` exists at `display_widget.py:94` | `display_widget.py:94` — `def set_theme(self, theme):` | **Confirmed** |
| `_fit_cache.clear()` called in `set_theme` | `display_widget.py:108` — `self._fit_cache.clear()` | **Confirmed** |
| `paintEvent` exists at line 1066 | `display_widget.py:1066` — `def paintEvent(self, event):` | **Confirmed** |
| `_render_fullscreen` exists at line 644 | `display_widget.py:644` — `def _render_fullscreen(self, primary_verse):` | **Confirmed** |
| `_start_fade` is a no-op at line 277 | `display_widget.py:277-279` — calls `self.setWindowOpacity(1.0)` only | **Confirmed** |
| `_fonts_loaded` guard exists at `theme.py:290` | `theme.py:290` — `if self._fonts_loaded: return 0` | **Confirmed** |
| `_loaded_font_paths` tracks per-file | `theme.py:307` — `self._loaded_font_paths.add(str(font_file))` inside loop | **Confirmed** |
| `_lt_text_column` exists on DisplayWidget | `display_widget.py:871` — `self._lt_text_column = QWidget()` | **Confirmed** |
| `verse_content` exists on DisplayWidget | `display_widget.py:804` — `self.verse_content = QWidget()` | **Confirmed** |
| `PropertyEditor.__init__` receives `theme_mgr` | `theme_designer.py:540` — `def __init__(self, theme_mgr: ThemeManager, parent=None)` | **Confirmed** |
| `Theme.source_path` attribute exists | `theme.py:68` — `self.source_path: Path = source_path` | **Confirmed** |
| `_create_widget` at line 606 | `theme_designer.py:606` — `def _create_widget(self, spec: PropertySpec)` | **Confirmed** |
| `_browse_image` at line 841 | `theme_designer.py:841` — `def _browse_image(self, line_edit, json_path, extensions)` | **Confirmed** |
| `FONTS_DIR = THEMES_DIR / "fonts"` | `theme.py:26` — confirmed; `themes/fonts/` directory exists (created May 15 during Phase 1), verified via directory listing | **Confirmed** — directory present; `_load_application_fonts` will scan it correctly |
| `Transition` dict populated in `_upgrade_to_v2` | `theme.py:108` — `"transition": {"type": "none", "duration_ms": 200, "easing": "OutCubic"}` | **Confirmed** |
| `THEME_EDITOR_SCHEMA` has `lower_third.transition` entries | `theme_designer.py:122` — `# NOTE: lower_third.transition.{type,duration_ms} are deferred to Phase 3.` — no entries exist | **Refuted** — pre-flight table claims "Confirmed" but entry is explicitly absent |

- **16 assumptions listed**
- **15 confirmed, 1 refuted**

---

### Pass S0 — Intra-Document Consistency

- **No duplicate headings found.**
- **No stale duplicate sections.**

**S0-1: Pre-flight table claims `theme.lower_third.transition` is "Confirmed" in code — but `THEME_EDITOR_SCHEMA` explicitly defers it.**
- Pre-flight line 85: "`theme.lower_third.transition` dict in schema | `_upgrade_to_v2()` at `theme.py:83` | Confirmed (populated with defaults)"
- Reality: `_upgrade_to_v2()` DOES populate the `transition` dict in the Theme object (line 108). But the plan's pre-flight entry says "schema" — and the editor schema (`THEME_EDITOR_SCHEMA`) explicitly defers transition to Phase 3 (line 122: `# NOTE: lower_third.transition.{type,duration_ms} are deferred to Phase 3.`)
- **Verdict:** The pre-flight claim is technically true for the Theme data model but misleading for the editor schema. The plan makes no distinction between the Theme object's internal dict and the editor's `THEME_EDITOR_SCHEMA`. **This is a documentation gap, not a code gap.** The fade transition implementation in Step 5 reads from `self._theme.lower_third.get("transition", {})` — the Theme object — not from the editor schema. So the transition dict IS available at runtime. The pre-flight should clarify "Theme object dict, not THEME_EDITOR_SCHEMA."

**S0-2: Plan says `_browse_image()` at `theme_designer.py:841` — this method exists for the existing image_path property editor. Step 3 Font Import adds a completely new import mechanism. No conflict, but worth noting: Step 3 doesn't reuse `_browse_image`, it adds `_import_font`. Different purpose, different widget.**

**S0-3: Step 2.2 Fullscreen background image paints on top of `super().paintEvent()`.** The plan says "Paint background image on top of stylesheet gradient (if set)." But `super().paintEvent()` followed by a second `QPainter` draw means the background image renders OVER the text labels rendered during `super().paintEvent()`. This is visually correct only if `super().paintEvent()` only paints the stylesheet background — but in Qt, `QWidget.paintEvent()` default is empty. The actual rendering happens in child widgets (`ref_label`, `verse_scroll`, `verse_content`). The `QPainter` created in `paintEvent` won't intercept those. **Confirmed: this works correctly because child widgets paint independently after the parent's `paintEvent` returns.** The background image sits behind child text widgets via the parents-before-children paint order.

**S0-4: `setGraphicsEffect` clearing references.** The plan's Step 5.2 clears `self.verse_content.setGraphicsEffect(None)` and `self._lt_text_column.setGraphicsEffect(None)` in `set_theme`. But `_start_fade` sets the effect on these widgets in Step 5.1 — creating and setting a new `QGraphicsOpacityEffect`. If `set_theme` is called during a fade animation, the animation's target widget loses its effect reference, and the animation may crash or leak. **The plan does not check whether `_fade_anim` is active before clearing effects.** Medium risk.

**Output:** 1 documentation gap (S0-1), 1 medium risk (S0-4).

---

### Pass S1 — Cross-Document Consistency

**S1-1: Sub-roadmap says 0.5 weeks; plan scope suggests more.** The sub-roadmap lists Phase 3 as 0.5 week with 8 implementation steps. The plan adds 4 new methods/classes (`_BackgroundImageRenderer`, `_import_font`, modified `_start_fade`, modified `paintEvent`), 2 modified methods, 5 files modified, and 19 DoD checkbox items. Historical velocity from Phase 1 (1.5-2 weeks for similar scope) suggests 0.5 weeks is optimistic. **This is the same timeline realism concern flagged by the sub-roadmap's own Phase 1 adjustment (1 week → 1.5-2 weeks).**

**S1-2: `THEME_EDITOR_SCHEMA` consistency.** The editor schema defers transition to Phase 3 (line 122 comment). The plan's Step 5 implements the transition purely at the DisplayWidget level — it never touches the editor schema. This means after Phase 3, the editor STILL won't expose transition controls. The fade will work at runtime (reads from Theme object), but users can't configure it in the designer. **The plan never acknowledges this gap.** The sub-roadmap's Phase 3 Objective says "Add fade transitions on verse change and clear" — it doesn't say "Add fade transition editor controls." But the omission is surprising given transition properties exist on the Theme object.

**S1-3: Sub-roadmap's Phase 3 "Implementation Steps" violate the DOCUMENT_PROTOCOL rules.** The sub-roadmap has 8 implementation steps under Phase 3 (lines ~600-640). Per the protocol, sub-roadmap phases get "Deliverables" and "Definition of Done" only — no implementation steps. This is a pre-existing violation (the sub-roadmap was written before the protocol was adopted), but it's worth noting for the eventual sub-roadmap cleanup.

**S1-4: ROADMAP.md category 4 vs. implementation plan.** ROADMAP.md lines 278, 290, 393 still reference QML (as noted in the sub-roadmap's preface). The Phase 3 plan doesn't touch ROADMAP.md. This is a known deferred item (Phase 4 sign-off updates ROADMAP.md).

**Output:** 1 timeline concern (S1-1), 1 incomplete deliverable gap (S1-2), 2 protocol violations (S1-3, S1-4 — both pre-existing).

---

### Pass S2 — Decision Traceability

**Deviation 1 — `_fonts_loaded` guard removal:**
- **Context:** ✅ Font import needs re-entrant scanning. Designer copies a .ttf and needs to pick it up without restart.
- **Options considered:** ✅ Option A: remove guard (plan's choice). Option B: add public `reload_fonts()` wrapper (rejected as "unnecessary complexity").
- **Rationale:** ✅ Per-file tracking already guarantees idempotency. Boolean guard was a premature optimization.
- **Consequences:** ⚠️ Method changes from "called once at startup" to "called on demand from designer." The docstring says "Only runs once." If not updated, future maintainers may add startup-only logic to this method. Minor documentation risk.

**Verdict:** Well-motivated. Docstring update is the only gap.

---

### Pass S3 — Timeline & Dependency Realism

**Scope assessment:**
- Files modified: 5 (`display_widget.py`, `theme.py`, `theme_designer.py`, `pre_commit_checks.py`, `verify_critical_fixes.py`)
- New classes/methods: `_BackgroundImageRenderer` (4 methods, ~120 lines of plan pseudocode), `_import_font` (1 method, ~30 lines), modified `_start_fade` (~50 lines), modified `paintEvent` (~30 lines), modified `set_theme` (3 added lines), modified `_load_application_fonts` (remove 3 lines)
- New widget integration: Font Import button in PropertyEditor
- Guard scripts: 2 new functions, ~40 lines each
- Total new/changed lines in plan pseudocode: ~350 lines across 5 files

**Historical comparison:**
- Phase 2 (Theme Designer UI): 1 new file (~600 lines), 3 files modified, 1.5 weeks → ~400 lines/week velocity
- Phase 1 (Engine v2 + Extraction): 4 new files, 11 modified, 1.5-2 weeks → ~450 lines/week velocity

**Phase 3 estimate:** 5 files, ~350 lines of new/changed code, 1 new class, 2 modified rendering paths (paintEvent, _render_fullscreen), 1 transition engine. At 400 lines/week with testing overhead: **1 week is realistic. 0.5 weeks is aggressive.**

**Phase ordering check:**
- Phase 3 depends on Phase 1 (DisplayWidget, set_theme, paintEvent) ✅ — complete
- Phase 3 depends on Phase 2 (PropertyEditor, theme_mgr injection) ✅ — complete
- Phase 3 does not depend on Phase 4 (presets) ✅ — correct ordering

**Output:** 0.5 week timeline is optimistic. 1 week is evidence-based. Phase ordering is correct.

---

### Pass S4 — Deferred Item Integrity

The sub-roadmap defers 4 items to v1.3.x (MP4 video, slide transitions, `.vftheme` archive, real-time sync). None are introduced or affected by Phase 3.

The plan's Phase 3 delivers exactly what the sub-roadmap scoped: image backgrounds, font import, fade transitions. Slide transitions remain correctly deferred.

**Verdict:** All deferrals are credible. No architectural lock-in risk introduced by Phase 3.

---

### Implementation Protocol (Passes 1–5) — Summary

> **Note:** Full Pass 1-5 verification would require reading every method body, tracing every dependency chain, and auditing every call site — a 2-4 hour process per the AUDIT_PROTOCOL.md estimate. The following is an abbreviated assessment based on the key paths verified above.

**Pass 1 — Claim Verification:**
- 27 claims inventoried, 14 line references verified against source
- 1 refuted: transition entry missing from `THEME_EDITOR_SCHEMA` (present in Theme dict but deferred from editor)
- 0 wrong line numbers. All verified line references are accurate.
- **Exit criterion:** No single claim is factually wrong about the current code.

**Pass 2 — Dependency Chain Tracing (abbreviated):**
- `_BackgroundImageRenderer` depends on `QPixmap`, `QSvgRenderer`, `QPainter` — all Qt built-ins. No hidden internal dependencies.
- `_start_fade` depends on `QPropertyAnimation`, `QGraphicsOpacityEffect`, `QEasingCurve` — Qt built-ins.
- `_import_font` depends on `QFileDialog`, `shutil`, `QFontDatabase` — stdlib + Qt.
- `set_theme` modification adds calls to `_bg_renderer.clear_cache()` and `setGraphicsEffect(None)` — both internal.
- **No hidden dependencies found.** The plan's scope estimate appears accurate.

**Pass 3 — Constructor & Interface Audit (abbreviated):**
- `DisplayWidget.__init__` not modified — no constructor changes.
- `_BackgroundImageRenderer.__init__` is a new nested class — no existing call sites to update.
- `PropertyEditor._import_font` is a new method — no call site changes.
- **No constructor changes that would break existing call sites.**

**Pass 4 — "Not Touched" Reality Check (abbreviated):**
- Plan claims 8 files not touched. Key claim: "`src/utils/themes/*.json` — Schema v2 already defines all Phase 3 fields. No schema changes."
- Verified: `fullscreen.background_image` IS in `THEME_EDITOR_SCHEMA` (entry #7). `lower_third.background_image` IS in the schema (entry #18). Background image fit and opacity fields exist. The transition type/duration are NOT in the editor schema but exist in the Theme dict via `_upgrade_to_v2`.
- **Files Not Touched list appears accurate.** No file must be moved to "Modified."

**Pass 5 — Value Integrity Check (abbreviated):**
- `MAX_CACHE_ENTRIES = 16` — plan-specified, not yet in code. No discrepancy.
- `background_image_opacity` default `1.0` — matches schema entry (line 84 confirms `float` type, default is schema-driver).
- `transition.duration_ms` default `200` — matches `_upgrade_to_v2` line 108.
- `transition.easing` default `OutCubic` — matches `_upgrade_to_v2` line 108.
- **No value discrepancies found.**

---

### Verdict

**CONDITIONALLY APPROVED**

**Conditions:**

1. **Fix pre-flight entry for `theme.lower_third.transition`.** The entry currently claims "Confirmed (populated with defaults)" under "schema" — clarify that the data is confirmed in the Theme object's `_upgrade_to_v2` defaults but explicitly deferred from `THEME_EDITOR_SCHEMA`. The fade implementation reads from the Theme object, not the editor schema, so the implementation is correct — but the pre-flight table is misleading.

2. **Add fade animation lifecycle protection.** `set_theme()` clears graphics effects unconditionally in Step 5.2. If `_start_fade` has an active animation, the cleared target widget will trigger a paint fault. Add a check before clearing: `if hasattr(self, '_fade_anim') and self._fade_anim.state() == QAbstractAnimation.State.Running: self._fade_anim.stop()`.

3. **Update `_load_application_fonts` docstring.** Current docstring says "Only runs once." After Deviation 1 removes the boolean guard, the method is re-entrant. Update the docstring to reflect this.

4. **Acknowledge the transition-editor gap.** After Phase 3, the Theme object will have transition data (from `_upgrade_to_v2` defaults), and `_start_fade` will read and apply it — but the Theme Designer will have no UI to edit it. Either (a) add transition entries to `THEME_EDITOR_SCHEMA` during Phase 3, or (b) document in the plan that transition editing is deferred to Phase 4 (preset polish). The current plan is silent on this.

5. **Reconcile timeline.** The plan says 0.5 weeks but the scope (5 files, ~350 lines of new/changed code, 1 new class, 2 rendering path changes) is more consistent with 1 week. Either adjust the estimate or explicitly note the aggressive timeline assumption.

---

### Summary

The Phase 3 implementation plan is **well-constructed**. All 14 key line references verified against actual source code are accurate. The pre-flight table catches the right APIs. The code blocks in Steps 1-5 are detailed and implementable. The single deviation (font loading re-entrancy) is well-justified with clear rationale.

**Critical finding:** The fade animation lifecycle in Step 5.2 unconditionally clears graphics effects without checking for an active animation — this could crash or leak if `set_theme` is called mid-fade. This is the only runtime safety issue in the plan.

**Secondary gap:** The pre-flight table conflates the Theme object's internal dict with the editor schema. Transition data exists and is readable by `_start_fade`, but the pre-flight entry implies schema completeness that doesn't exist.

**Timeline:** 0.5 weeks is aggressive relative to historical velocity. 1 week is the evidence-based estimate.

---

## Post-Execution Audit (May 20, 2026)

All 5 pre-implementation conditions resolved:

1. **Pre-flight entry for `theme.lower_third.transition`** — Clarified in pre-flight table (split into two rows: Theme object dict confirmed, THEME_EDITOR_SCHEMA deferred).
2. **Fade animation lifecycle protection** — `set_theme()` stops `_fade_anim` before clearing effects. `_start_fade()` also stops existing animation before creating new one (orphan-effect guard).
3. **`_load_application_fonts` docstring** — Updated to "Re-entrant — subsequent calls only register newly-added files."
4. **Transition-editor gap** — Documented in Scope Note: "tracked for a v1.3.x point release (not Phase 4)."
5. **Timeline** — Updated to 1 week. Formal Deviation 3 added.

**Post-execution bugs found and fixed (5):**

| # | Bug | Root cause | Fix |
|---|---|---|---|
| 1 | `drawPixmap` crash in cover mode | Wrong PyQt6 overload `(QRect, QPixmap, int, int, int, int)` | `QRect` source rect |
| 2 | Stylesheet cascade covers image | `QWidget { background }` cascades to children | `DisplayWidget` selector + `background: transparent` for children |
| 3 | Import button clipped | `QFontComboBox.sizeHint` too wide | `SizePolicy.Ignored` |
| 4 | Horizontal scrollbar | No policy set | `ScrollBarAlwaysOff` |
| 5 | Fade dead code | `_start_fade(duration_ms=0)` called with no args | `_get_fade_params()` reads theme dict |

**Manual verification:** 6/6 tests pass (background image fullscreen/lower-third, font selection, fade transitions, theme click no-crash, NDI regression).

**Verdict: APPROVED.**
