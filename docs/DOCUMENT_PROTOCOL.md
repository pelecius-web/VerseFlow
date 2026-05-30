# VerseFlow Document Protocol

A dual-template protocol that enforces consistency across planning documents, with explicit rules for when to use which.

**Two document types:**

| Type | Purpose | When to use |
|---|---|---|
| **Sub-Roadmap** | Strategic: *what* and *why* — capabilities, phases, decisions, DoD | Before any code work begins. Defines the version's scope. |
| **Implementation Plan** | Tactical: *how* — exact steps, code blocks, line numbers, hazards | Before each phase starts. Derived from the sub-roadmap. |

**Related protocol:** [AUDIT_PROTOCOL.md](./AUDIT_PROTOCOL.md) — defines verification passes (S0–S4 strategic, 1–6 implementation) applied after documents are written. Sub-roadmap sections feed strategic passes; implementation plan sections feed implementation passes.

---

## Sub-Roadmap Template

### Required Sections (5)

```
# VerseFlow v{VERSION} {NAME} — Sub-Roadmap

> **Stage:** v{VERSION}
> **Roadmap Category:** Category {N} — {NAME}
> **Primary Goal:** {one-sentence objective}
> **Status:** Planned
> **Implementation Style:** {e.g., "Additive only. Zero regression."}

---

## 1. Executive Summary
- Capability list (bullet points)
- Critical implementation rule (blockquote)
- Explicitly deferred items (bullet points)

## 2. Architectural Decision Record
- Decision table: Option | Summary | Score | Decision
- "Why selected" rationale
- "Long-term direction" (if applicable)
- Architectural rules going forward

## 3. Non-Regression & Scope Exclusions
- Invariants that must hold (numbered list, narrative — not file lists)
- "What must not break" (specific files, signals, workflows)
- Scope boundaries (e.g., "NDI pipeline untouched")

## 4. Phases (1–N)
For each phase:
  ### Phase {N} — {NAME} ({duration})
  - Objective
  - Deliverables
  - Definition of Done (checkbox list)
  No implementation steps. No code blocks. The implementation plan owns all tactical sequencing.

## 5. Cross-Phase Verification Matrix
- Table: Test | Phase 1 | Phase 2 | ... | Phase N

---

## 6. Status Log
- Table: Date | Note

---

## Optional Extensions
The following sections from earlier sub-roadmaps may be included when applicable.
Omission requires documented justification under Template Deviations (Rule 8).
- Pre-Commit Guard Checklist
- Verification Script Checklist
- Professional Design / Operator Safety Guidelines
- Regression Testing Addendum
- Rollback Strategy
- Suggested Milestones (with risk levels)
```

---

## ROADMAP.md Template

The master roadmap is the root of the document hierarchy. It defines category-level scope, version releases, architecture invariants, and the ADRs that sub-roadmaps deviate from. Its content must be structured and precise enough for Rule 3 (sub-roadmap→ROADMAP deviation tracking) to function.

### Required Sections (7)

```
# VerseFlow Unified Roadmap

> **Last Updated:** {date}
> **Current Status:** {one-line summary}

---

## 1. Version Release Plan
- Table: Version | Categories | Description | Est. Duration | Status

## 2. Architecture Invariants
- Non-negotiable constraints all sub-roadmaps must preserve
- Core philosophy (e.g., dual-pane, state machine, production-first)
- Breaking these requires a formal deviation in the sub-roadmap (Rule 3)

## 3. Category {N} — {NAME} (v{VERSION})
For each category:
  ### 3.N Features
  - Feature table: Feature | Description | Status

  ### 3.N.1 Architecture Decisions
  - Abbreviated ADR: Decision | Options | Rationale | Score
  - One ADR entry per category-level decision
  - Sub-roadmaps reference these entries in their deviation sections

  ### 3.N.2 Implementation Phases
  - Phase table: Phase | Duration | Deliverables | Status

## 4. Technical Stack
- Table: Layer | Technology

## 5. Data Models & Schema (if applicable)
- Cross-version data contracts (e.g., `.verseplaylist` format, theme schema)
- Sub-roadmaps must not break these without a documented deviation

## 6. Changelog
- Table: Date | Version | Changes

## 7. Status Log
- Table: Date | Note
```

### Rules Specific to ROADMAP.md

