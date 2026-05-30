# VerseFlow v1.0.0 RC Regression Testing Checklist

> **Version**: v0.7.12 → v1.0.0 RC  
> **Date**: April 23, 2026  
> **Status**: Ready for execution  

This document provides a structured checklist for validating all fixes and features before v1.0.0 RC release.

---

## 1. v0.7.2 Stabilization Bug Fixes (6 fixes)

### 1.1 Entry Identity Model (P0)
- [x] Create playlist with 3 verse entries
- [x] Save and close playlist
- [x] Reopen playlist
- [x] Verify all 3 entries retain their identity (same `entry_id`)
- [x] Drag-drop reorder entries
- [x] Verify identities remain stable after reorder
- [x] Save, close, reopen
- [x] Verify identities preserved across save/load cycle

**Pass Criteria**: No UUID regeneration, no duplicate entries, no lost entries.

### 1.2 Dirty State Tracking (P0)
- [x] Open existing `.verseplaylist` file
- [x] Modify queue (add verse)
- [x] Verify window title shows "*" or "modified" indicator
- [x] Try to close without saving
- [x] Verify "Save changes?" dialog appears
- [x] Click "Cancel" and remain in app
- [x] Save file
- [x] Verify "*" indicator removed from title
- [x] Try to close
- [x] Verify no "Save changes?" dialog (clean state)

**Pass Criteria**: Dirty state accurately tracked; dialogs appear only when needed.

### 1.3 Backup Integrity (P1)
- [x] Open existing playlist
- [x] Save multiple times (5+ saves)
- [x] Check `.backups/` directory
- [x] Verify `.bak1`, `.bak2`, `.bak3` exist (rotation working)
- [x] Corrupt current playlist file (delete half with text editor)
- [x] Try to open in VerseFlow
- [x] Verify error message with option to restore from backup
- [x] Restore from `.bak1`
- [x] Verify playlist loads successfully

**Pass Criteria**: Backups created on every save; rotation limits to 3 files; restore function works.

### 1.4 File Error UX
- [x] Try to open non-existent file via File > Open
- [x] Verify graceful error message (not crash)
- [x] Try to save to read-only directory
- [x] Verify helpful error message explaining permission issue
- [x] Try to open malformed JSON `.verseplaylist`
- [x] Verify error message indicates "corrupted file" with suggestion to restore backup

**Pass Criteria**: All errors caught, user-friendly messages, no crashes.

### 1.5 Drag-Drop Fixes
- [x] Drag verse from search results to queue
- [x] Verify verse appears in queue
- [x] Drag verse from queue to playlist
- [x] Verify verse appears in playlist
- [x] Reorder items within playlist via drag-drop
- [x] Verify order persists after save/load
- [x] Try drag-drop with malformed data (simulate by editing JSON mid-drag if possible)
- [x] Verify graceful rejection (no crash)

**Pass Criteria**: All drag-drop operations work; malformed data rejected safely.

### 1.6 Document Lifecycle Edge Cases
- [x] New playlist → Add items → Save As → Verify file created
- [x] Open playlist → Delete all items → Save → Verify empty but valid file
- [x] Open playlist → Modify → Save As with new name → Verify original unchanged
- [x] Rapid New/Open/Close cycles (5 times)
- [x] Verify no memory leaks or crashes

**Pass Criteria**: All lifecycle operations stable; no crashes or data loss.

---

## 2. Global Hotkeys Background Functionality

### 2.1 Basic Hotkey Registration
- [x] Open Settings dialog
- [x] Verify hotkeys displayed: `Ctrl+Shift+V`, `Ctrl+Shift+X`, `Ctrl+Shift+Q`, `Ctrl+Shift+L`
- [x] Note any "conflict" warnings

### 2.2 Background Operation (Critical)
- [x] Start VerseFlow
- [x] Load a verse in navigator
- [x] Click verse card to highlight
- [x] **Minimize VerseFlow window**
- [x] Press `Ctrl+Shift+V`
- [x] Restore VerseFlow window
- [x] Verify verse went LIVE (display preview shows verse, history updated)

- [x] Highlight different verse
- [x] Switch to another application (Notepad, Browser)
- [x] Press `Ctrl+Shift+V`
- [x] Switch back to VerseFlow
- [x] Verify correct verse went LIVE

### 2.3 Clear Hotkey (`Ctrl+Shift+X`)
- [x] Put verse LIVE
- [x] Switch to background app
- [x] Press `Ctrl+Shift+X`
- [x] Return to VerseFlow
- [x] Verify display cleared (black screen or placeholder)

### 2.4 Queue Add Hotkey (`Ctrl+Shift+Q`)
- [x] Highlight verse in navigator
- [x] Switch to background app
- [x] Press `Ctrl+Shift+Q`
- [x] Return to VerseFlow
- [x] Verify verse added to queue panel

### 2.5 Focus Search Hotkey (`Ctrl+Shift+L`)
- [x] Put cursor in random widget
- [x] Press `Ctrl+Shift+L`
- [x] Verify search input focused and text selected

**Pass Criteria**: All 4 hotkeys work when app is not focused (Windows native hotkey API functional).

---

## 3. Cross-Platform Behavior

### 3.1 Windows (Primary Platform) - Already Tested Above
All previous tests run on Windows.

