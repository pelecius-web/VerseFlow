# Phase 0 — Typography System Foundation
## Implementation Plan (v1.3.1)

> **Status:** ✅ Done — Signed off May 23, 2026
> **Audit basis:** v1.3.1 UI Polish & Consistency Sub-Roadmap (May 22, 2026 revision with B1–B5 blockers + R2–R8 refinements applied). Cross-referenced against `theme.py` (686 lines), 3 built-in theme JSONs, `settings_panel.py` (509 lines), `pre_commit_checks.py`, and `DOCUMENT_PROTOCOL.md`.
> **Sub-roadmap deviations:** 2 intentional (documented below)

---

## Deviations from Sub-Roadmap

### Deviation 1 — Guard script typography key count: 5 → 4

- **Sub-roadmap says:** "Guard script `pre_commit_checks.py` extended: verify all built-in themes (the 3 in `BUILTIN_THEME_IDS` — `dark_gold`, `light`, `high_contrast`) have a `typography` section with the **5** expected keys."
- **Plan says:** Guard script verifies **4** expected keys: `compact`, `standard`, `body`, `hint`.
- **Justification:** R5 deferred the `caption` entry to v1.4.0. The sub-roadmap's Phase 0 DoD correctly states "4 named scales (compact, standard, body, hint)" and the JSON spec shows 4 entries, but the guard script deliverable text still references "5" — a stale count from before R5 was applied. The DoD is authoritative; the guard script deliverable text is the pre-R5 artifact.

### Deviation 2 — Typography selector color: per-entry token mapping (not uniform gold)
- **Sub-roadmap says:** `generate_stylesheet()` pseudocode: `rules.append(f'QLabel[typography="{name}"] {{ ... }}')` — the `{{ ... }}` placeholder does not specify which color token to use per entry.
- **Plan says:** Each typography entry maps to a specific color token via a `TYPO_COLOR_TOKENS` mapping dict: `compact` → `gold`, `standard` → `gold`, `body` → `text_primary`, `hint` → `nav_inactive_text`. The loop reads this mapping per entry rather than applying `gold` uniformly.
- **Justification:** The current codebase uses different color tokens for different label types: `QLabel[section-header="true"]` uses `c("gold")` (section headers), `QLabel[hint="true"]` uses `c("nav_inactive_text")` (dimmed hint text). Applying `gold` to all 4 typography entries would cause `hint` and `body` labels to render as bright gold instead of their intended muted/primary colors — a functional regression. The mapping dict preserves existing behavior and is extensible for future entries (v1.4.0 `caption` can add its own color token). (Deviation 2, F2 fix)

---

## Files Created
None. Phase 0 is additive modifications to existing files only.

---

## Files Modified
- `src/utils/themes/dark_gold.json` — Add `typography` section (4 entries) between `spacing` and `author`
- `src/utils/themes/light.json` — Add `typography` section (4 entries) between `spacing` and `fullscreen`
- `src/utils/themes/high_contrast.json` — Add `typography` section (4 entries) between `spacing` and `fullscreen`
- `src/utils/theme.py` — Add `TYPOGRAPHY_DEFAULTS` and `TYPO_COLOR_TOKENS` constants; add `self.typography` to `__init__`; inject typography in `_upgrade_to_v2`; extend `deep_copy()` and `_to_dict()`; replace hardcoded section-header QSS block with typography loop + deprecated alias
- `pre_commit_checks.py` — Add `check_v131_typography_phase0()` function; register in `__main__`

---

## Files Not Touched
- `src/utils/themes/test_1.json` — User-created theme, not in `BUILTIN_THEME_IDS`. Falls back to `TYPOGRAPHY_DEFAULTS` via `Theme.__init__`. No disk modification needed (R4).
- `src/ui/settings_panel.py` — Phase 0 scope: infrastructure only. Panel migration is Phase 1. The single `setProperty("section-header", True)` call at `_make_section_header` remains unchanged — deprecated alias preserves its rendering.
- `src/ui/home_panel.py` — Phase 3 scope. Not touched until Phase 3 migration.
- `src/ui/theme_designer.py` — Phase 4 scope. Not touched until Phase 4 migration.
- `src/core/channel_manager.py` — Outside v1.3.1 operator-panel scope.
- `src/display/*` (all display files) — Outside v1.3.1 operator-panel scope. Congregation display rendering must not change.
- `src/utils/icons.py` — Phase 2 scope. Not touched until icon factory extension.
- `src/db/db_layer.py` — Outside v1.3.1 scope entirely.
- `src/core/navigator.py` — Outside v1.3.1 scope entirely.
- `verify_critical_fixes.py` — Phase 0 DoD does not require changes to this script. Phase 1 may extend it for the settings-panel zero-inline-call check.

