# Software Engineering Deep Audit Protocol

A dual-layer methodology for verifying any plan, roadmap, or specification against its target codebase.

**Two layers:**
1. **Strategic Protocol (Passes S1-S4)** — for roadmaps, sub-roadmaps, architecture documents
2. **Implementation Protocol (Passes 1-5)** — for phase plans, implementation specs, pull requests

Apply the strategic protocol first. Only proceed to the implementation protocol when the strategic layer has passed.

---

## Precondition — Claims Inventory

Before starting any audit, read the document in full. Produce a numbered **Claims Inventory Table** with every factual assertion the document makes. This table is **mandatory** — no pass may begin before it is complete.

| ID | Category | Claim | Plan line | Target (file/method/value) |
|----|----------|-------|-----------|---------------------------|
| C1 | Constructor | `DisplayWidget.__init__` takes `display_controller` | :51 | `display_widget.py` |
| ... | ... | ... | ... | ... |

**Required categories (every plan must be checked for all):**

| Category | What to extract |
|----------|----------------|
| **API contracts** | Constructor signatures, method names, parameter lists, return types |
| **Line references** | Every `file:line` or `file:line-line` range claimed in the plan |
| **Values & constants** | Defaults, thresholds, config keys, enum variants, theme values |
| **Behavioral claims** | "X calls Y", "X guards against Z", "X rejects when...", mitigation claims in hazard sections |
| **Structural claims** | Class hierarchies, signal connections, file locations, import paths |
| **Scope declarations** | Every file listed under "Files Modified", "Files Created", "Files Not Touched" |
| **Decision claims** | Every architectural choice, deferral, rejection with its stated rationale |
| **Code-block imports** | Every `import` statement in every plan code block |

**Rules:**
- Every row must have a unique ID. No grouping multiple claims into one row.
- Code-block claims (steps showing pseudocode) count as claims about what the implementation should do — verify them against the plan's own API contracts and hazard mitigations.
- Hazard mitigations are behavioral claims. "`save_as` rejects when target path exists" must be verified against `save_as`'s code block.

---

## Pass 0 — Assumption Verification (Debugging Pre-Flight)

**Scope:** Any bug investigation, root-cause analysis, or behavioural debugging. Mandatory before any fix proposal.

**Question:** Every implicit belief about the bug's mechanism — is it true?

**Method:**

1. **List every assumption** you are making about how the system works. These are the things you are taking for granted without checking. Common categories:
   - Signal ordering ("signal X always fires before signal Y")
   - Default values ("the default for setting Z is `false`")
   - Code paths ("method A is never called when B is active")
   - State invariants ("variable V is always set before W is read")
   - Data flow ("caller C always passes a non-null argument")

2. **For each assumption, find the confirming or refuting evidence** in source code. Produce a `file:line` reference.
   - If the assumption is **confirmed**, move on.
   - If the assumption is **refuted**, correct your model and re-check any dependent logic.
   - If the assumption is **unverifiable** (no source path exists), flag it as a gap — do not proceed until it can be verified or re-framed.

3. **Tabulate the results** before writing any fix:

   | Assumption | Source evidence | Status |
   |-----------|-----------------|--------|
   | ... | `file:line` — reason | Confirmed / Refuted / Unverifiable |

**Failure pattern from real audit:** Auditor assumed `current_primary` stays unchanged when adding an overlay. A 5-second `grep` of `editors.py` for `current_primary` would have shown the assignment `self.current_primary = translation` fires on every checkbox check. The wrong assumption led to a dead-end analysis that stopped at a symptom (signal cascade) instead of reaching the root cause (the unconditional assignment).

**Failure pattern — helper function boundary leak:** Auditor assumed `_strip_extra()` only affected verse reference labels (its documented purpose), but a `grep` of call sites would have shown it was also applied to verse content across 3 rendering paths (`_render_fullscreen`, lower third, `DisplayPreview.forward_verse`). The `#` character and everything after it was silently stripped from displayed text. The assumption that "this utility only touches references" was never verified against actual call sites. When debugging content corruption, trace every data transformation the content passes through — not just the final rendering method. A function's documented intent is not its actual scope.