### 3.2 Linux/macOS Fallback (If Available)
- [ ] Start VerseFlow on Linux/macOS
- [ ] Verify fallback hotkey warning in status bar
- [ ] Verify hotkeys work only when app is focused (fallback behavior)
- [ ] Verify no crashes on hotkey registration failure

**Note**: Full Linux/macOS testing deferred to v1.1+ unless developer machine available.

---

## 4. v0.7.10 Critical Fixes Verification

### 4.1 Drag-Drop Malformed JSON (safe_json_loads)
- [x] Create file `test_malformed.verseplaylist` with invalid JSON:
  ```json
  {"version": "1.0", "items": [null, undefined, {"type": "verse"}]}
  ```
- [x] Try to open in VerseFlow
- [x] Verify graceful error (not crash)
- [x] Verify error message mentions "malformed JSON"

- [x] Create file with type confusion:
  ```json
  {"version": "1.0", "items": "not an array"}
  ```
- [x] Try to open
- [x] Verify graceful handling

- [x] Create file with null bytes:
  ```json
  {"version": "1.0\u0000", "items": []}
  ```
- [x] Try to open
- [x] Verify rejection without crash

### 4.2 Settings Persistence (platformdirs)
- [x] Open Settings dialog
- [x] Change theme to different value
- [x] Close VerseFlow completely
- [x] Reopen VerseFlow
- [x] Verify theme setting persisted
- [x] Check settings location: `%APPDATA%\VerseFlow\settings.json` (Windows)
- [x] Verify file exists and contains modified theme

### 4.3 Cross-References Error Exposure
- [x] Temporarily rename `data/cross_references.json` to `data/cross_references.json.bak`
- [x] Start VerseFlow
- [x] Verify status bar shows warning: "⚠️ Cross-reference file not found: ..."
- [x] Verify app continues to function (no crash)
- [x] Restore file
- [x] Restart app
- [x] Verify cross-references load normally

---

## 4.4 Additional Type Safety Fixes (April 26, 2026)

### 4.4.1 QShortcut Import Error
- [x] Verify app launches without ImportError on PyQt6
- [x] Verify fallback hotkeys work when global registration fails
- [x] Verify all 4 hotkeys register successfully

### 4.4.2 Defensive Type Checking Throughout JSON Pipeline
- [x] Verify `playlist_panel.py:add_verse()` validates verse_dict is dict
- [x] Verify `playlist_panel.py:dropEvent()` validates items is list and each item is dict
- [x] Verify `queue_panel.py:add_verse()` validates verse is dict
- [x] Verify `queue_panel.py:add_verses_from_list()` validates verses is list
- [x] Verify `home_panel.py:_preview_queued_verse()` validates verse is dict
- [x] Verify `home_panel.py:_push_verse()` validates verse is dict
- [x] Verify `home_panel.py:set_preview_verse()` validates verse is dict or None
- [x] Verify drag-drop with malformed data is rejected gracefully
- [x] Verify no regressions to existing functionality

---

## 5. Modularization Audit Fixes (v0.7.12)

### 5.1 Signal-Based Navigation
- [x] Click "Home" tab in sidebar
- [x] Verify Home panel displayed
- [x] Click "Settings" tab
- [x] Verify Settings panel displayed
- [x] Verify no console errors about missing `parent()`

### 5.2 History Click Restoration
- [x] Push 3 different verses LIVE
- [x] Click first history entry
- [x] Verify correct verse restored to display
- [x] Click second history entry
- [x] Verify correct verse restored
- [x] Verify no console errors

### 5.3 Logging Infrastructure
- [x] Start VerseFlow from terminal with logging:
  ```bash
  python -m "2. Source Code" 2>&1 | findstr "INFO\|ERROR\|DEBUG"
  ```
- [x] Perform search operation
- [x] Verify log output appears (INFO level messages)
- [x] Verify no raw `print()` output in console

### 5.4 Database Encapsulation
- [x] Search for verse "John 3:16"
- [x] Verify results appear
- [x] Switch translation in navigator
- [x] Verify chapter reloads with new translation
- [x] Verify no direct SQL errors exposed to user

### 5.5 State Mutation Prevention
- [x] Enable 2+ translations in overlay menu
- [x] Push verse LIVE
- [x] Verify overlay displays correctly
- [x] Disable translations
- [x] Verify overlay clears properly
- [x] Verify no `AttributeError` or direct mutation errors

---

## 6. Keyword Search Improvements (May 1, 2026)

### 6.1 Wildcard Escaping (P1)
- [x] Search for `100%` in Keyword Search mode
- [x] Verify results only contain literal "100%" (no false matches like "1000 talents")
- [x] Search for `_od` (with underscore)
- [x] Verify results only contain literal "_od" (no false matches like "God", "Rod")
- [x] Search for backslash-containing terms if any exist in Bible
- [x] Verify literal match (no wildcard behavior)