---

## Step 0 — Pre-Flight Verification
Confirm the current codebase state matches expectations before any modification.
| Required by Plan | Present in Code | Status |
|-------------------|-----------------|--------|
| `BUILTIN_THEME_IDS = {"dark_gold", "light", "high_contrast"}` | `theme.py` defines this set at module level | ✅ Confirmed |
| `test_1` not in `BUILTIN_THEME_IDS` | Not present in the set | ✅ Confirmed |
| `Theme.__init__` does not parse `typography` | No `self.typography` in `__init__` body | ✅ Confirmed — absent, needs addition |
| `Theme.deep_copy()` does not include `typography` | Reconstruction dict lacks `typography` key | ✅ Confirmed — absent, needs addition (B1) |
| `Theme._to_dict()` does not include `typography` | Serialization dict lacks `typography` key | ✅ Confirmed — absent, needs addition (B1) |
| `_upgrade_to_v2()` does not inject typography | Method body has no typography injection | ✅ Confirmed — absent, needs addition |
| `generate_stylesheet()` has hardcoded `QLabel[section-header="true"]` | Present in the f-string | ✅ Confirmed — will be replaced by loop |
| `generate_stylesheet()` has no typography loop | No iteration of `theme.typography` in function body | ✅ Confirmed — absent, needs addition |
| All 3 built-in JSONs lack `typography` section | Verified: `dark_gold.json`, `light.json`, `high_contrast.json` — none has `typography` | ✅ Confirmed — absent, needs addition |
| `test_1.json` lacks `typography` section | Verified: no `typography` key | ✅ Confirmed — will use fallback |
| `QLabel[hint="true"]` uses `c("nav_inactive_text")` | Present in `generate_stylesheet()` | ✅ Confirmed — guides color mapping |
| settings_panel `_make_section_header` uses `setProperty("section-header", True)` | Present at line 244 | ✅ Confirmed — preserved by deprecated alias |
| `pre_commit_checks.py` has no typography checks | Verified: no `typography` references in any check function | ✅ Confirmed — absent, needs addition |
| Guard script key count discrepancy (deliverable says 5, DoD says 4) | Sub-roadmap line 234 says "5 expected keys"; DoD says "4 named scales" | ✅ Confirmed — DoD is authoritative (Deviation 1) |

---

## Step 1 — Add `TYPOGRAPHY_DEFAULTS` and `TYPO_COLOR_TOKENS` constants
**Insertion point:** After `WEIGHT_MAP` dict (after the closing brace), before `class Theme`.
**Rationale:** These constants are used in three places: `__init__` fallback, `_upgrade_to_v2` injection, and `generate_stylesheet` typography loop + deprecated alias. Defining once avoids duplication. `TYPO_COLOR_TOKENS` maps typography entry names to theme color token names — this is the F2 fix that prevents `body` and `hint` from rendering as gold.
**Code to insert:**
```python
# Default typography scale — emitted by generate_stylesheet() when a theme
# lacks the section. Matches the 4-entry initial population in built-in JSONs.
# Invariant: typography dict values must be numeric/string primitives that
# never contain unbalanced braces — this protects generate_stylesheet()'s
# f-string injection point from ValueError crashes. (F8 mitigation)
TYPOGRAPHY_DEFAULTS = {
    "compact":   {"size": 9,  "weight": "Bold",   "uppercase": True,  "letter_spacing": 2},
    "standard":  {"size": 13, "weight": "Bold",   "uppercase": False, "letter_spacing": 0},
    "body":      {"size": 10, "weight": "Normal", "uppercase": False, "letter_spacing": 0},
    "hint":      {"size": 9,  "weight": "Normal", "uppercase": False, "letter_spacing": 0},
}

# Color token mapping per typography entry (Deviation 2, F2 fix).
# Section headers (compact, standard) use gold — matches current QLabel[section-header="true"].
# Body labels use text_primary — matches standard QLabel color.
# Hint labels use nav_inactive_text — matches current QLabel[hint="true"].
# Future entries (e.g., caption in v1.4.0) add their token here as a one-line edit.
TYPO_COLOR_TOKENS = {
    "compact":  "gold",
    "standard": "gold",
    "body":     "text_primary",
    "hint":     "nav_inactive_text",
}
```