**Failure pattern — configuration propagation scope misattribution:** Auditor assumed a style rule on component A propagated laterally to sibling component B. In hierarchical component frameworks, style/configuration rules propagate along the defined scope (typically parent → descendant subtree), not across sibling boundaries. When debugging a visual or behavioral effect in one component, verify the actual propagation scope of the suspected rule — trace which components are in the rule's defined scope, not which components seem affected. Assuming browser-CSS-like lateral cascade in a framework with subtree scoping is a category error.

**Failure pattern — snapshot dependency on unresolved internal state:** When capturing a system snapshot (visual capture, data export, state serialization) for derivative output, the snapshot's validity depends on all internal state being fully resolved: layout geometry, cascading configuration precedence, animation completion, and processing queue clearance. Each unresolved dependency is a hidden assumption. Enumerate every state dependency the snapshot requires, verify each is resolved before capture, or bypass the dependency by reading source data directly instead of capturing live state.

**Failure pattern — rendering vs structural resolution independence:** In any UI or layout framework, forcing a visual repaint does not guarantee structural resolution (geometry calculation, layout assignment, state finalization). These are independent operations — one is visual, one is structural. When debugging "blank" or "zero-size" outputs after dynamic content insertion, verify structural resolution separately from visual rendering. The two must both be complete for correct output; completing one does not imply the other.

**Failure pattern — stacked symptom fixes masking root cause:** Fix A addresses symptom S1. Fix B addresses symptom S2. Both are committed. Root cause RC remains active. Later Fix C addresses RC. Fixes A and B remain in code despite being unnecessary or orthogonal to the actual root cause. When proposing a fix, verify it independently resolves the observed symptom when applied alone. If it doesn't, it is addressing a secondary issue, not the root cause. Layering fixes without independent verification creates dead code, obscures the real mechanism, and increases regression risk.

**Exit criterion:** Every assumption in the list must carry a `[Confirmed]` or `[Refuted]` status grounded in source evidence. Zero `[Unverifiable]` items are permitted before a fix proposal. If an assumption cannot be verified, state it explicitly as a known unknown — do not proceed without acknowledging the gap.

**Output:** A completed assumption table. This table is part of the audit record and must be included in the Post-Audit Report.

---

## Strategic Protocol — for Roadmaps & Sub-Roadmaps

### Pass S0 — Intra-Document Consistency

**Question:** Does the document agree with itself? No stale sections, no duplicate blocks, no contradictions between early and late sections.

**Method:**

1. **Scan for duplicate headings or sections.** Two identically-named sections in the same document means one is stale.
2. **Compare early descriptions with later specifications.** If §3.6 describes a button as "calls X via signal" but §5.3 describes it as "emits signal connected to X," flag the contradiction — only one can be correct.
3. **Check that every fix applied in a later section is reflected in all earlier sections that reference the same component.** If E5 adds `_confirm_discard_changes()` to slot wiring, every earlier mention of slot wiring must include it.
4. **Compare the Phase 1.5 Patches section against what the code actually shows.** If the plan claims 3 patches but the code has 4, flag the gap.

**Output:** List of internal contradictions, stale duplicate sections, and documentation gaps where a fix in one section isn't reflected elsewhere in the same document.

**Failure pattern:** Plan has two "Internal slot wiring:" sections — first pre-E5, second post-E5. Both remain in the document. Implementer reads the first and misses `_confirm_discard_changes()`. Edits silently discarded on theme switch.

---

### Pass S1 — Cross-Document Consistency

**Question:** Does this document agree with every other document it references or depends on?

**Method:**

1. List every external document referenced or implied: main ROADMAP, earlier sub-roadmaps, REGRESSION_TESTING.md, BUGFIX_LOG.md, To Implement.md, any ADR records.
2. For each referenced document, extract the relevant claims:
   - Architectural decisions (e.g., "use QML for preview")
   - Timeline estimates (e.g., "Phase 2: 1.5 weeks")
   - Feature scopes (e.g., "Phase 3 ships video backgrounds")
   - Technical stack specifications (e.g., "Display Rendering: QML")
3. Compare pairwise. Flag every direct contradiction.
4. Also flag orphan decisions — where one document commits to a position and the other never acknowledges it.

**Output:** List of cross-document contradictions and orphan decisions.

**Example:** Sub-roadmap Decision 1 rejects QML. Main ROADMAP lines 278, 290, 393 specify QML. The sub-roadmap has no deviation note acknowledging this conflict.

---

### Pass S2 — Decision Traceability

**Question:** Every decision in the document — where is it justified?

**Method:**