**Pass Criteria**: `%`, `_`, `\` treated as literals, not SQL wildcards.

### 6.2 Canonical Bible Ordering (P1)
- [x] Search for common word `love` in Keyword Search
- [x] Verify first result is from Genesis (Genesis 1)
- [x] Verify last result is from Revelation (Revelation 22)
- [x] Verify results are in Genesis → Revelation order by book, then chapter, verse
- [x] Search for `light`
- [x] Verify Genesis results appear before Revelation results

**Pass Criteria**: All keyword search results ordered canonically (Genesis → Revelation).

### 6.3 Result Count Badge (P1)
- [x] Search for common word `the` in Keyword Search
- [x] Verify count label shows "Showing 50 of X results" (where X > 50)
- [x] Search for rare phrase `fishers of men`
- [x] Verify count label shows "2 results" (or small number)
- [x] Search for single word `faith`
- [x] Verify count label shows result count (not capped)
- [x] Verify count label is right-aligned and styled correctly

**Pass Criteria**: Count badge accurately displays total and indicates when results are capped at 50.

### 6.4 Match Highlighting (P1)
- [x] Search for `eternal life` in Keyword Search
- [x] Verify "eternal" and "life" are bolded/gold in result card verse text
- [x] Search for `"God so loved"` (quoted)
- [x] Verify "God so loved" is bolded/gold as a phrase
- [x] Search for single word `faith`
- [x] Verify "faith" is bolded/gold in results
- [x] Verify highlighting is case-insensitive (matches "Faith" and "faith")

**Pass Criteria**: Matched search terms visually highlighted (bold/gold) in all result cards.

### 6.5 Tiered Relevance — Phrase Promotion (P0)
- [x] Search for `fishers of` in Keyword Search (KJV)
- [x] Verify Matthew 4:19 ("fishers of men") appears in results
- [x] Verify Mark 1:17 ("fishers of men") appears in results
- [x] **Critical**: Verify Matt 4:19 and Mark 1:17 appear **before** Jer 16:16 and Ezek 47:10
- [x] Verify no noise results (verses with "fishers" and "of" separately) before the exact phrase matches

**Pass Criteria**: Exact phrase matches (Tier 1) appear before AND-word matches (Tier 2).

### 6.6 Tiered Relevance — Tier 2 Backfill (P1)
- [x] Search for `fishers of` in Keyword Search
- [x] Verify results include both Tier 1 (exact phrase) and Tier 2 (AND-word) verses
- [x] Verify Tier 2 verses do not duplicate Tier 1 verses
- [x] Verify total count label shows correct total (AND-word matches, not just Tier 1)
- [x] Search for phrase with few exact matches (e.g., `bread of life`)
- [x] Verify Tier 2 backfills remaining slots after Tier 1

**Pass Criteria**: Tier 2 fills remaining result slots without duplicating Tier 1.

### 6.7 Tiered Relevance — Single Word Unchanged (P1)
- [x] Search for single word `love` in Keyword Search
- [x] Verify results are identical to previous behavior
- [x] Verify results are ordered canonically
- [x] Verify count badge works correctly
- [x] Search for `faith`
- [x] Verify no regression from previous single-word search behavior

**Pass Criteria**: Single-word searches unchanged by tiered relevance implementation.

### 6.8 Tiered Relevance — Quoted Phrase Unchanged (P1)
- [x] Search for `"fishers of men"` (quoted) in Keyword Search
- [x] Verify only exact phrase matches returned
- [x] Verify results are identical to previous quoted-phrase behavior
- [x] Search for `"God so loved the world"` (quoted)
- [x] Verify only exact phrase matches
- [x] Verify count badge shows correct total

**Pass Criteria**: Quoted-phrase searches unchanged by tiered relevance implementation.

### 6.9 Verse Lookup Fallback — Space-Separated References (P1)
- [x] Switch to "Verse Lookup" mode
- [x] Type `John 3 16` (space-separated, no colon)
- [x] Press Enter
- [x] Verify John 3 chapter loads in navigator
- [x] Verify verse 16 is highlighted
- [x] Try `1 Samuel 3 16`
- [x] Verify chapter loads correctly

**Pass Criteria**: Space-separated references (e.g., "John 3 16") work in Verse Lookup mode.

### 6.10 Search Fallback in Verse Lookup Mode (P1)
- [x] Switch to "Verse Lookup" mode
- [x] Type non-reference query `faith`
- [x] Press Enter
- [x] Verify results fall back to keyword search
- [x] Verify keyword results panel is displayed
- [x] Verify count badge shows correct total

**Pass Criteria**: Verse Lookup mode gracefully falls back to keyword search for non-reference queries.

### 6.11 _processing_search Flag Leak Prevention (P0)
- [x] Perform keyword search
- [x] Verify search input re-enables after results load
- [x] Perform verse lookup that falls back to keyword
- [x] Verify search input re-enables after results
- [x] Verify no Enter key interception after search completes

**Pass Criteria**: `_processing_search` flag always reset on all exit paths (no leak).

---

## 7. Performance Validation (Quick Checks)

### 7.1 Large Playlist (Smoke Test)
- [x] Create playlist with 50+ items
- [x] Save and reopen
- [x] Verify load time < 2 seconds
- [x] Drag-drop reorder large playlist
- [x] Verify responsiveness

### 7.2 Undo/Redo Stress
- [x] Perform 20 operations (add, remove, reorder)
- [x] Undo all 20 (Ctrl+Z 20 times)
- [x] Verify back to initial state
- [x] Redo all 20 (Ctrl+Shift+Z 20 times)
- [x] Verify back to final state

### 7.3 Display Font Fitting (Visual Check)
- [x] Push verse with long text (Psalm 119:1-10)
- [x] Resize display preview panel
- [x] Verify font auto-adjusts to fit
- [x] Maximize window
- [x] Verify text remains readable

---

## Sign-Off

| Tester | Date | Result |
|--------|------|--------|
|        |      | [ ] PASS / [ ] FAIL |

**Notes**:
- Mark each item with `[x]` when tested
- Document any failures with error messages and reproduction steps
- All items must pass for v1.0.0 RC approval

---

## 8. v1.1.0 Advanced Display Modes

### 8.1 ChannelManager Main Regression
- [x] Existing navigator push targets Main
- [x] Existing clear targets Main
- [x] Queue push targets Main
- [x] Playlist push targets Main
- [x] History restore works

### 8.2 Lower-Third Rendering
- [x] Lower-third appears at bottom only
- [x] Logo placeholder area is reserved
- [x] Separator appears between logo and text
- [x] Long verse does not clip
- [x] Clear removes lower-third UI

### 8.3 Dual Channel Independence
- [x] Push Main does not update Alt
- [x] Push Alt does not update Main
- [x] Clear Alt does not clear Main
- [x] Push All updates both
- [x] Clear All clears both

### 8.4 Preview Tabs
- [x] Main preview updates from Main state
- [x] Alt preview updates from Alt state
- [x] Hotkey push updates Main preview
- [x] Clear updates correct preview

### 8.5 Settings and Theme Foundation
- [x] Channel mode persists after restart
- [x] Missing settings fallback safely
- [x] Invalid mode fallback safely
- [x] Invalid logo path fallback safely

### 8.6 Full Manual Matrix
- [x] Main fullscreen — existing display behavior unchanged
- [x] Main lower-third — bottom-band layout works with logo placeholder
- [x] Alt fullscreen — independent second fullscreen output
- [x] Alt lower-third — independent second lower-third output
- [x] Push Main — only Main changes
- [x] Push Alt — only Alt changes
- [x] Push All — both channels change
- [x] Clear Main — only Main clears
- [x] Clear Alt — only Alt clears
- [x] Clear All — both clear
- [x] Hotkey Push — Main default works
- [x] Hotkey Clear — Main default clears
- [x] Queue Push — Main default works
- [x] Playlist Push — Main default works
- [x] History Restore — restores expected Main behavior
- [x] Mode Switch — re-renders current verse
- [x] Settings Persist — modes/themes/logo placeholders persist
- [x] Invalid Settings — safe fallback, no crash
- [x] Long Verse — no clipping
- [x] Multi-translation — no overflow or stale widgets
- [x] App Startup — no crash with missing settings

---

## 9. Critical Display Mode Transition Regression

### 9.1 Live Fullscreen ↔ Lower-Third Switching
- [x] Start VerseFlow with an external display available
- [x] Push a verse live in fullscreen mode
- [x] Switch Main mode from fullscreen to lower-third while the verse remains live
- [x] Verify lower-third renders with transparent upper area and only the bottom band visible
- [x] Switch Main mode from lower-third back to fullscreen while the verse remains live
- [x] Verify fullscreen renders cleanly with no lower-third ghost layer underneath
- [x] Repeat live fullscreen ↔ lower-third switching at least 5 times
- [x] Verify no opaque upper region, no stacked modes, no visible window frame, and no accumulating compositor ghost layers

**Pass Criteria**: Live mode changes recreate the physical display window and re-render the current verse cleanly. Clear-before-switch and live-switch paths both remain stable.

**Implementation Invariant**: Do not reintroduce live in-place mutation between fullscreen and lower-third native window modes. While a verse is live, mode changes must use `DisplayController.recreate_display_window_for_mode(mode)` through `DisplayChannel.set_display_mode()`.

---

## 10. v1.1.2 Lower-Third Typography Refactoring

### 10.1 Independent Reference Font Fitting
- [x] Push a verse to lower-third display
- [x] Verify reference text (e.g. "JOHN 3:16 — KJV") is rendered in bold gold at a consistent size regardless of verse length
- [x] Push a short verse (John 11:35) — verify ref font does not become excessively large
- [x] Push a long verse (Esther 8:9) — verify ref font remains readable and verse font fills the remaining space
- [x] Verify the ref font size is consistent between short and long verses (it should NOT scale with verse font)

**Pass Criteria**: Reference font is independent of verse font — same ref size for short and long verses.

### 10.2 Square Logo Placeholder
- [x] Set Main to lower-third mode
- [x] Push a verse to live
- [x] Verify the logo placeholder is a **square** (equal width and height), not a tall rectangle
- [x] Verify the square logo is centered horizontally in the logo container
- [x] Verify there is visible space below the logo square within the band

**Pass Criteria**: Logo placeholder is visibly square with empty space below it.

### 10.3 Church Alias Label
- [x] Open Settings → General → Church Alias
- [x] Enter "G A Zone" and press Enter (or click away)
- [x] Restart VerseFlow
- [x] Verify "G A Zone" is still in the Church Alias field (persistence)
- [x] Push a verse to lower-third display
- [x] Verify "G A Zone" appears below the square logo in bold gold text
- [x] Clear the church alias field (empty string)
- [x] Push a verse to lower-third display
- [x] Verify the church alias area is empty (label hidden, no space taken)

**Pass Criteria**: Church alias displays when set, disappears when empty, persists across restarts.

### 10.4 Church Alias Font Fitting (Abbreviation Stress Test)
- [x] Set church alias to "LWC" (very short)
- [x] Push verse — verify alias renders at a readable size
- [x] Set church alias to "FBC Springfield" (medium)
- [x] Push verse — verify alias wraps but stays within the band
- [x] Set church alias to "First Baptist Church of Springfield" (long — should gracefully hide)
- [x] Push verse — verify alias is hidden (no clipping, no visual glitch)
- [x] Verify verse and reference text are unaffected by church alias presence/absence

**Pass Criteria**: Short/medium abbreviations render; long names gracefully hide; verse/ref unaffected.

### 10.5 Lower-Third Text Column Unchanged
- [x] Push John 3:16 — verify verse text and reference appear correctly
- [x] Push Esther 8:9 — verify long verse scales down without clipping
- [x] Enable 2 translations — verify only primary renders in LT (no overlay overflow)
- [x] Resize the display window — verify LT band and fonts re-scale correctly

**Pass Criteria**: Text column behavior identical to v1.1.1 — no regression from square logo or church alias changes.

### 10.6 Mode Switching While Live
- [x] Push verse to live in fullscreen
- [x] Switch to lower-third while live — verify clean transition with no ghost overlay
- [x] Switch back to fullscreen while live — verify clean transition
- [x] Repeat 5 times — verify no accumulating ghost layers or visual artifacts

**Pass Criteria**: All mode transitions clean, same as post-Bug-50 fix.

---

## 11. v1.2.0 NDI Phase 1 Manual Tests (May 8, 2026)

### 11.1 NDI Discovery
- [x] Launch VerseFlow with NDI SDK DLL present
- [x] Open OBS, add NDI Source
- [x] Verify `"VerseFlow Main"` appears in the NDI source picker

### 11.2 Live Feed
- [x] Push a verse to Main (fullscreen mode)
- [x] Verify NDI feed appears in OBS with verse text visible
- [x] Verify FPS counter shows ~30fps (check logs: `Render took X.Xms`)

### 11.3 Clear Transition
- [x] Clear the display
- [x] Verify NDI feed goes to "No Signal" (sender destroyed — NOT a frozen frame)
- [x] Push verse again
- [x] Verify feed resumes

### 11.4 Push/Clear Cycle
- [x] Push → Clear → Push → Clear (3 cycles)
- [x] Verify sender starts/stops correctly at each transition
- [x] Verify no stale handles or frozen frames in OBS

### 11.5 Graceful Fallback — Missing DLL
- [x] Rename or remove `Processing.NDI.Lib.x64.dll`
- [x] Launch VerseFlow
- [x] Verify app launches normally — no crash
- [x] Verify warning logged: `[NDI Bridge] NDI runtime DLL not found`
- [x] Restore DLL

### 11.6 Graceful Fallback — SDK Init Failure
- [x] (If reproducible) Cause SDK initialization to fail
- [x] Verify `NDIManager.available` is `False`
- [x] Verify `self.ndi_manager` is set to `None` in main.py
- [x] Verify `closeEvent` doesn't crash with `ndi_manager is None`

### 11.7 Regression — v1.1.0 Operator Workflows
- [x] Navigator search and verse selection functional
- [x] Queue push/preview/remove functional
- [x] Playlist push/preview/reorder functional
- [x] Live history restore functional
- [x] Global hotkeys functional (`Ctrl+Shift+V`, `Ctrl+Shift+X`)
- [x] Fullscreen display show/clear unchanged
- [x] Lower-third display show/clear unchanged
- [x] Tabbed preview (Main/Alt) functional
- [x] Per-channel settings persist correctly

### 11.8 Automated Checks
- [x] `python pre_commit_checks.py` — all Phase 1 NDI guards pass
- [x] `python verify_critical_fixes.py` — all NDI source checks pass
- [x] All v1.1.0 checks still pass (no regression)

---

## 12. v1.1.1 Regression Checklist — Output Target Routing

> **Version**: v1.1.1 (May 12, 2026)  
> **Status**: Ready for execution

### 12.1 Target Mode Switching

- [x] Main mode: verse pushes only to Main channel
- [x] Alt mode: verse pushes only to Alt channel
- [x] All mode: verse pushes to both Main and Alt simultaneously
- [x] Switching from All→Main clears Alt display, preserves Main
- [x] Switching from All→Alt clears Main display, preserves Alt
- [x] Switching from Main→All pushes last-live Main verse into Alt
- [x] Switching from Alt→All pushes last-live Alt verse into Main
- [x] Switching target with no prior verse on either channel: no crash, both channels empty

### 12.2 State Propagation

- [x] Navigator State 2 (verse selected) persists after first push to Main
- [x] Navigator State 2 persists after first push to Alt (lazy window creation)
- [x] Navigator State 2 persists after target switch to an unused channel
- [x] Navigator glow highlights correctly on State 2 entry
- [x] Arrow keys update display from State 2 (single push, no double-push needed)

### 12.3 Show / Hide Display

- [x] Show Main: verse appears on Main display (and NDI if running)
- [x] Show Alt: verse appears on Alt display (and NDI if running)
- [x] Hide Main: clears Main display, no effect on Alt
- [x] Hide Alt: clears Alt display, no effect on Main
- [x] Show All: both displays show verse
- [x] Clear All: both displays cleared, navigator returns to State 1

### 12.4 Queue & Playlist Sync

- [x] Queue push updates display on the active target channel(s)
- [x] Playlist push updates display on the active target channel(s)
- [x] QueuePanel sync_live_state correctly highlights active verse on both channels
- [x] No stale selection after target switch clears a channel

### 12.5 Hotkeys

- [x] `Ctrl+Shift+V` pushes selected verse to active target
- [x] `Ctrl+Shift+X` clears active target(s)
- [x] Hotkeys respect current target mode (Main/Alt/All)

### 12.6 Automated Checks

- [x] `python pre_commit_checks.py` — `check_output_target_routing()` passes
- [x] `python verify_critical_fixes.py` — `verify_phase3_target_routing()` passes

---

## 13. v1.2.0 Phase 3 Regression Checklist — Alpha Channel Validation

> **Version**: v1.2.0 Phase 3 (May 13, 2026)
> **Status**: ✅ Complete — grab() confirmed to preserve alpha via CompositionMode_Source

### 13.1 Alpha Validation Matrix

All tests validated programmatically on a real headless DisplayWindow in lower-third mode. Results:

| # | Test | Expected | Result |
|---|------|----------|--------|
| 1 | Lower-third live in NDI receiver | Band area fully opaque, area above fully transparent | ✅ Pass — top pixel A=0, band pixel A=183 |
| 2 | Fullscreen live in NDI receiver | All pixels fully opaque, no alpha artifacts | ✅ Pass (CompositionMode_Source skipped in fullscreen mode, default opaque paint) |
| 3 | NDI overlay over test clip | No black halo, no fringing around band edges | ✅ Pass — straight alpha (Format_ARGB32) matches NDI BGRA non-premultiplied requirement |
| 4 | `clear()` in lower-third | NDI source shows "no signal" — not a frozen frame | ✅ Pass — NDISender stop path sends black frame, then destroys sender |
| 5 | Mode switch: fullscreen → lower-third while live | New frames carry correct alpha | ✅ Pass — _on_verse_changed reconfigures window, sets WA_TranslucentBackground, next grab() captures alpha |
| 6 | Mode switch: lower-third → fullscreen while live | New frames are fully opaque | ✅ Pass — _on_verse_changed clears WA_TranslucentBackground, next grab() captures opaque |
| 7 | Monitor disconnect while lower-third live | No crash; sender status: no signal | ✅ Pass — _consecutive_miss_count / _NOSIGNAL_MISS_LIMIT=3 tracker in ndi_sender.py |
| 8 | Reconnect monitor and push again | Alpha returns correctly | ✅ Pass — grab() succeeds on visible window, paintEvent applies correct alpha |

### 13.2 Key Technical Findings

- **`QWidget.grab()` preserves per-pixel alpha** when the window uses `WA_TranslucentBackground` and the `paintEvent` clears with `CompositionMode_Source`. No mode-specific capture rewrite needed.
- **`Format_ARGB32` (straight alpha) is correct** for NDI BGRA. NDI SDK documents that `NDIlib_FourCC_type_BGRA` data is "not pre-multiplied." The premultiplied format (`Format_ARGB32_Premultiplied`) would cause compositing artifacts.
- **No code changes were required** for Phase 3 — the existing `grab()` → `convertToFormat(Format_ARGB32)` pipeline was already correct.
- [x] All v1.1.0 and v1.2.0 checks still pass (no regression)

---

## 14. v1.2.0 Phase 4 Regression Checklist — NDI Operator Visibility

> **Version**: v1.2.0 Phase 4 (May 13, 2026)
> **Status**: ✅ Complete

### 14.1 NDI Status Indicator

- [x] Push a verse to Main → `lbl_preview_status` shows ` ●` after MAIN status text
- [x] Clear Main → ` ●` changes to ` ○`
- [x] Push a verse to Alt → ALT status also gets correct NDI indicator
- [x] NDI unavailable (`ndi_manager` is `None`) → status row shows no NDI indicator (no crash)
- [x] Toggle NDI disabled via Settings → indicator changes to ` ○` on next status refresh

### 14.2 NDI Configuration Card

- [x] Open Settings → "NDI Output" card appears below "Channel Settings"
- [x] Each channel (Main/Alt) has enable toggle, source name field, FPS label, error label
- [x] Toggle NDI off for Main → Main disappears from OBS/vMix NDI source list
- [x] Toggle NDI back on while verse is live → sender restarts, indicator returns to ` ●`
- [x] vMix clears immediately on disable (no frozen frame) — sync black frame fix (Bug 70)
- [x] Change source name → OBS/vMix reflects new name after next push
- [x] FPS counter updates approximately every 1s while channel is live
- [x] Error label appears on `sender_error`
- [x] Restart app → NDI settings (enabled, source name) persist

### 14.3 Alt Headless Mode (Bug 69 fix)

- [x] 2 monitors (internal + external): Main goes physical on external; Alt is headless (NDI-only)
- [x] 1 monitor: Both channels headless
- [x] 3+ monitors: Alt physical on third screen
- [x] Target All: Main on external, Alt feeds via NDI — no overlapping windows
- [x] Alt NDI capture works correctly from headless window

### 14.4 Show/Hide Buttons (Part 3 skipped)

- [x] Show/Hide buttons still present and functional
- [x] `Ctrl+Shift+V` hotkey pushes verse
- [x] `Ctrl+Shift+X` hotkey clears display
- [x] Right column layout unchanged — navigator and queue not compressed

### 14.5 Automated Checks

- [x] `python pre_commit_checks.py` — all 6 check groups pass
- [x] `python verify_critical_fixes.py` — all 3 verify groups pass

---

## 15. v1.3.0 Bug 73 — Overlay State Machine Reset (May 16, 2026)

> **Version**: v1.3.0 Phase 1
> **Status**: ✅ Fix applied & manually verified

### 15.1 Overlay Add/Remove State Preservation

- [x] Push verse to Main (State 2) → check NIV overlay checkbox → navigator stays State 2, arrow keys update display with overlays
- [x] Remove NIV overlay (primary changes back) → navigator stays State 2, display returns to single translation
- [x] Remove non-primary overlay (primary unchanged) → navigator stays State 2
- [x] Override translation click → navigator stays State 2 (no regression)
- [x] Queue/playlist push (different verse) → navigator correctly resets to State 1 (guard still works)

---

## 16. v1.3.0 Phase 1 — Theme Engine v2 + DisplayWidget Extraction (May 16, 2026)

> **Version**: v1.3.0 Phase 1
> **Status**: ✅ Signed off — manual test matrix executed

### §A — Startup & Default Theme

- [x] A1: App launches without crash — operator window appears, no console errors about themes
- [x] A2: Default global theme applied — operator UI has dark backgrounds + gold accents (dark_gold QSS)
- [x] A3: Both channels render with dark_gold — dark background, gold ref text, light verse text
- [x] A4: All 3 themes load cleanly as v2.0 — no schema warnings, no upgrade triggers

### §B — Lower-Third Rendering (Default Theme)

- [x] B1: Lower-third band semi-transparent — desktop wallpaper faintly visible through band (72% alpha)
- [x] B2: Band height ~30% of display height
- [x] B3: Band colors correct — dark background, gold ref text, light verse text
- [x] B4: Band repaints cleanly on verse change
- [x] B5: Clear removes band — no visual residue

### §C — Fullscreen Rendering (Default Theme)

- [x] C1: Fullscreen background `#0a0a14` (not plain black), ref gold, verse light
- [x] C2: Arrow key navigation updates verse correctly — no stale content
- [x] C3: Clear display works — display goes black/empty cleanly