---

## Step 2 — Parse `typography` in `Theme.__init__`
**Insertion point:** After `self.fullscreen = data.get("fullscreen", {})`, before `if self.schema_version == "1.0": self._upgrade_to_v2()`.
**Rationale:** `data.get("typography", copy.deepcopy(TYPOGRAPHY_DEFAULTS))` fallback ensures: (a) themes with a `typography` section get their own dict (fresh from `json.load`, no shared-reference risk), (b) themes without the section get independent copies of the defaults (not the shared `TYPOGRAPHY_DEFAULTS` object itself), and (c) `_upgrade_to_v2` can then override the fallback for v1.0 themes if needed.
**Code to insert:**
```python
self.typography: dict = data.get("typography", copy.deepcopy(TYPOGRAPHY_DEFAULTS))
```

---

## Step 3 — Inject typography in `_upgrade_to_v2()`
**Insertion point:** After the `if not self.fullscreen:` block (after fullscreen defaults are populated), before `self.schema_version = self.SCHEMA_VERSION`.
**Rationale:** `__init__` already set `self.typography` via `data.get()`. If a v1.0 theme somehow had a `typography` key in its JSON, `data.get()` would have populated it. The `if not self.typography:` guard preserves any pre-existing values — matches the `setdefault` pattern used for lower_third keys. Only v1.0 themes that lack the `typography` key entirely get the defaults injected.
**Code to insert:**
```python
        # Typography defaults (Phase 0 — additive section, no schema_version bump)
        if not self.typography:
            self.typography = copy.deepcopy(TYPOGRAPHY_DEFAULTS)
```

---

## Step 4 — Extend `Theme.deep_copy()` reconstruction dict
**Insertion point:** In the `data` dict inside `deep_copy()`, add `"typography": copy.deepcopy(self.typography)` between `"spacing"` and `"lower_third"`.
**Before:**
```python
        data = {
            "name": self.name,
            "id": self.id,
            "description": self.description,
            "version": self.version,
            "schema_version": self.schema_version,
            "author": self.author,
            "colors": copy.deepcopy(self.colors),
            "fonts": copy.deepcopy(self.fonts),
            "animation": copy.deepcopy(self.animation),
            "spacing": copy.deepcopy(self.spacing),
            "lower_third": copy.deepcopy(self.lower_third),
            "fullscreen": copy.deepcopy(self.fullscreen),
        }
```
**After:**
```python
        data = {
            "name": self.name,
            "id": self.id,
            "description": self.description,
            "version": self.version,
            "schema_version": self.schema_version,
            "author": self.author,
            "colors": copy.deepcopy(self.colors),
            "fonts": copy.deepcopy(self.fonts),
            "animation": copy.deepcopy(self.animation),
            "spacing": copy.deepcopy(self.spacing),
            "typography": copy.deepcopy(self.typography),   # Phase 0 (B1)
            "lower_third": copy.deepcopy(self.lower_third),
            "fullscreen": copy.deepcopy(self.fullscreen),
        }
```
**Rationale:** Without this, the Theme Designer's `deep_copy()` → `Theme(data)` → `__init__` path would lose the source theme's typography and fall back to `TYPOGRAPHY_DEFAULTS`. This silently overwrites any custom typography a user defined in their theme — a data-loss bug (B1 blocker).

---