- **Category-level ADRs are mandatory.** Every category must have at least one formal ADR entry (3.N.1) if the category introduces a new architectural decision. This is what sub-roadmaps deviate from under Rule 3.
- **Version table is the single source of truth.** Sub-roadmap status fields, To Implement.md checkboxes, and the ROADMAP version table must agree. If they don't, the ROADMAP is authoritative.
- **Stale sections must be removed or marked archival.** The "File Organization" section, dev logs, and inline implementation checklists belong in sub-roadmaps or To Implement.md — not ROADMAP.md. Link to them, don't duplicate.

---

## Implementation Plan Template

### Required Sections (8)

```
# Phase {N} — {NAME}
## Implementation Plan (v{VERSION})

> **Status:** {Planned / In Progress / Complete}
> **Audit basis:** {description}
> **Sub-roadmap deviations:** {count} intentional (documented below)

---

## Deviations from Sub-Roadmap
### Deviation {N} — {title}
- **Sub-roadmap says:** {quote}
- **Plan says:** {what actually happens}
- **Justification:** {why}

## Files Created
- `{path}` — {description, line count}

## Files Modified
- `{path}` — {description, what changes}

## Files Not Touched
- `{path}` — {reason it can stay untouched}

## Step 0 — Pre-Flight Verification
- API contract table: Required by plan | Present in code | Status

## Step {N} — {title}
- Detailed pseudocode with exact line references
- Before/after diffs where applicable
- Rationale for non-obvious choices

## Regression Hazards
- Hazard | Risk | Mitigation (one per row)

## Definition of Done
- Checkbox list (testable, not aspirational)

## Status Log
- Table: Date | Note
```

---

## Protocol Rules

1. **One sub-roadmap per version.** One implementation plan per phase.

2. **Deviation format is mandatory — plan→sub-roadmap.** Every plan deviation from its parent sub-roadmap must use the three-line format:
   - **Sub-roadmap says:** {quote from sub-roadmap}
   - **Plan says:** {what actually happens}
   - **Justification:** {why}

3. **Sub-roadmap→ROADMAP deviations are mandatory.** Every sub-roadmap must document intentional deviations from ROADMAP.md using the same three-line format. Place this in a "Deviations from ROADMAP" section after the ADR.

4. **Files Not Touched is mandatory — in plans only.** Every plan must explicitly list what it does NOT touch and why. Sub-roadmaps use Scope Exclusions instead (narrative boundaries, not file lists).

5. **Pre-Flight is mandatory.** Every plan must verify API contracts before Step 1. Include a table: Required by plan | Present in code | Status.

6. **Regression Hazards is mandatory.** Every plan must list risks and mitigations.

7. **Definition of Done is mandatory.** Every plan and every sub-roadmap phase must have a checkbox DoD.

8. **Status Log is mandatory.** Every document must have a status log table with dated entries.

9. **Sub-roadmap updates trigger plan review.** When a sub-roadmap is updated after a plan exists, the plan owner must review the diff. If any deviation, deliverable, or DoD item is affected, the plan must be updated before the next phase begins.

10. **Template deviations require justification.** If a plan or sub-roadmap omits or adds a section, it must document why in a "Template Deviations" section at the end.

    **Example of a valid template deviation:**
    *"The v1.2.0 NDI sub-roadmap adds an 'NDI SDK Integration' section not in the template. Justification: ctypes bridge architecture has no analog in other categories."*

    **Example of a valid omission:**
    *"This sub-roadmap omits the Rollback Strategy extension. Justification: Phase 1 is extract-only with zero behavioral change — rollback is `git checkout` of the original file."*

---

## To Implement.md

After protocol adoption, `To Implement.md` is a **status tracker only**. It contains:

- (a) Links to sub-roadmaps
- (b) Links to implementation plans
- (c) Phase status checkboxes

No implementation steps. No code. No architecture decisions.

---

## Document Hierarchy

```
ROADMAP.md                      — Master plan, category-level scope, version releases
  └── vX.Y.Z — Sub-Roadmap.md   — Strategic scope for one version
        │                           ← Audited by Strategic passes (S0–S4)
        └── Phase N — Implementation Plan.md  — Tactical execution for one phase
              │                           ← Audited by Implementation passes (1–6)
              └── (Code implementation)
                    └── (Post-execution audit)  — Pass 6: Expression Fidelity
```

Audits verify the document's accuracy against the codebase *before* implementation. A post-execution audit (Pass 6) verifies the implementation matches the plan *after* code is written. See [AUDIT_PROTOCOL.md](./AUDIT_PROTOCOL.md) for the full verification methodology.

`To Implement.md` sits alongside this hierarchy as a pure index — it links to sub-roadmaps and plans, and tracks completion status, but duplicates nothing.