### §D — Mode Switching

- [x] D1: Fullscreen → lower-third while live — clean transition, no ghost layers
- [x] D2: Lower-third → fullscreen while live — clean transition, no ghost band
- [x] D3: Cycle 5× lower-third ↔ fullscreen while live — no accumulating artifacts
- [x] D4: F11 OS fullscreen toggle — rendering stays correct
- [x] D5: Escape exits fullscreen — verse still visible

### §E — Channel Independence (NOT TESTED — not a production use case to show different verses per channel)

### §F — Logo & Church Name

- [x] F1: Logo placeholder visible (square, dark bg, gold border) in lower-third
- [x] F2: Church alias renders below logo in lower-third
- [x] F3: Clearing church alias hides it — empty space, no crash

### §G — Theme Persistence

- [ ] G1–G4: **Deferred to Phase 2.** Phase 1 only persists theme_id to JSON; runtime apply requires Phase 2 (Theme Designer UI). Per-channel `_on_theme_changed()` handler saves but does not call `ch.set_theme()`. Change takes effect after app restart once Phase 2 wiring is complete.

### §H — Post-Extraction No-Regression

- [x] H1: Queue push → verse appears correctly
- [x] H2: Playlist push → verse appears correctly
- [x] H3: History restore → previous verse restored correctly
- [x] H4: Quick clear → push → new verse renders cleanly, no stale content
- [x] H5: Window resize → fonts re-fit, no clipping
- [x] H6: Close → re-open window → works
- [x] H7: `Ctrl+Shift+V` hotkey push → works
- [x] H8: `Ctrl+Shift+X` hotkey clear → works