## Step 5 — Extend `Theme._to_dict()` serialization output
**Insertion point:** In the return dict inside `_to_dict()`, add `"typography": self.typography` between `"spacing"` and `"fullscreen"`.
**Before:**
```python
        return {
            "name": self.name,
            "id": self.id,
            "description": self.description,
            "version": self.version,
            "schema_version": "2.0",
            "author": getattr(self, "author", ""),
            "colors": self.colors,
            "fonts": self.fonts,
            "animation": self.animation,
            "spacing": self.spacing,
            "fullscreen": self.fullscreen,
            "lower_third": self.lower_third,
        }
```
**After:**
```python
        return {
            "name": self.name,
            "id": self.id,
            "description": self.description,
            "version": self.version,
            "schema_version": "2.0",
            "author": getattr(self, "author", ""),
            "colors": self.colors,
            "fonts": self.fonts,
            "animation": self.animation,
            "spacing": self.spacing,
            "typography": self.typography,   # Phase 0 (B1)
            "fullscreen": self.fullscreen,
            "lower_third": self.lower_third,
        }
```
**Rationale:** Without this, `Theme.save()` and `Theme.save_as()` silently strip the typography section from the saved JSON. A user who opens their theme in the designer, edits a color, and saves would lose their typography — a silent data-loss bug (B1 blocker). The insertion position between `spacing` and `fullscreen` preserves the established section order in JSON files.

---

## Step 6 — Add `typography` section to 3 built-in theme JSONs
All 3 built-in JSONs receive the same 4-entry typography block with identical values. Future divergence (e.g., high_contrast using 11px for `compact` accessibility) is a JSON edit — exactly the workflow Decision 5 enables.

### 6a — `dark_gold.json`
**Insertion point:** After the `spacing` section closing brace, before `"author"`.
```json
"typography": {
    "compact":   { "size": 9,  "weight": "Bold",   "uppercase": true,  "letter_spacing": 2 },
    "standard":  { "size": 13, "weight": "Bold",   "uppercase": false, "letter_spacing": 0 },
    "body":      { "size": 10, "weight": "Normal", "uppercase": false, "letter_spacing": 0 },
    "hint":      { "size": 9,  "weight": "Normal", "uppercase": false, "letter_spacing": 0 }
},
```

### 6b — `light.json`
**Insertion point:** After the `spacing` section closing brace, before `"fullscreen"`.
Same `typography` block as above.

### 6c — `high_contrast.json`
**Insertion point:** After the `spacing` section closing brace, before `"fullscreen"`.
Same `typography` block as above.

**Note:** `test_1.json` is not modified. It is a user-created theme not in `BUILTIN_THEME_IDS`. `Theme.__init__` provides fallback via `TYPOGRAPHY_DEFAULTS` (R4).

---

## Step 7 — Replace hardcoded section-header QSS with typography loop + deprecated alias
This is the core `generate_stylesheet()` modification. It replaces the static `QLabel[section-header="true"]` block with a dynamic loop that emits per-entry selectors with correct color tokens, plus a deprecated alias for backward compatibility.

**Insertion point in `generate_stylesheet()` function body:** The function currently starts with `c = theme.c`, `f = theme.fonts`, `s = theme.spacing`, then returns a single f-string. The typography loop must be computed before the f-string is assembled, and the f-string must be modified to accept the `{typography_qss}` injection.

