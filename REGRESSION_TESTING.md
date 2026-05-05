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

- [ ] Create file with null bytes:
  ```json
  {"version": "1.0\u0000", "items": []}
  ```
- [ ] Try to open
- [ ] Verify rejection without crash

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
- [ ] Existing navigator push targets Main
- [ ] Existing clear targets Main
- [ ] Queue push targets Main
- [ ] Playlist push targets Main
- [ ] History restore works

### 8.2 Lower-Third Rendering
- [ ] Lower-third appears at bottom only
- [ ] Logo placeholder area is reserved
- [ ] Separator appears between logo and text
- [ ] Long verse does not clip
- [ ] Clear removes lower-third UI

### 8.3 Dual Channel Independence
- [ ] Push Main does not update Alt
- [ ] Push Alt does not update Main
- [ ] Clear Alt does not clear Main
- [ ] Push All updates both
- [ ] Clear All clears both

### 8.4 Preview Tabs
- [ ] Main preview updates from Main state
- [ ] Alt preview updates from Alt state
- [ ] Hotkey push updates Main preview
- [ ] Clear updates correct preview

### 8.5 Settings and Theme Foundation
- [ ] Channel mode persists after restart
- [ ] Missing settings fallback safely
- [ ] Invalid mode fallback safely
- [ ] Invalid logo path fallback safely

### 8.6 Full Manual Matrix
- [ ] Main fullscreen — existing display behavior unchanged
- [ ] Main lower-third — bottom-band layout works with logo placeholder
- [ ] Alt fullscreen — independent second fullscreen output
- [ ] Alt lower-third — independent second lower-third output
- [ ] Push Main — only Main changes
- [ ] Push Alt — only Alt changes
- [ ] Push All — both channels change
- [ ] Clear Main — only Main clears
- [ ] Clear Alt — only Alt clears
- [ ] Clear All — both clear
- [ ] Hotkey Push — Main default works
- [ ] Hotkey Clear — Main default clears
- [ ] Queue Push — Main default works
- [ ] Playlist Push — Main default works
- [ ] History Restore — restores expected Main behavior
- [ ] Mode Switch — re-renders current verse
- [ ] Settings Persist — modes/themes/logo placeholders persist
- [ ] Invalid Settings — safe fallback, no crash
- [ ] Long Verse — no clipping
- [ ] Multi-translation — no overflow or stale widgets
- [ ] App Startup — no crash with missing settings