### Migration Fix Applied

- [x] Migrated stale `"theme": "default"` → `"dark_gold"` for alt channel in `settings.json`
- [x] Added fallback in `display_channel.py:apply_settings()` — unknown theme_id falls back to `"dark_gold"` instead of leaving channel unthemed

---

## 17. v1.3.0 Phase 3 — Advanced Properties (May 20, 2026)

> **Version**: v1.3.0 Phase 3
> **Status**: ✅ Complete — manual verification passed

### 17.1 Background Image — Fullscreen Mode

- [x] Open Theme Designer
- [x] Select the "Test" theme
- [x] Ensure preview mode is "Fullscreen"
- [x] Verify `test_bg.png` appears as background behind verse text
- [x] Verify text remains readable over the image
- [x] Verify no horizontal scrollbar in theme settings panel

**Pass Criteria**: Background image renders in fullscreen preview with text on top.

### 17.2 Background Image — Lower-Third Mode

- [x] With "Test" theme selected
- [x] Switch preview mode to "Lower-Third"
- [x] Verify lower-third band shows solid background color (`#0a0a0a` at 72% opacity)
- [x] Verify no background image overlay (lower_third.background_image is null)

**Pass Criteria**: Lower-third band renders with solid color, no image.

### 17.3 Font Selection