### 7a — Add typography loop construction before the f-string return
**Insertion point:** After the `c = theme.c`, `f = theme.fonts`, `s = theme.spacing` assignments, before the `return f"""` statement.
```python
    # ── Typography selectors (Phase 0: Decision 5 token-based loop) ──
    typo_rules = []
    family = f.get("family", "Segoe UI")
    for name, spec in theme.typography.items():
        size = spec.get("size", 9)
        weight = spec.get("weight", "Bold")
        weight_num = WEIGHT_MAP.get(weight, 700)
        uppercase = spec.get("uppercase", False)
        ls = spec.get("letter_spacing", 0)
        color_token = TYPO_COLOR_TOKENS.get(name, "gold")   # Deviation 2: per-entry color

        text_transform = "uppercase" if uppercase else "none"

        typo_rules.append(
            f'QLabel[typography="{name}"] {{\n'
            f'    color: {c(color_token)};\n'
            f'    font-family: "{family}";\n'
            f'    font-size: {size}px;\n'
            f'    font-weight: {weight_num};\n'
            f'    text-transform: {text_transform};\n'
            f'    letter-spacing: {ls}px;\n'
            f'    background: transparent;\n'
            f'}}\n'
        )
        typo_rules.append(
            f'QLabel[section-header="{name}"] {{\n'
            f'    color: {c(color_token)};\n'
            f'    font-family: "{family}";\n'
            f'    font-size: {size}px;\n'
            f'    font-weight: {weight_num};\n'
            f'    text-transform: {text_transform};\n'
            f'    letter-spacing: {ls}px;\n'
            f'    background: transparent;\n'
            f'}}\n'
        )

    # Deprecated alias: section-header="true" renders as compact.
    # Removed in Phase 1 DoD after _make_section_header migration.
    # F9 fix: use .get() with fallback to prevent KeyError on partial dicts.
    compact_spec = theme.typography.get("compact", TYPOGRAPHY_DEFAULTS["compact"])
    typo_rules.append(
        f'QLabel[section-header="true"] {{\n'
        f'    color: {c(TYPO_COLOR_TOKENS.get("compact", "gold"))};\n'
        f'    font-family: "{family}";\n'
        f'    font-size: {compact_spec.get("size", 9)}px;\n'
        f'    font-weight: {WEIGHT_MAP.get(compact_spec.get("weight", "Bold"), 700)};\n'
        f'    text-transform: uppercase;\n'
        f'    letter-spacing: {compact_spec.get("letter_spacing", 2)}px;\n'
        f'    background: transparent;\n'
        f'}}\n'
    )

    typography_qss = "\n".join(typo_rules)
```

### 7b — Replace the hardcoded section-header block in the f-string
**Current code (to be removed):**
```python
/* ── Section Headers (uppercase labels with gold accent) ── */
QLabel[section-header="true"] {{
    color: {c("gold")};
    font-size: 9px;
    font-weight: bold;
    letter-spacing: 2px;
    background: transparent;
}}
```

**Replace with:**
```python
/* ── Typography / Section Headers (Phase 0: Decision 5 token-based loop) ── */
{typography_qss}
```

**Key design decisions:**
- **Dual emission** (`[typography="X"]` + `[section-header="X"]`): Per sub-roadmap requirement. Preserves backward compatibility with v1.3.0 `section-header` property while introducing `typography` as the forward-looking property name. Phases 1, 3, 4 use whichever name fits semantically.
- **Per-entry color tokens** (`TYPO_COLOR_TOKENS`): F2 fix. `compact`/`standard` → `gold` (section headers), `body` → `text_primary` (content text), `hint` -> `nav_inactive_text` (dimmed text, matching existing `QLabel[hint="true"]`). Future entries extend the mapping dict with one line.
- **Deprecated alias is not hardcoded**: Reads from `theme.typography.get("compact", ...)` with fallback. If a theme overrides `compact` to 11px, the deprecated alias follows automatically.
- **F9 `.get()` fallback**: `compact_spec = theme.typography.get("compact", TYPOGRAPHY_DEFAULTS["compact"])` prevents `KeyError` on partial user typography dicts (user themes with incomplete `typography` sections).
- **`font-family` sourced from `theme.fonts.family`**: Typography entries don't include `family` in their JSON spec. The generator sources it from the existing `fonts` section, matching how the current hardcoded rule implicitly inherits whatever QFont the label uses.

---