1. List every named decision: ADR entries, technology choices, scope cuts, feature deferrals.
2. For each decision, check if it has:
   - **Context:** What problem does this decision solve?
   - **Options considered:** At least two meaningful alternatives, including "do nothing."
   - **Rationale:** Why was this option chosen? Specific technical reasoning, not generic statements.
   - **Consequences:** What does this decision foreclose? What future work does it enable?
3. Flag any decision missing two or more elements as undermotivated.

**Output:** List of undermotivated decisions with missing elements noted.

**Examples of insufficient rationale:**
- "Option A scores 95/100, Option B scores 45/100" with no rubric
- "Deferred to future release" with no reason
- "Option C (12/100) rejected" with no explanation of why the score is so low

---

### Pass S3 — Timeline & Dependency Realism

**Question:** Are the phase durations and ordering backed by evidence?

**Method:**

1. For each phase, extract:
   - Number of files modified
   - Number of new files created
   - Number of new public APIs or classes
   - Whether a major refactor is required (e.g., class extraction, interface change)
2. Compare against historical velocity from the same project:
   - Which previous phase was most similar in scope?
   - How long did it actually take?
   - What went over schedule?
3. If no comparable phase exists, use industry benchmarks:
   - New file (single class, tested): 0.5-1 day
   - File modification with new logic: 0.5-1 day
   - Class extraction (refactor one class into two, ~500 lines): 2-3 days
   - API design + documentation: 0.5-1 day per API
   - Guard script creation or migration: 0.5-1 day
4. Check phase ordering:
   - Does Phase N create infrastructure that Phase N+1 needs? (Correct ordering)
   - Does Phase N+1 depend on a deliverable not listed in Phase N's DoD? (Ordering gap)
5. Estimate a realistic total with explicit assumptions.

**Output:** Realistic phase durations and total timeline, with delta from plan.

**Example:** Plan says Phase 1: 1 week. Files modified: 10, files created: 4, refactor required: DisplayWidget extraction (~900+ line scope change). Realistic: 2-3 weeks.

---

### Pass S4 — Deferred Item Integrity

**Question:** Every feature marked deferred or out of scope — is this credible?

**Method:**

1. List every deferred feature.
2. For each, check:
   - **Rationale:** Documented technical or strategic reason, or just deferral by default?
   - **External dependency:** Does it depend on something unavailable (missing library, unapproved vendor, incomplete hardware support)?
   - **Effort sense:** Is this truly high-effort/low-return, or is it being deferred because it's hard but strategically necessary?
   - **Regurgitation risk:** Will this feature cost significantly more to add after the current work than it would before? (Architectural lock-in.)
3. Flag items where deferral increases future cost.

**Output:** Deferred items sorted by credibility. Flagged items where deferral is strategic risk.

**Example of credible deferral:** MP4 video backgrounds. Rationale: downstream broadcast chain handles video compositing. Embedding it in the scripture display duplicates work and adds codec/GPU/NDI risk. No architectural lock-in — image backgrounds use the same slot.

**Example of risky deferral:** Path portability convention for theme assets. If deferred past the DisplayWidget extraction, the asset path convention must be retrofitted into every theme-loading codepath. Cost increases.

---

## Implementation Protocol — for Phase Plans & Implementation Specs

### Pass 1 — Claim Verification

**Question:** Does the plan correctly describe the current code?

**Method:**

For every empirical claim in the plan (file paths, line numbers, method names, default values, inheritance, signal connections, call chains):

1. Read the actual file at the claimed path.
2. If a line number is specified, read that exact line.
3. If the claim is about behavior (e.g., "X calls Y"), trace the call in source.
4. If the claim is about a value (e.g., "the default alpha is 0.72"), find the actual assignment.
5. Mark each claim: **Confirmed** / **Wrong** / **Unverifiable** (no path given).