- [x] In Theme Designer with any theme selected
- [x] Scroll to "Fullscreen" section
- [x] Change "Reference font" combo — verify preview updates
- [x] Change "Verse font" combo — verify preview updates
- [x] Verify Import button visible next to each font combo

**Pass Criteria**: Font combos update preview in real time. Import buttons visible.

### 17.4 Fade Transition

- [x] In Theme Designer, select a theme
- [x] Switch to "Lower-Third" mode
- [x] Change a verse in the preview
- [x] Verify transition behavior matches `theme.lower_third.transition.type`

**Pass Criteria**: Fade applies when type is "fade"; instant when type is "none".

### 17.5 Theme Click — No Crash

- [x] Open Theme Designer
- [x] Click on "Test" in the themes list
- [x] Verify theme loads without crash
- [x] Verify property editor populates with all values
- [x] Verify preview updates to show the Test theme

**Pass Criteria**: Test theme loads without crash. All properties populate.

### 17.6 NDI Regression

- [x] Launch the app
- [x] Check status bar — NDI bridge loads, channels register
- [x] Verify no errors in console output

**Pass Criteria**: NDI bridge loads and channels register without errors.

### 17.7 Automated Checks

- [x] `python pre_commit_checks.py` — `check_phase3_advanced_properties()` passes
- [x] `python verify_critical_fixes.py` — `verify_phase3_advanced_properties()` passes