## Step 8 — Extend `pre_commit_checks.py` with typography guard
**Insertion point:** Add `import json` to the existing import block at the top of `pre_commit_checks.py` (currently absent — the function uses `json.load()`). Add new function `check_v131_typography_phase0()` after the existing check functions. Register it in the `__main__` block.
```python
def check_v131_typography_phase0():
    """Verify Phase 0 typography system foundation is intact."""
    errors = []

    # 1. All 3 built-in themes have a typography section with 4 expected keys (Deviation 1: 4 not 5)
    THEMES_DIR = SRC_UTILS / 'themes'
    BUILTIN_IDS = {"dark_gold", "light", "high_contrast"}
    EXPECTED_TYPO_KEYS = {"compact", "standard", "body", "hint"}

    for builtin_id in BUILTIN_IDS:
        path = THEMES_DIR / f"{builtin_id}.json"
        if not path.exists():
            errors.append(f"CRITICAL: Built-in theme {builtin_id}.json missing")
            continue
        with open(path, encoding='utf-8') as f:
            data = json.load(f)
        if "typography" not in data:
            errors.append(f"CRITICAL: {builtin_id}.json missing typography section")
            continue
        typo_keys = set(data["typography"].keys())
        missing = EXPECTED_TYPO_KEYS - typo_keys
        if missing:
            errors.append(f"CRITICAL: {builtin_id}.json typography missing keys: {missing}")

    # 2. theme.py typography infrastructure
    theme_path = SRC_UTILS / 'theme.py'
    with open(theme_path, encoding='utf-8') as f:
        theme_content = f.read()

    if 'TYPOGRAPHY_DEFAULTS' not in theme_content:
        errors.append("CRITICAL: theme.py missing TYPOGRAPHY_DEFAULTS constant")
    if 'TYPO_COLOR_TOKENS' not in theme_content:
        errors.append("CRITICAL: theme.py missing TYPO_COLOR_TOKENS color mapping (F2 fix)")
    if 'typography' not in theme_content:
        errors.append("CRITICAL: theme.py missing typography handling")
    if 'typography_qss' not in theme_content:
        errors.append("CRITICAL: theme.py generate_stylesheet missing typography loop injection")
    if 'section-header="true"' not in theme_content:
        errors.append("CRITICAL: theme.py missing deprecated section-header=true alias")

    # 3. B1 blockers: deep_copy and _to_dict must include typography
    if 'copy.deepcopy(self.typography)' not in theme_content:
        errors.append("CRITICAL: Theme.deep_copy missing typography (B1 blocker)")
    if '"typography": self.typography' not in theme_content:
        errors.append("CRITICAL: Theme._to_dict missing typography (B1 blocker)")

    # 4. F9 fix: deprecated alias must use .get() with fallback
    if 'typography.get("compact"' not in theme_content:
        errors.append("CRITICAL: Deprecated alias missing .get() fallback (F9 KeyError risk)")

    return errors
```

**Register in `__main__`:** Add after existing check calls:
```python
    print("Checking v1.3.1 Phase 0 typography system...")
    all_errors.extend(check_v131_typography_phase0())
```

---

## Regression Hazards
| Hazard | Risk | Mitigation |
|--------|------|------------|
| Typography loop output injected into f-string via `{typography_qss}` — introduces new failure mode where unbalanced braces in theme data would cause Python `ValueError` crash, breaking stylesheet generation for all panels | High impact, low probability — typography values are numeric/string primitives (`size: 9`, `weight: "Bold")`) that never contain braces; but code construction never produces them from user-facing theme JSON editing | **Invariant documented**: `TYPOGRAPHY_DEFAULTS` comment states that typography dict values must be numeric/string primitives never containing unbalanced braces. Future edits must preserve this invariant. |
 `QLabel[typography="hint"]` color is `nav_inactive_text` (not `gold`) — if Phase 1 developers expect gold and write `setProperty("typography", "hint")` expecting gold output, they get dimmed text | Medium impact, medium probability — developers familiar with section-header="true" behavior may assume all typography selectors are gold | **`TYPO_COLOR_TOKENS` mapping is the single source of truth.** Phase 1 plan must reference this dict. Documentation in Phase 1 plan should explicitly state: "typography selector color varies by entry; consult `TYPO_COLOR_TOKENS`." |
