# Dual-Template Protocol Review — May 19, 2026

Reviewed against all 8 foundational documents in the `docs/` directory.

---

## D1/D2/D3 Mapping

| Ref in Proposal | Actual File | Lines |
|---|---|---|
| **D1** | `Phase 1 — NDI Bridge + NDISender — Implementation Plan (Audited).md` | 1,034 |
| **D2** | `Phase 1 — Theme Engine v2 + DisplayWidget Extraction — Implementation Plan (Audited).md` | 947 |
| **D3** | `Phase 2 — Theme Designer UI — Implementation Plan.md` | 978 |

---

## 1. Accuracy of the "What This Fixes" Claims

The proposal lists 5 gaps. Here's what's actually true:

| Claim | Verdict | Evidence |
|---|---|---|
| "D2/D3 missing Hazards, DoD, Status Log" | **Half true** | D2 is missing Regression Hazards and Definition of Done. D3 has **all three** (Hazards lines 931–948, DoD lines 950–968, Status Log lines 970–980). The claim is correct for D2, incorrect for D3. |
| "D1 has pre-flight, D2/D3 don't" | **False** | D3 has Step 0 — Pre-Flight Verification (lines 172–188) with a full API contract table verifying 6 `DisplayWidget` signatures. D2 is the only one missing a standalone pre-flight section. |
| "D3 has unique SDK section" | **True** | D3's "Phase 1.5 Patches" (lines 9–56) documents 4 pre-applied patches + 3 deferred items. This is analogous to D1's "NDI SDK Dependency" section — both are phase-specific prerequisite blocks outside the core template. |
| "To Implement.md has no structure" | **True** | The file is overloaded — it mixes a version status tracker (what it should be) with full inline implementation plans for v1.1.0 phases 5–7, including code blocks, architecture decisions, and regression checklists. It should be a link index, not a container. |
| "No rule for when to use which doc" | **True** | The existing docs evolved organically. `ROADMAP.md` delegates to sub-roadmaps. Sub-roadmaps delegate to implementation plans. But there's no written rule, and the boundaries blur in practice (e.g., `To Implement.md` contains implementation detail). |

**Net verdict:** 2 claims are fully true, 1 is half true, 1 is false, 1 is true. The protocol would fix real problems but overstates two of them.

---

## 2. Existing Documentation: Structural Completeness Scores

### Sub-Roadmaps

| Document | Score | Strengths | Gaps |
|---|---|---|---|
| **v1.1.0 Advanced Display Modes** | **91%** | Full ADR, regression requirements, 7 phases with DoD, rollback strategy, milestones, guard checklists, verification scripts | Stale status (says "Planned"; v1.1.0 is done); no deviation tracking from ROADMAP |
| **v1.2.0 NDI Output** | **93%** | 4 formal ADRs with scoring rubric, 14 regression invariants, 5 phases with explicit Files Not Touched, operator safety guidelines, rollback strategy | No consolidated deviations section; 2 deviations (Phase 4, Part 3 skip) buried in completion notes |
| **v1.3.0 Theme Designer** | **82%** | 6 formal ADRs (best in class), cross-phase verification matrix, audit corrections applied, status log, deferred/out-of-scope with target versions | Missing guard checklists, verification scripts, rollback strategy, and milestones — all present in v1.1.0/v1.2.0. Regression from earlier sub-roadmaps. |

**Trend:** The sub-roadmaps got better at ADRs and got worse at process infrastructure (guard checklists, verification scripts, rollback). v1.3.0 is the most architecturally rigorous but the least operationally complete.

### Implementation Plans

| Document | Score | T1 | T2 | T3 | T4 | T5 | T6 | T7 | T8 |
|---|---|---|---|---|---|---|---|---|---|
| **D1 — NDI Bridge** | **74%** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **D2 — Theme Engine** | **69%** | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| **D3 — Theme Designer** | **94%** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

Template key: T1=Header, T2=Deviations, T3=Files Created/Modified/Not Touched, T4=Steps, T5=Pre-Commit Guards, T6=Verification Guards, T7=Regression Hazards, T8=Definition of Done