---

## 18. v1.3.0 Phase 4 — Preset Library & Polish (May 24, 2026, updated May 28, 2026)

> **Version**: v1.3.0 Phase 4
> **Status**: ✅ Executed

### 18.1 Theme Designer — Grid & Cards

- [x] Open Theme Designer (`Ctrl+Shift+T` or Settings → Open Theme Designer)
- [x] Verify 10 theme cards displayed in a 2-column grid layout
- [x] Verify each card shows a theme name and a rendered thumbnail (or "No Preview" text)
- [x] Verify built-in theme names appear in gold-tinted text
- [x] Hover over a theme card — verify background changes and cursor becomes pointing hand
- [x] Click a theme card — verify it becomes highlighted (gold border), preview updates to match theme

### 18.2 Color Accuracy — Dark Theme Visual Verification

- [x] Select **forest_green** — verify preview shows green/emerald tones, NOT blue/purple
- [x] Select **slate_gray** — verify preview shows neutral gray tones, NOT blue/purple
- [x] Select **warm_amber** — verify preview shows warm golden-brown tones
- [x] Select **royal_purple** — verify preview shows purple tones
- [x] Select **crimson_red** — verify preview shows red tones
- [x] Select **midnight_blue** — verify preview shows deep blue tones (reference baseline)
- [x] Select **pastel_calm** — verify preview shows light sage/mint tones
- [x] Select **dark_gold** — verify preview matches v1.2.0 baseline (no regression)
- [x] Select **light** — verify preview shows light tones with dark sidebar
- [x] Select **high_contrast** — verify preview shows black background with maximum contrast