| `deep_copy()` reconstructs `typography` via `copy.deepcopy(self.typography)` — double-deepcopy on fallback path (when `self.typography` is already a `deepcopy` of `TYPOGRAPHY_DEFAULTS`) | No functional impact — double-deepcopy produces a fresh independent dict, which is correct behavior. Minor performance overhead in fallback path only Acceptable. Fallback path is rare; correct independence is more important than avoiding redundant deepcopy. |
| Deprecated alias `section-header="true"` duplicates the `section-header="compact"` selector — both produce identical QSS for compact entries | No visual impact — both selectors render the same. Minor cascade noise | Acceptable during Phase 0. Alias removed in Phase 1 DoD after the single `setProperty("section-header", True)` call site migration. |
| Typography loop emits selectors with `font-family` injection — overrides per-widget font choices for labels opting via `setProperty("typography", "X")` | Low impact — typography selectors target only labels that explicitly opt in. Generic `QLabel` styling is unaffected. `font-family` value comes from `theme.fonts.family`, the app's default font | Acceptable. Labels opting in to typography rendering expect their font to be the theme's default family. If a label needs a different font, it shouldn't use the typography property — it should set its own `QFont` directly. |
| `__init__` fallback `data.get("typography", copy.deepcopy(TYPOGRAPHY_DEFAULTS))` — partial typography dicts (e.g., `{standard: {...}}` without `compact`) pass through without filling missing keys | Medium impact — partial dicts would cause `KeyError` in `theme.typography["compact"]` access | **F9 fix applied**: deprecated alias uses `theme.typography.get("compact", TYPOGRAPHY_DEFAULTS["compact"])` with fallback. Typography loop uses `.get()` per spec field. Guard script validates built-in themes have all 4 keys. User themes with partial dicts won't crash. |

---

## Definition of Done
- [ ] All 3 built-in theme JSONs (`dark_gold`, `light`, `high_contrast`) have a `typography` section with 4 named scales (compact, standard, body, hint). User-created themes lacking the section fall back to `TYPOGRAPHY_DEFAULTS` via `Theme.__init__`. (R4, R5: scope to built-ins; defer `caption` to v1.4.0.)
- [ ] `Theme.typography` attribute parses and exposes the dict. Themes without the section receive `copy.deepcopy(TYPOGRAPHY_DEFAULTS)` — no shared-reference mutation risk.
- [ ] **`Theme.deep_copy()` includes `typography` in its reconstruction dict.** (B1) Verified: deep-copied editing sandbox preserves typography on every edit cycle.
- [ ] **`Theme._to_dict()` includes `typography` in its serialization output.** (B1) Verified: `Theme.save()` and `Theme.save_as()` retain typography on disk.
- [ ] Schema v1.0 themes (none currently exist; safety check) get a default typography dict via `_upgrade_to_v2()`.
- [ ] `generate_stylesheet()` emits `QLabel[typography="X"]` and `QLabel[section-header="X"]` for every X in the dict.
- [ ] The legacy `QLabel[section-header="true"]` selector is **kept as a deprecated alias** of `compact`. (Removed in Phase 1 DoD after the single call site is migrated.)
- [ ] All 4 themes render existing panels (home, settings, theme designer) **without any visual regression**. The deprecated alias guarantees the v1.3.0 settings panel section headers continue rendering correctly until Phase 1 explicitly migrates them.
- [ ] **Value verification:** Parse `generate_stylesheet(theme)` output and assert `QLabel[section-header="true"]` contains `font-size: 9px` and `letter-spacing: 2px`; assert `QLabel[typography="hint"]` contains color value matching the `nav_inactive_text` token (not `gold`). (F7 fix)
- [ ] Round-trip test: open a theme in the Theme Designer, edit a property, save. Verify the saved JSON file retains its `typography` section. (Validates B1 fix end-to-end.)
- [ ] Guard scripts pass.

---

## Status Log
| Date | Note |
|------|------|
| May 22, 2026 | Phase 0 implementation plan drafted. DOCUMENT_PROTOCOL-compliant structure with all 8 mandatory sections. 2 deviations documented (guard key count 5→4, per-entry color tokens). Audit corrections F1 (template compliance), F2 (per-entry color), F8 (f-string injection hazard), F9 (.get() fallback), F7 (value verification), F5 (no line numbers) applied. |
| May 23, 2026 | **Phase 0 SIGNED OFF.** All 11 DoD criteria met: `temp_verify_phase0.py` (10/10 runtime tests pass), `scripts/pre_commit_checks.py` (0 errors), manual round-trip test (save via Theme Designer → JSON retains typography section with all 4 keys). Two post-audit findings fixed: stale root `pre_commit_checks.py` deleted, `_to_dict` `schema_version` changed from hardcoded literal to `self.schema_version`. |