**D3 is the most structurally complete implementation plan in the repo.** It exceeds D1 (which lacks standalone Steps numbering) and far exceeds D2 (which is missing half the template sections).

---

## 3. The Proposed Templates vs. What Already Exists

### Proposed Sub-Roadmap Template (7 sections)

The proposal specifies: Executive Summary, ADR, Non-Regression, Phases, Cross-Phase Matrix, Status Log. 

**What the existing sub-roadmaps have that the proposal drops:**
- Pre-Commit Guard Checklist (v1.1.0 §8, v1.2.0 §8)
- Verification Script Checklist (v1.1.0 §9, v1.2.0 §9)
- Professional Design / Operator Safety Guidelines (v1.1.0 §10, v1.2.0 §10)
- Regression Testing Addendum template (v1.1.0 §7, v1.2.0 §7)
- Rollback Strategy (v1.1.0 §12, v1.2.0 §12)
- Suggested Milestones with risk levels (v1.1.0 §11, v1.2.0 §11)

These 6 sections exist in the 2 most complete sub-roadmaps. The proposed template includes **none of them**. If adopted as written, the template would *reduce* the completeness of sub-roadmaps from ~91% to roughly what it mandates — which is less.

**Recommendation:** Either add these 6 sections as optional extensions (with the "Template Deviations" rule covering them) or fold guard checklists and verification scripts into the Phases section explicitly.

### Proposed Implementation Plan Template (8 sections)

The proposal maps almost perfectly onto D3's actual structure. Every required section (header, deviations, files, steps, guards, hazards, DoD, status log) exists in D3. The template essentially codifies what D3 already does.

**What D3 has that the proposal doesn't require but should allow:**
- Preexisting patch documentation (Phase 1.5 Patches section)
- API contract table in Step 0