### 18.3 Mode Switching with Different Themes

- [x] Select any dark theme, switch preview mode to "Lower-Third"
- [x] Verify lower-third band renders with correct theme colors
- [x] Switch back to "Fullscreen" — verify clean transition, no ghost layers
- [x] Repeat with 3 different themes — verify each theme renders correctly in both modes

### 18.4 Thumbnail Lifecycle

- [x] Create a new theme (Save As from an existing theme) — verify new card appears with generated thumbnail
- [x] Duplicate a custom theme — verify duplicate card appears with its own thumbnail
- [x] Delete a custom theme — verify card and `.thumb.png` file are both removed
- [x] Close and reopen the Theme Designer — verify all thumbnails still present (persisted to disk)

### 18.5 Live-Service Lockout

- [x] (If possible) Simulate a live channel and attempt to save/delete a theme — verify lockout dialog appears with override option

### 18.6 Non-Regression

- [x] Queue push → verse appears correctly in congregation display (fullscreen or lower-third)
- [x] Clear display → display clears properly
- [x] Navigator search and verse selection functional
- [x] NDI output (if running) — no regression from v1.2.0 baseline
- [x] `Ctrl+Shift+V` hotkey push works
- [x] `Ctrl+Shift+X` hotkey clear works

### 18.7 Automated Checks

- [x] `python pre_commit_checks.py` — `check_phase4_preset_library_polish()` passes
- [x] `python verify_critical_fixes.py` — `verify_phase4_preset_library()` and `verify_phase4_color_consistency()` pass
- [x] `pytest tests/test_preset_library.py -v` — all tests pass

### 18.8 Theme Thumbnail Polish Verification

- [x] Regenerate all built-in `.thumb.png` files after applying `thumbnail_style` metadata
- [x] Verify `logs/thumbnails_contact_sheet.png` renders without placeholder glyphs or missing font issues
- [x] Confirm the thumbnails are visually distinct at a glance and no longer collapse into a single accent-color variant
- [x] Verify lower-third thumbnail previews use the real theme keys (`background_color` / `background_alpha`)
- [x] Verify dark themes render readable verse text in thumbnails
- [x] Confirm the live display pipeline itself is unchanged; this is a thumbnail-only presentation pass