**Exit criterion:** If any single claim is wrong (file doesn't exist, line number wrong by >5 lines, method doesn't exist, value doesn't match), report immediately and stop. A plan with a false claim about the current state cannot be trusted on the rest.

**Output:** Numbered table with every claim from the Claims Inventory (Pass 0.5). Every row must have a status. No grouping — "C1-C4, C6-C15: ✅ Confirmed" is prohibited. Each claim gets its own row with its own evidence.

| ID | Claim | Expected | Actual | File:Line | Status |
|----|-------|----------|--------|-----------|--------|
| C1 | `DisplayWidget.__init__` takes `display_controller` | `display_controller` | `display_controller` | `display_widget.py:51` | ✅ Confirmed |
| C2 | `set_theme(theme)` exists | method present | method present | `display_widget.py:94` | ✅ Confirmed |
| ... | ... | ... | ... | ... | ... |

**No row left blank.** If a claim from the inventory cannot be verified, mark it Unverifiable with a reason.

---

### Pass 2 — Dependency Chain Tracing

**Question:** Does the plan's scope estimate account for every dependency — both downward (what methods call) and upward (what callers must do after side effects)?

**Method:**

For every method, class, or function the plan says will be moved, extracted, refactored, or written:

**Downward trace (existing):**
1. **Read every method body** — not just the signature. Count every internal call it makes.
2. For each internal call (non-framework, non-stdlib), check if it's in the plan's scope list.
3. If it's not, it's a hidden dependency. Add it to a discovery list.
4. **Recurse:** Read each discovered method body. Repeat until every callee is either in the plan's scope or is a framework/library call.
5. Report the true scope: plan claims N items; trace reveals N+M items across K additional code paths.

**Upward trace (new):**
6. **For every operation with a side effect** (file I/O, registry mutation, resource allocation, signal emission), identify the caller in the plan's flow.
7. **Check postcondition handling:** After the operation completes, what must the caller do? Examples:
   - `Theme.delete()` unlinks the file → caller must drop the theme from `ThemeManager._themes` or call `reload_theme()` to detect the missing file.
   - `save_as()` mutates `self.id` → caller must ensure it operated on a deep copy.
   - `set_theme()` changes rendering state → caller must refresh affected widgets.
8. **Flag any unhandled postcondition** where the plan's flow description is vague ("theme_mgr removes from registry" without specifying the mechanism).

**Heuristic:** A method that calls 3 unlisted utility methods has 3 hidden dependencies. A utility method that is itself called by 4 different scope methods has 4 incoming dependencies. Both must be accounted for.

**Failure pattern — execution-path divergence in alternative rendering:** A framework's alternative execution path (offscreen capture, export mode, background rendering, test harness) may resolve configuration precedence differently than the primary (on-screen/foreground/production) path. A rule correctly overridden in the primary path may win in the alternative path due to different specificity resolution, different state initialization, or different entry points into the configuration cascade. When debugging behavioral differences between primary and alternative outputs, compare configuration precedence resolution in both paths — not just the primary.

**Output:** Delta report: "Plan claims N items. True scope is N+M items." Plus a postcondition gap list: "K side-effect operations with unspecified caller handling."

---

### Pass 3 — Constructor & Interface Audit

**Question:** If I build the plan's proposed API, will existing call sites work?

**Method:**

For every class the plan creates, refactors, or changes the constructor of:

1. **Read the current constructor.** List every parameter.
2. **Grep all call sites.** Count every place that constructs this class.
3. **Check each call site** against the plan's proposed new signature. Do the arguments match? If the plan adds a required parameter, every call site must be updated.
4. **Check for hidden dependencies.** Scan the class body for:
   - `QApplication.instance()` or any global instance access
   - `SettingsManager()` or any global factory instantiation mid-method
   - Hardcoded file paths, database queries, or network calls
   - Any call to a global/singleton that isn't injected through the constructor
5. For each hidden dependency, note whether the plan explicitly addresses it. If not, the class has a leaky abstraction — it works only when that global is available, making testing and isolated embedding impossible.

**Output:** List of call sites requiring update, list of hidden dependencies not addressed by the plan.

---

### Pass 4 — "Not Touched" Reality Check

**Question:** Every file the plan says it won't touch — can it actually stay untouched?

**Method:**

For every file under "Files Not Touched," "Unchanged," "Unmodified," or "Out of Scope":

1. **Trace the data flow.** Does this file create, configure, pass, or invoke any class that IS in the modified scope?
   - If A creates B, and B's constructor changes, A must pass new parameters. A is touched.
   - If A calls a method on B, and that method's signature changes, A is touched.
   - If A imports B, and B is renamed or moves, A is touched.
2. Repeat for every excluded file. One broken data flow = silent runtime failure.
3. Report any file that must be moved to "Files Modified."

**Output:** List of files that must be moved from "Not Touched" to "Modified."

---

### Pass 5 — Value Integrity Check

**Question:** Do the plan's constants, defaults, and configuration values match the actual codebase?

**Method:**

For every constant, default value, configuration key, enum variant, threshold, or whitelist/guard entry the plan specifies:

1. **Find the actual value** in the codebase. Check `constants.py`, JSON/YAML/TOML configs, `.env`, database migrations, QSS stylesheets, inline literals, whitelists, path validators, and guard functions.
2. **Compare against the plan's specification.** Write both values down.
3. If they differ:
   - Is the plan proposing a deliberate change? (Document as a change, not a mistake.)
   - Is the plan simply wrong about the current value? (Report as a factual error.)
   - Does the difference cause a behavioral regression? (Calculate the impact: value changes by X%, does behavior observably change?)
4. **For whitelists and guard functions:** Cross-reference every entry against the schema or data it protects. Flag entries that can never match (dead code in the plan's own guards).

**Output:** Table of values compared, with discrepancies flagged as change / error / regression risk / dead entry.

**Failure pattern from real audit:** `_is_v2_default_path` whitelist includes `"lower_third.transition."` — but transition paths are excluded from the Phase 2 schema. The entry will never match. Harmless but indicates the whitelist wasn't cross-referenced against the schema it guards.

---

### Pass 6 — Expression Fidelity (Implementation vs Plan)

**Question:** Does every code block in the plan's specification match the actual implementation at the sub-expression level?

**Scope:** Post-implementation only. Apply this pass when auditing a codebase against an already-approved plan. Skipped during pre-implementation plan review.

**Method:**

For every code block the plan specifies inline (pseudocode, code snippets, diff hunks, delta tables, API call sequences):

#### 6a — Statement-by-Statement Tracing

For each statement in the plan's code block:

1. **Find the corresponding statement** in the implementation file. If the plan specifies a method body, read the exact function/method in the implementation.
2. **Compare every sub-expression**, not just the outer structure. A plan that says:

   ```
   value = Constructor(arg1)
   value.mutate(someVar)
   consumer(value)
   ```

   must have all three statements — not just `Constructor(arg1)` and `consumer(value)` with the mutating call dropped.
3. **Flag any omission or substitution** where the plan specifies expression X but the implementation has expression Y at the equivalent position. Report the exact mismatch.

**Failure pattern:** Plan specifies a two-step sequence (construct + configure). Implementation skips the configure step. The configured parameter silently uses its default instead of the plan's value.

#### 6b — Dependency Declaration Completeness

For every external symbol used in the implementation:

1. **Build a usage set** from the implementation code: scan for every class, function, constant, module, or type that comes from outside the file or outside the language's standard library.
2. **Build a dependency set** from the file's declarations: every name that appears in import/include/use/require statements.
3. **Compute the difference:** usage − dependency = missing declarations. Every item here is a runtime `NameError` / `ReferenceError` / undefined symbol.
4. **Check the reverse:** dependency − usage = dead imports. Not a crash but indicates stale code or copy-paste residue.

**Failure pattern:** Implementation calls `ExternalClass.method()` but `ExternalClass` is never imported. Crash on first execution of that code path.

#### 6c — Structure Enumeration

For every data structure the plan defines with enumerated members (struct fields, dict keys, enum variants, config options, interface methods):

1. **Count the plan's members.** Write down every key or variant the plan defines.
2. **Count the implementation's members.** Read the actual struct/interface/config in source.
3. **Compare counts and names.** Report:
   - Missing members: in plan but not in implementation
   - Extra members: in implementation but not in plan
   - Renamed members: same semantic role but different name

**Failure pattern:** Plan specifies an interface with 10 fields. Implementation has 4 fields with different naming conventions. Any code written to the plan's spec silently fails (wrong keys, wrong indices, missing data).

#### 6d — Error/Failure Path Check

For every operation in the plan that can fail (file I/O, network call, type conversion, resource allocation, null-returning factory):

1. **Identify the failure mode** — does the plan include an error guard? (e.g., `if result is None:`, `try/except`, `result.isValid()`, `match { Ok => ..., Err => ... }`)
2. **Check implementation** — does it have the same guard? Does it have any guard at all?
3. **Report missing guards** — if the plan specifies a guard and the implementation drops it, that is a latent crash path or silent data corruption.

**Failure pattern:** Plan says `if image.isValid(): display(image) else: use_placeholder()`. Implementation calls `display(image)` with no validation. Display breaks silently when the image file is missing.

#### 6e — Control Flow/Structural Fidelity

For every conditional (`if/else`, `switch/match`, `try/catch`, loop) the plan specifies:

1. **Does the implementation have the same branches?** Same conditions? Same number of branches? Same nesting depth?
2. **Does each branch contain the correct statements?** Not just "something similar" but the exact assignments and calls the plan puts in each branch.
3. **Report flattened conditionals** — plan says `if X: A else: B`; implementation has `if X: A` with no `else` and B is not handled. Behavior changes when X is false.
4. **Report merged conditionals** — plan has two separate `if` blocks; implementation merges them into one. May or may not be correct — flag for auditor judgment.

**Failure pattern:** Plan has an `if X is None` guard with a fallback branch. Implementation omits the guard and unconditionally dereferences X. Crash when X is None.

---

**Exit criterion:** One wrong statement in a code-block trace fails the entire Pass 6. A plan's code specification is the implementation contract. If any expression in the implementation deviates from that contract without a documented deviation (in the plan's "Deviations" section), the implementation is not faithful. Report immediately and stop.

---

## Combined Workflow

```
Document or bug to audit
│
├── Run Precondition — build Claims Inventory Table. Mandatory.
│   Every pass below must reference claim IDs from this table.
│
├── Run Pass 0 (Assumption Verification) — mandatory before any other pass.
│   If any assumption remains Unverifiable: STOP. Do not proceed until
│   the gap is closed.
│
├── Is it a post-implementation audit (codebase vs approved plan)?
│   → Yes → Apply Implementation Protocol (Passes 1-5) first.
│            Then apply Pass 6 (Expression Fidelity).
│            Passes 1-5 verify the plan against the codebase.
│            Pass 6 verifies the implementation against the plan.
│            Both must pass. If either fails: REJECTED.
│
├── Is it a roadmap or sub-roadmap (architecture-level)?
│   → Yes → Apply Strategic Protocol (Passes S0-S4)
│   │        Pass S0 checks the document against itself.
│   │        If passes → for each implementable phase:
│   │                      Apply Claims Inventory + Pass 0, then Implementation Protocol (Passes 1-5)
│   │        If fails → return to author with S0-S4 findings
│   │
│   └── No → Is it an implementation plan, PR, or bug investigation?
│       → Yes → Apply Claims Inventory + Pass 0, then Implementation Protocol (Passes 1-5)
│       → No  → Apply judgement (test plan, release checklist, config change, etc.)
│
└── All passes clear → APPROVED
    Any pass fails → CONDITIONALLY APPROVED or REJECTED
```

---

## Post-Audit Report Template

```
## Audit Report: [Document Name]

### Claims Inventory (Precondition)

| ID | Category | Claim | Plan line | Target |
|----|----------|-------|-----------|--------|
| ... | ... | ... | ... | ... |

- N claims inventoried

### Pass 0 — Assumption Verification

- N assumptions listed
- N confirmed: [list]
- N refuted: [list]
- N unverifiable: [list — must be zero before fix proposal]

### Strategic Protocol

**Pass S0 — Intra-Document Consistency:**
- N duplicate/stale sections found: [list]
- N internal contradictions found: [list]

**Pass S1 — Cross-Document Consistency:**
- N references checked
- N contradictions found: [list]

**Pass S2 — Decision Traceability:**
- N decisions checked
- N undermotivated: [list with missing elements]

**Pass S3 — Timeline & Dependency Realism:**
- Plan duration: X weeks
- Evidence-based duration: Y weeks
- Delta: +Y-X weeks
- Key assumptions: [list]

**Pass S4 — Deferred Item Integrity:**
- N deferred items
- N credible: [list]
- N risky (future cost increase): [list]

### Implementation Protocol

**Pass 1 — Claim Verification:**
- Every claim from the Claims Inventory verified individually. No grouped rows.
- N claims confirmed, N wrong, N unverifiable
- [If any wrong: STOP and reject]

**Pass 2 — Dependency Chain Tracing (downward + upward):**
- Plan claims N items in scope
- Trace reveals N+M items across K additional code paths
- [List M unlisted dependencies with file:line]
- Postcondition gaps: K operations with unspecified caller handling [list]

**Pass 3 — Constructor & Interface Audit:**
- N classes with changed constructors
- N call sites checked
- N hidden dependencies found: [list with details]

**Pass 4 — "Not Touched" Reality Check:**
- N files listed as unchanged
- N must move to "Files Modified": [list with data flow trace]

**Pass 5 — Value Integrity Check:**
- N values checked (constants, config keys, whitelist entries, guard function members)
- N discrepancies: [list with plan value vs actual value]
- N dead whitelist/guard entries: [list]

**Pass 6 — Expression Fidelity (post-implementation only):**
- N code blocks traced, N mismatches found
- 6a (Statement tracing): N mismatches at [file:line] — [short description]
- 6b (Dependencies): N missing declarations: [list]; N dead imports: [list]
- 6c (Structures): N members count/name mismatches: [list]
- 6d (Error paths): N missing guards: [list]
- 6e (Control flow): N structural mismatches: [list]

### Verdict
APPROVED / CONDITIONALLY APPROVED / REJECTED

If Conditionally Approved: list exact conditions that must be met before full approval.
If Rejected: state minimum fix to re-enter review.
```

---

## Why This Works

| Pass | Failure Mode | Example |
|------|-------------|---------|
| **Claims Inventory** | Ungrouped claims hidden in narrative | Auditor claims "15 verified" but 25 were never checked; grouped "1-4, 6-28: confirmed" hides 20 unverified rows |
| 0 | Unverified assumption | Auditor assumed `current_primary` unchanged when adding an overlay; never checked `editors.py` for the assignment |
| 0 | Configuration propagation scope misattribution | Assumed style rule cascades laterally to sibling; framework only propagates parent → descendant subtree |
| 0 | Snapshot dependency on unresolved internal state | Visual capture depends on layout, CSS, animation, event-loop state — all must be resolved or bypassed by direct data reading |
| 0 | Rendering vs structural resolution independence | `repaint()` forces visual paint; `activate()` forces geometry calc. Neither implies the other; both needed for correct output |
| 0 | Stacked symptom fixes masking root cause | Fix A and Fix B address symptoms while root cause RC persists; independent verification reveals neither resolves the symptom alone |
| **S0** | Intra-document contradiction | Plan has two "Internal slot wiring:" sections; first is pre-E5, second is post-E5. Implementer reads the first and misses `_confirm_discard_changes()` |
| S1 | Cross-document contradiction | ROADMAP says QML; sub-roadmap rejects QML with no deviation note |
| S2 | Undermotivated decision | ADR score 95/100 with no rubric |
| S3 | Unrealistic timeline | 1 week for 10-file refactor with class extraction |
| S4 | Risky deferral | Deferring asset path convention past architectural lock-in |
| 1 | Plan describes code that doesn't exist | References a method that was renamed two sprints ago |
| 2 | Underestimated scope / unhandled postcondition | Plan claims `delete()` removes from registry but never specifies the mechanism; caller doesn't know to call `reload_theme()` |
| 2 (upward) | Side-effect postcondition gap | `delete()` unlinks file; registry still holds stale Theme. Plan says "theme_mgr removes from registry" but never specifies how |
| 2 (upward) | Execution-path divergence | Alternative rendering path (offscreen, export, test harness) resolves configuration precedence differently than primary path; rule correctly overridden on-screen may win offscreen |
| 3 | Missed API coupling | Plan changes constructor but doesn't update three call sites |
| 4 | Assumed incorrect isolation | Plan says "don't touch X" but data flow forces X to pass new params |
| 5 | Wrong baseline value / dead whitelist entry | Plan whitelist includes `"lower_third.transition."` but transition paths excluded from schema; entry never matches |
| 6 | Expression mismatch | Plan specifies construct+mutation+consume; implementation skips mutation |
| 6b | Missing dependency / dead import | Implementation uses `ExternalClass` but never imports it. Or imports `theme as theme_mod` then never references `theme_mod` |
| 6c | Structure member count mismatch | Plan defines 10 struct fields; implementation defines 4 with different names |
| 6d | Missing failure guard | Plan has `if result is not None:` guard; implementation omits it |
| 6e | Flattened/merged conditional | Plan has `if X: A else: B`; implementation has `if X: A` with no else |

Running all passes for a strategic document (S1-S4) takes 1-2 hours. Running all passes for an implementation plan (Passes 1-5 or 1-6) takes 2-4 hours. Running one pass takes 5-15 minutes and guarantees that failure mode goes undetected.