Both are covered by the "Template Deviations" rule (protocol rule #8).

**The only real template gap is in D2.** D2 is missing T5–T8. The protocol would mandate those — which is the right fix.

---

## 4. Protocol Rules: Feasibility Assessment

> **Note:** The original proposal had 8 rules. The final [DOCUMENT_PROTOCOL.md](./DOCUMENT_PROTOCOL.md) has 10 rules after synthesis. This table maps proposal rules to final protocol rules.

| Proposal # | Final # | Rule | Verdict | Notes |
|---|---|---|---|---|
| 1 | 1 | One sub-roadmap per version, one plan per phase | **Sound** | Already true in practice. Codifying it prevents `To Implement.md` from containing full plans. |
| 2 | 2 | Deviation format mandatory — plan→sub-roadmap | **Sound** | D1 (7 deviations), D2 (3), D3 (3) all use this format. It works. |
| — | 3 | Sub-roadmap→ROADMAP deviations mandatory | **Sound** (new) | Added during synthesis. v1.3.0 sub-roadmap's QML rejection should have been a formal deviation from ROADMAP.md. |
| 3 | 4 | Files Not Touched mandatory (plans) / Scope Exclusions (sub-roadmaps) | **Sound** | All 3 plans already do this. Sub-roadmaps now use narrative Scope Exclusions instead of file lists — synthesis refinement. |
| 4 | 5 | Pre-Flight mandatory | **Sound** | D1 and D3 already have it. D2 had it added during backfill. |
| 5 | 6 | Regression Hazards mandatory | **Sound** | D2 was the only violator. Fixed during backfill. |
| 6 | 7 | Definition of Done mandatory | **Sound** | D2 was the violator. Fixed during backfill. |
| 7 | 8 | Status Log mandatory | **Sound** | D1 and D3 have one. D2 had one added during backfill. |
| — | 9 | Sub-roadmap update triggers plan review | **Sound** (new) | Added during synthesis. Closes the gap where plans execute against stale sub-roadmaps. |
| 8 | 10 | Template deviations require justification | **Sound** | Already exists in practice via the audit protocol. Formalizing it is good. |

All 10 rules are feasible because most are already followed by at least 2 of the 3 documents of each type. The two new rules (3 and 9) close real process gaps identified during synthesis. The protocol doesn't invent new process — it standardizes what the best documents already do.

---

## 5. What the Protocol Doesn't Address

| Gap | Severity | Notes |
|---|---|---|
| **ROADMAP.md lacks ADRs** for categories 2–6 | Medium | Only v1.1.0 has a formal ADR in ROADMAP.md. The rest are undocumented at the master level. Sub-roadmaps fill this gap, but ROADMAP.md should at minimum summarize key decisions. |
| **Sub-roadmaps have no deviation tracking from ROADMAP** | Medium | Rule 2 mandates plan→sub-roadmap deviation tracking but not sub-roadmap→ROADMAP tracking. v1.3.0's QML rejection is an example of a sub-roadmap decision that contradicts an earlier assumption. |
| **v1.3.0 sub-roadmap is regressing on process quality** | High | It dropped 6 sections present in v1.1.0/v1.2.0. The proposed template would make this worse by not requiring those sections either. |
| **No template for ROADMAP.md itself** | Low | The master roadmap has no formal structure definition. It's the parent of all sub-roadmaps but has the weakest structural specification. |
| **Audit protocol integration** | Low | The existing `AUDIT_PROTOCOL.md` defines Passes S0–S4 (strategic) and 1–6 (implementation). The proposed templates should map explicitly to audit passes — e.g., "Section X satisfies Pass S1" — so a reviewer knows which template section feeds which audit pass. |

---

## 6. Recommendations

1. **Adopt the implementation plan template as-is.** ✅ Done — template adopted in DOCUMENT_PROTOCOL.md.

2. **Expand the sub-roadmap template.** ✅ Done — 6 extensions listed as optional with Rule 10 justification requirement.

3. **Add sub-roadmap→ROADMAP deviation tracking.** ✅ Done — Rule 3.

4. **Split `To Implement.md`** into a pure status tracker. ✅ Done — rewritten as 50-line link index. All legacy implementation content archived.

5. **Add a ROADMAP.md template section** to the protocol. ✅ Done — 7 required sections + 3 ROADMAP-specific rules added to DOCUMENT_PROTOCOL.md.

6. **Map template sections to audit passes.** ✅ Done at document level — hierarchy diagram shows Strategic passes (S0–S4) on sub-roadmaps, Implementation passes (1–6) on plans, Pass 6 on post-execution. Section-level granularity is not required.

7. **Backfill D2.** ✅ Done — T5 (Pre-Commit Guards), T6 (Verification Guards), T7 (Regression Hazards), T8 (Definition of Done), and Status Log added.

---

## Summary

The proposed dual-template protocol is **substantially correct**. It identifies a real inconsistency problem and proposes a structure that the best existing documents already demonstrate works. The 8 protocol rules are all feasible and mostly already practiced.

The proposal's **errors** are in its problem diagnosis: D3 is not missing Hazards, DoD, or Pre-Flight — D2 is. The proposal's **omissions** are in the sub-roadmap template, which drops 6 valuable sections from the existing gold-standard documents (v1.1.0 and v1.2.0). 

Adopt with the 7 recommendations above, and you'll have a protocol that standardizes what works, fixes what's broken, and doesn't regress on what's already good.

---

## 7. Post-Execution Update (v1.3.1 Phase 4)

The property-based QSS pattern (Decisions 1–6 in the v1.3.1 sub-roadmap) is now the codebase norm. All three primary operator panels (settings, home, theme designer) use `setProperty()`-based selectors with `generate_stylesheet()` as the single source of truth. Future panels (v1.4.0 transcript history, v2.0.0 sermon notes) inherit the system without inventing their own. The sub-roadmap's critical implementation rule is fulfilled: after v1.3.1, no operator-panel `.py` file shall contain `setStyleSheet()` with hardcoded rgba/hex values except for category-(a) per-row dynamic color call sites.
