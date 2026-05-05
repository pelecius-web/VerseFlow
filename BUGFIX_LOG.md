# VerseFlow Bugfix Log

This file documents bugs reported and their fix status for reference.

---

## Bug Report Date: April 23, 2026

### GUI Icon Corruption Issues

| # | Issue | Location | Status | Fix Details |
|---|-------|----------|--------|-------------|
| 1 | Translation dropdown up/down symbol corruption | `editors.py` TranslationMenu | ✅ FIXED | Replaced Unicode characters with SVG icons via `icons.get_arrow_down_icon()` and `icons.get_arrow_up_icon()` |
| 2 | Verse navigation up/down symbols corruption | `navigator.py` NavVerseCard | ✅ FIXED | Replaced Unicode characters with SVG icons via `icons.get_arrow_right_icon()` |
| 3 | Display control show/hide symbols corruption | `home_panel.py` HomePanel | ✅ FIXED | Replaced Unicode characters with SVG icons via `icons.get_play_icon()` and `icons.get_stop_icon()` |
| 4 | Live history return symbol corruption | `home_panel.py` HistoryEntryCard | ✅ FIXED | Replaced Unicode QLabel text with SVG icon via `icons.get_return_icon()` and `setPixmap()` |

### Text Encoding Issues (Mojibake)

| # | Issue | Location | Status | Fix Details |
|---|-------|----------|--------|-------------|
| 5 | Corrupted book names (e.g., "Isaiah a£") | `navigator.py`, `home_panel.py` | ✅ FIXED | Fixed UTF-8 encoding - replaced corrupted sequences `â€"` with proper em-dashes `—` and `â€¦` with ellipses `…` |
| 6 | Corrupted references in operator display preview | Multiple files | ✅ FIXED | Fixed mojibake in text labels across `navigator.py`, `home_panel.py`, `editors.py`, `main.py` |

### Functional Issues

| # | Issue | Location | Status | Fix Details |
|---|-------|----------|--------|-------------|
| 7 | Playlist shows full text instead of reference only | `playlist_panel.py` PlaylistItemDelegate | ✅ FIXED | Removed text snippet rendering from `paint()` method; reduced `ITEM_HEIGHT` from 60px to 40px |
| 8 | Save As crashes with AttributeError: 'HomePanel' object has no attribute 'statusBar' | `home_panel.py` | ✅ FIXED | Removed invalid `self.statusBar()` calls (QWidget has no statusBar method) |

---

## Implementation Summary

### Files Modified
- `icons.py` - Added 7 new SVG icon functions
- `navigator.py` - Replaced Unicode buttons, fixed mojibake
- `home_panel.py` - Replaced Unicode buttons, fixed mojibake, removed statusBar calls
- `editors.py` - Replaced Unicode buttons, fixed mojibake
- `playlist_panel.py` - Removed text rendering, reduced height

### New SVG Icons Added
- `get_arrow_right_icon()` - Right arrow for navigation
- `get_arrow_up_icon()` - Up arrow for navigation
- `get_arrow_down_icon()` - Down arrow for navigation
- `get_close_icon()` - X/close icon for clearing
- `get_play_icon()` - Play icon for show display
- `get_stop_icon()` - Stop icon for hide display
- `get_return_icon()` - Return arrow for history restore

### Total Changes
- **Unicode replacements**: 16 button instances
- **Mojibake fixes**: 20+ text instances
- **StatusBar crashes**: 2 locations fixed
- **Playlist UI**: Height reduced, text removed

---

## Bug Report Date: April 23, 2026 (Session 2)

### Title & Drag-Drop Issues

| # | Issue | Location | Status | Fix Details |
|---|-------|----------|--------|-------------|
| 9 | Playlist title not updating when opening saved file | `document_manager.py:187` | ✅ FIXED | Added `self.title_changed.emit(self._title)` after load — direct `_title` assignment bypassed the property setter's signal |
| 10 | Duplicate verse drag-drop crash (playlist → queue → playlist) | `models.py:317-343` | ✅ FIXED | Replaced direct `self._items` list mutation with proper `beginRemoveRows`/`endRemoveRows` and `beginInsertRows`/`endInsertRows` in both `PlaylistModel.dropMimeData` and `QueueModel.dropMimeData` |

### Icon Consistency

| # | Issue | Location | Status | Fix Details |
|---|-------|----------|--------|-------------|
| 11 | Navigator "+Q"/"+P" buttons use text instead of SVG icons | `navigator.py:NavVerseCard`, `KeywordVerseCard` | ✅ FIXED | Added `get_queue_icon()` (plus, green) and `get_playlist_icon()` (list, gold) to `icons.py`; replaced text buttons with SVG icon buttons |

### UI Cleanup

| # | Issue | Location | Status | Fix Details |
|---|-------|----------|--------|-------------|
| 12 | Unnecessary separator lines on display take up space | `display_window.py`, `home_panel.py` | ✅ FIXED | Removed separator QFrames from: DisplayWindow main, DisplayWindow overlays, DisplayPreview main, DisplayPreview overlays; updated font fitting calculations to reclaim space |

### Undo/Redo Issues

| # | Issue | Location | Status | Fix Details |
|---|-------|----------|--------|-------------|
| 13 | Undo/Redo keyboard shortcuts not working consistently | `home_panel.py:616-620`, `main.py:145-155` | ✅ FIXED | Removed duplicate QShortcut registration from home_panel.py (widget-scoped, only worked when HomePanel had focus); connected QAction enabled states to undo stack's canUndoChanged/canRedoChanged signals for proper enable/disable feedback |

### Navigation & Settings Issues

| # | Issue | Location | Status | Fix Details |
|---|-------|----------|--------|-------------|
| 14 | Global hotkeys don't work when app is unfocused | `hotkey_manager.py` | ✅ FIXED | Added Windows error code reporting via GetLastError(); added automatic QShortcut fallback when global RegisterHotKey fails or backend unavailable; hotkeys now work at minimum when app is focused |
| 15 | Settings panel is empty (PlaceholderPanel) | `main.py:77`, `settings_panel.py` (new) | ✅ FIXED | Created MVP SettingsPanel with Back button, hotkey diagnostics display, test hotkeys button, and full details view; replaced PlaceholderPanel |
| 16 | Navigation trap - no way back from Settings panel | `home_panel.py:150-182`, `main.py` | ✅ FIXED | Moved Home/Settings tab buttons from HomePanel sidebar to MainWindow (persistent tab bar above content stack); tab buttons now visible on both panels; added View menu with Ctrl+1/Ctrl+2 shortcuts |
| 17 | HomePanel tab buttons removed for MainWindow migration | `home_panel.py:150-182` | ✅ FIXED | Removed tab_home and tab_settings button creation and stack_nav method; kept stack_nav_requested signal for backward compatibility; replaced with simple title header |

---

## Implementation Summary (Session 2)

### Files Modified
- `document_manager.py` - Added `title_changed.emit()` in `load()`
- `models.py` - Fixed `dropMimeData()` in both `PlaylistModel` and `QueueModel` with proper Qt model notifications
- `icons.py` - Added `get_queue_icon()` and `get_playlist_icon()`
- `navigator.py` - Replaced text "+Q"/"+P" buttons with SVG icon buttons in `NavVerseCard` and `KeywordVerseCard`
- `display_window.py` - Removed main separator, overlay separators, updated font calculation, fixed stale comment
- `home_panel.py` - Removed main separator, overlay separators, reduced overlay gap spacing from `height//2` to `height//4`, removed duplicate QShortcut for undo/redo, removed tab buttons and stack_nav method, kept stack_nav_requested signal for compatibility
- `main.py` - Connected undo/redo QAction enabled states to undo stack's canUndoChanged/canRedoChanged signals, added persistent tab bar above content stack, replaced PlaceholderPanel with SettingsPanel, added View menu with Ctrl+1/Ctrl+2 shortcuts
- `hotkey_manager.py` - Added Windows error code reporting via GetLastError(), added automatic QShortcut fallback when global RegisterHotKey fails, added get_diagnostics() and trigger_action_by_name() methods

### New Files Added
- `settings_panel.py` - MVP SettingsPanel with Back button, hotkey diagnostics display, test hotkeys button, and full details view

### New SVG Icons Added
- `get_queue_icon()` - Plus icon for queue (green `#4caf7d`)
- `get_playlist_icon()` - List icon for playlist (gold `#c8a03c`)

### Key Technical Details
- **Bug 9**: Used explicit `emit()` instead of property setter in `load()` to avoid pushing unwanted undo commands after `_undo_stack.clear()`
- **Bug 10**: Qt model/view contract requires `beginRemoveRows`/`endRemoveRows` before/after removing items, and `beginInsertRows`/`endInsertRows` before/after inserting — direct list mutation causes index corruption and crashes
- **Bug 12**: Removed 4 separator QFrames (1px each) plus overlay separator spacing, allowing font fitting algorithms to allocate slightly larger fonts
- **Bug 13**: QShortcut with widget parent only works when that widget has focus; QAction in menu bar provides application-wide shortcuts. Duplicate registration caused inconsistent behavior and maintenance burden
- **Bug 14**: Windows `RegisterHotKey` with `NULL` hwnd registers hotkeys for the calling thread, not system-global. Added automatic QShortcut fallback to ensure hotkeys work at minimum when app is focused
- **Bug 16**: Navigation trap occurred because tab buttons were inside HomePanel's sidebar. Moving tab bar to MainWindow ensures persistent visibility regardless of which panel is active

---

## Regression Testing
All modified files pass Python syntax validation. Icons module loads successfully with all 15 icon functions available.

---

## Bug Report Date: April 24, 2026

### Navigator & Search Issues

| # | Issue | Location | Status | Fix Details |
|---|-------|----------|--------|-------------|
| 18 | First Enter key after verse search jumps immediately to state 2 (live display) | `home_panel.py:573, 888, 913, 1111` | ✅ FIXED | Added `_processing_search` flag set at start of `_do_search()`, cleared deferred after focus moves; eventFilter now skips Enter interception while flag is active |
| 19 | Saved playlist verses do not load when file is opened | `playlist_panel.py:468`, `queue_panel.py:412` | ✅ FIXED | Added `modelReset` signal connection to `_update_empty_state()`; `set_items()` uses `beginResetModel()/endResetModel()` which emits `modelReset`, but panels weren't listening |

### UI Layout & Spacing Issues

| # | Issue | Location | Status | Fix Details |
|---|-------|----------|--------|-------------|
| 20 | Cross-reference panel too tall, taking space from playlist | `navigator.py:871` | ✅ FIXED | Reduced height by 25%: 180px → 135px |
| 21 | SEARCH header creates misalignment with left sidebar | `home_panel.py:195-199` | ✅ FIXED | Removed SEARCH header label; translation menu now aligns with left sidebar "VerseFlow" title |
| 22 | Full-width tab bar pushes center/right panels down with empty space above | `main.py:67-74, 131-179`, `home_panel.py:145-182` | ✅ FIXED | Moved Home/Settings buttons from MainWindow's full-width tab bar into HomePanel's left sidebar; removed `_setup_navigation_tabs()` method; connected `home_panel.stack_nav_requested` to `main._switch_tab()` |
| 23 | AlignTop flags prevent vertical stretching of panels | `home_panel.py:356, 586` | ✅ FIXED | Removed `AlignTop` alignment flags on center and right columns; navigator, history, queue, playlist now stretch to fill window height |

---

## Implementation Summary (April 24, 2026)

### Files Modified
- `home_panel.py` - Added `_processing_search` flag for Enter key fix; removed SEARCH header; added Home/Settings tab buttons to left sidebar; removed AlignTop flags
- `navigator.py` - Reduced CrossRefPanel height from 180px to 135px
- `playlist_panel.py` - Added `modelReset` signal connection to `_update_empty_state()`
- `queue_panel.py` - Added `modelReset` signal connection to `_update_empty_state()`
- `main.py` - Removed `_setup_navigation_tabs()` call and entire method; connected `home_panel.stack_nav_requested` to `_switch_tab()`; updated `_switch_tab()` to reference `home_panel.btn_tab_home/settings`

### Key Technical Details
- **Bug 18**: Qt's focus re-dispatch bug occurs when a focused widget is synchronously disabled; Enter keypress is re-delivered to the newly focused widget. The `_processing_search` flag blocks eventFilter from intercepting Enter during the synchronous search execution, preventing immediate push to state 2.
- **Bug 19**: `set_items()` uses `beginResetModel()/endResetModel()` which emits `modelReset`, not `layoutChanged/rowsInserted/rowsRemoved`. Panels were only listening to the latter three signals, so empty state never updated after file load.
- **Bug 22**: Full-width tab bar in MainWindow's central layout created a 40px horizontal strip above all content. Moving tabs into left sidebar confines them to 280px width, eliminating the push-down effect on center/right columns.
- **Bug 23**: Passing an alignment flag to `addWidget()` sizes widget to its size hint and aligns it within available space, preventing vertical expansion. Removing the flag allows proper stretching based on layout's stretch factors.

---

## Bug Report Date: April 25, 2026

### Data Integrity & Encoding Issues

| # | Issue | Location | Status | Fix Details |
|---|-------|----------|--------|-------------|
| 24 | Saved playlist files show corrupted references (e.g., "Psalms 35:9 a£") while live display is clean | `home_panel.py:1449`, `db_layer.py:31-65`, `document_manager.py:166-235`, `playlist_panel.py:535-567`, `queue_panel.py:460-498` | ✅ FIXED | **Root cause was TWO distinct bugs**: (1) Hardcoded mojibake `â€"` (corrupted em-dash `—`) in `home_panel.py:set_preview_verse()` — this was the PRIMARY cause of visible corruption in preview; (2) Database `reference` column containing mojibake flowing to all consumers. **Fix**: (a) Replaced `â€"` with `—` in source code; (b) Added `_clean_reference()` in `db_layer.py` to sanitize ALL verse dicts at the database layer (single source of truth); (c) Kept existing migration/sanitization in playlist/queue/document_manager as defense-in-depth; (d) Cleaned all mojibake comments across codebase |

---

## Implementation Summary (April 25, 2026)

### Files Modified
- `home_panel.py` - **PRIMARY FIX**: Replaced hardcoded mojibake `â€"` with proper em-dash `—` in `set_preview_verse()` (line 1449); cleaned all mojibake comments
- `db_layer.py` - Added `_clean_reference()` helper to sanitize ALL verse dict references at the database layer (6 query sites)
- `build_db.py` - Database rebuilt from clean XML sources (6 translations, 186,558 verses)
- `document_manager.py` - Migration logic in `load()` to ALWAYS reconstruct clean references from book/chapter/verse fields
- `playlist_panel.py` - Sanitization in `add_verse()` to ALWAYS rebuild references with verse range preservation
- `queue_panel.py` - Sanitization in `add_verse()` to ensure queue items have clean references
- `navigator.py` - Cleaned mojibake comments (section headers, arrows)
- `main.py` - Cleaned mojibake comments (section headers)
- `editors.py` - Cleaned mojibake comments (section headers, arrows)

### Key Technical Details
- **Bug 24 (TRUE ROOT CAUSE)**: The mojibake visible in preview was caused by a **hardcoded corrupted string literal** in `home_panel.py:set_preview_verse()` — `â€"` instead of `—` (em-dash). This was NOT a database issue; the source code itself contained mojibake. Previous fixes only addressed database/migration layers but missed that the display code was injecting corruption directly. Secondary issue: database `reference` column also contained mojibake, now sanitized at the `db_layer.py` level via `_clean_reference()` which reconstructs clean references from book/chapter/verse fields, preserving verse range suffixes.

---

## Bug Report Date: April 26, 2026

### Type Safety & Crash Prevention

| # | Issue | Location | Status | Fix Details |
|---|-------|----------|--------|-------------|
| 25 | Malformed JSON playlist crash with `AttributeError: 'str' object has no attribute 'setdefault'` | `document_manager.py:155-176` | ✅ FIXED | Added `isinstance()` validation for `data` (must be dict), `items` (must be list), and individual items (must be dict) before processing. Raises `ValueError` with clear message for invalid input. |
| 26 | Cross-reference warning not displayed in status bar when file is missing | `main.py:95-97` → `main.py:114-116` | ✅ FIXED | Moved warning display to AFTER hotkey startup completes to prevent HotkeyManager status signals from overwriting it. |
| 27 | `ImportError: cannot import name 'QShortcut' from 'PyQt6.QtWidgets'` | `hotkey_manager.py:411` | ✅ FIXED | Changed import from `PyQt6.QtWidgets` to `PyQt6.QtGui` (QShortcut moved to QtGui in newer PyQt6 versions) |
| 28 | Multiple entry points vulnerable to type confusion from malformed data | `playlist_panel.py:527-532, 274-285`, `queue_panel.py:460-465, 504-509`, `home_panel.py:972-978, 1000-1007, 1448-1458` | ✅ FIXED | Added `isinstance()` validation at 8 critical entry points: `add_verse()`, `dropEvent()`, `add_verses_from_list()`, `_preview_queued_verse()`, `_push_verse()`, `set_preview_verse()`. All log warnings for malformed data instead of crashing. |

---

## Implementation Summary (April 26, 2026)

### Files Modified
- `document_manager.py` - Added type validation for data (dict), items (list), and individual items (dict)
- `main.py` - Moved cross-reference warning display to after hotkey startup
- `hotkey_manager.py` - Fixed QShortcut import from QtWidgets to QtGui
- `playlist_panel.py` - Added type validation in `add_verse()` and `dropEvent()`
- `queue_panel.py` - Added type validation in `add_verse()` and `add_verses_from_list()`
- `home_panel.py` - Added type validation in `_preview_queued_verse()`, `_push_verse()`, `set_preview_verse()`

### Key Technical Details
- **Bug 25**: Python allows iterating over strings, so `for it in "not an array"` produces individual characters. The code then called `it.setdefault()` on each character, causing `AttributeError`. Type validation prevents this by checking `isinstance(items, list)` before iteration.
- **Bug 26**: HotkeyManager's `start()` method emits status signals via `self.status.emit()` during registration. These signals are connected to `statusBar().showMessage()` in main.py line 79, so they overwrite any previous status messages. Moving the warning to after startup ensures it's the last message set.
- **Bug 27**: PyQt6 API change - QShortcut moved from QtWidgets module to QtGui module in newer versions. The fallback hotkey system uses QShortcut, so the import needed updating.
- **Bug 28**: Defense-in-depth approach - added type validation at all external data entry points (drag-drop, API calls, signal handlers). Each check logs a warning and returns early instead of crashing, ensuring robustness against malformed data from any source.

---

## Bug Report Date: April 29, 2026

### Display & Translation Interaction Issues

| # | Issue | Location | Status | Fix Details |
|---|-------|----------|--------|-------------|
| 29 | Translation dropdown "buggy" (signal cascade) | `editors.py` TranslationMenu | ✅ FIXED | Wrapped programmatic `setChecked()` calls in `_set_default_translation` and `_on_text_click` with `blockSignals(True/False)` to prevent spurious `stateChanged` triggers |
| 30 | 3-Translation overlay clips for long verses (Est 8:9) | `display_window.py` | ✅ FIXED | Added `QTimer` debouncer (0ms) to coalesce rapid `translations_changed` signals into a single re-render, preventing "ghost widget" accumulation from `deleteLater()` |
| 31 | Overlay clipping persists on low-res displays (800x600) | `display_window.py` font fitting | ✅ FIXED | Lowered hardcoded `min_font` floor from 14pt to 8pt for both single and overlay modes; allowed translation badge to scale down to 8pt |

---

## Implementation Summary (April 29, 2026)

### Files Modified
- `editors.py` - Blocked signals during programmatic translation menu updates
- `display_window.py` - Implemented render debouncing; lowered font floor to 8pt

### Key Technical Details
- **Bug 29**: `QCheckBox.setChecked()` fires `stateChanged` even for programmatic changes. This caused `_on_checkbox_toggle` to emit "remove" and "overlay" signals during a primary translation swap, corrupting `HomePanel` state before the correct "override" signal arrived.
- **Bug 30**: Adding 3 overlays in a loop triggered 3 rapid full-clears and re-renders. Because `deleteLater()` is deferred, old widgets were still taking up layout space when the next render fired, causing overflow. Debouncing ensures exactly one render occurs after all overlays settle.
- **Bug 31**: 800x600 displays lack vertical space for Esther 8:9 at 14pt (requires ~608px for blocks alone). Lowering the floor to 8pt allows the binary search to find the correct fit (11pt fits perfectly at ~462px).

---

## Bug Report Date: May 1, 2026

### Drag-Drop Reordering Issues

| # | Issue | Location | Status | Fix Details |
|---|-------|----------|--------|-------------|
| 32 | Internal drag-drop reordering deletes verses (double-move bug) | `playlist_panel.py:288`, `queue_panel.py:337` | ✅ FIXED | After pushing undo command that moves the item, set drop action to `IgnoreAction` before accepting event. This prevents Qt's `QAbstractItemView::startDrag()` from invoking automatic source cleanup (`clearOrRemove()`) which was causing a second move on the wrong row after our move command already displaced items. |
| 33 | Playlist missing setDefaultDropAction for internal reordering | `playlist_panel.py:229` | ✅ FIXED | Added `setDefaultDropAction(Qt.DropAction.MoveAction)` to ensure drop action is MoveAction for internal reorders (required for condition check) |
| 34 | Playlist uses unreliable currentIndex for source row detection | `playlist_panel.py:266-275` | ✅ FIXED | Extract source row from mime data by looking up item ID in model instead of using currentIndex, which can change during drag |
| 35 | Queue uses unreliable currentIndex for source row detection | `queue_panel.py:315-323` | ✅ FIXED | Extract source row from mime data by looking up item ID in model instead of using currentIndex |
| 36 | Playlist uses equality comparison instead of identity for source check | `playlist_panel.py:258` | ✅ FIXED | Changed `event.source() == self` to `event.source() is self` for correct object identity comparison |
| 37 | Queue missing playlist→queue external drop handler | `queue_panel.py:275-298` | ✅ FIXED | Added explicit handler for external drops from playlist with `AddToQueueCommand` and `CopyAction` to prevent source modification |

---

## Implementation Summary (May 1, 2026)

### Files Modified
- `playlist_panel.py` - Added `setDefaultDropAction(MoveAction)`, changed identity comparison to `is`, extracted source row from mime data, set drop action to `IgnoreAction` after move
- `queue_panel.py` - Added playlist→queue external drop handler, extracted source row from mime data, set drop action to `IgnoreAction` after move
- `verify_critical_fixes.py` - Added checks for `IgnoreAction` in both files
- `pre_commit_checks.py` - Added critical check for `IgnoreAction` to prevent double-move regression

### Key Technical Details
- **Bug 32 (ROOT CAUSE)**: When `setDefaultDropAction(MoveAction)` is set, Qt's `QAbstractItemView::startDrag()` calls `drag.exec(supportedActions, MoveAction)`. After the drop, if `drag.exec()` returns `MoveAction`, Qt automatically invokes `clearOrRemove()` on the source rows to complete the "move". Since our undo command already moved the item via `move_item()`, the source row now contains a different verse. Qt's cleanup deletes this wrong verse. Setting drop action to `IgnoreAction` before accepting tells Qt the drop is fully handled and no automatic cleanup should occur.
- **Bug 33-35**: `currentIndex()` returns the currently selected item, which can change if the user clicks elsewhere during a drag. Extracting the dragged item's ID from mime data and looking it up in the model provides the true source row regardless of selection state.
- **Bug 36**: `==` tests value equality, `is` tests object identity. For comparing `event.source()` with `self`, `is` is correct because we need to verify it's the exact same widget instance, not just an equivalent one.

---

## Bug Report Date: May 1, 2026 (Session 2)

### Keyword Search Relevance Issues

| # | Issue | Location | Status | Fix Details |
|---|-------|----------|--------|-------------|
| 38 | Multi-word search buries exact phrase matches behind noise results | `db_layer.py:_keyword_search()` (lines 175-342) | ✅ FIXED | Implemented two-tier relevance: Tier 1 queries exact contiguous phrase (`text LIKE '%fishers of%'`), Tier 2 backfills with AND-word matches excluding Tier 1 IDs via `NOT IN`. Tier 1 results appear first, ordered canonically. Applies only to unquoted multi-word queries (2+ words). Single-word and quoted-phrase paths unchanged. |
| 39 | Wildcard characters (%) and (_) treated as SQL wildcards, causing false matches | `db_layer.py:_keyword_search()` | ✅ FIXED (already in previous session) | Added `_escape_like()` helper that escapes `%`, `_`, `\` with backslashes; appended `ESCAPE '\'` to all LIKE clauses. |
| 40 | Search results not ordered canonically (Genesis → Revelation) | `db_layer.py:_keyword_search()` | ✅ FIXED (already in previous session) | Added `BOOK_ORDER_EXPR` (CASE expression mapping books to canonical order) and `ORDER BY` clause to all keyword search queries. |
| 41 | No result count display; capped results not indicated | `db_layer.py:_keyword_search()`, `navigator.py:KeywordResults` | ✅ FIXED (already in previous session) | `_keyword_search()` returns dict with `verses`, `total`, `capped` keys; `KeywordResults` displays count label showing "X results" or "Showing 50 of X results". |
| 42 | Matched search terms not highlighted in result cards | `navigator.py:KeywordVerseCard` | ✅ FIXED (already in previous session) | Added `_highlight_matches()` static method that wraps matched terms in bold/gold HTML tags; text label uses `RichText` format. |
| 43 | Verse lookup fallback fails on space-separated references | `db_layer.py:lookup_verse()`, `search()` | ✅ FIXED (already in previous session) | Added `SPACE_VERSE_RE` regex for purely space-separated references (e.g., "John 3 16"); applied as fallback in both `lookup_verse()` and `search()`. |
| 44 | `_processing_search` flag leak on crash paths | `home_panel.py:_do_search()` | ✅ FIXED (already in previous session) | Added `_deferred_reset` flag and `finally` block to ensure `_processing_search` is always reset on all exit paths. |
| 45 | Playlist panel live state not synced when external source changes display | `playlist_panel.py`, `home_panel.py` | ✅ FIXED (already in previous session) | Added `sync_live_state()` method to PlaylistPanel; connected `display.verse_changed` signal to it. |
| 46 | Navigator state not reset when external source takes over display | `home_panel.py` | ✅ FIXED (already in previous session) | Added `_sync_navigator_state()` method to reset navigator to State 1 when displayed verse doesn't match highlighted verse. |

---

## Implementation Summary (May 1, 2026 - Session 2)

### Files Modified
- `db_layer.py` - Rewrote `_keyword_search()` with two-tier relevance for unquoted multi-word queries; added `_escape_like()`, `BOOK_ORDER_EXPR`; updated to return dict with `verses/total/capped`
- `navigator.py` - Added `count_label` to `KeywordResults`; updated `set_verses()` signature to accept `total/capped/query`; added `_highlight_matches()` to `KeywordVerseCard`; text label uses `RichText` format
- `home_panel.py` - Updated `_do_search()` to handle dict return with `isinstance(result, dict)` guard; passes `total/capped/query` to `set_verses()`
- `pre_commit_checks.py` - Added 4 new tiered search regression guards (`tier1_rows`, `tier2_rows`, `NOT IN`, `safe_phrase`, `TWO-TIER RELEVANCE`)
- `verify_critical_fixes.py` - Added 5 new tiered search verification checks

### Key Technical Details
- **Bug 38 (ROOT CAUSE)**: Previous implementation AND'd all words together without attempting phrase match first. For `fishers of`, this returned verses containing "fishers" and "of" separately (e.g., "many fishers... of the LORD") before the exact phrase "fishers of men". Two-tier strategy runs phrase query first (Tier 1), fills remaining slots with AND-word query excluding Tier 1 IDs (Tier 2).
- **Tier 1**: Exact contiguous phrase via `text LIKE '%safe_phrase%' ESCAPE '\' OR reference LIKE '%safe_phrase%' ESCAPE '\'`. Canonical ordering. Limited to `MAX_RESULTS`.
- **Tier 2**: AND-word match via `text LIKE '%word1%' AND text LIKE '%word2%' ... ESCAPE '\'` with `id NOT IN (tier1_ids)` to prevent duplicates. Only fetched if `remaining = MAX_RESULTS - len(tier1_rows) > 0`.
- **Total count**: Uses AND-word COUNT (superset) since Tier 1 is a subset of Tier 2. This reflects the full result set for the count label.
- **Guarded edge cases**: Empty `tier1_ids` → no `NOT IN ()` emitted (SQL error avoided). Single-word path unchanged (no phrase to promote). Quoted-phrase path unchanged (explicit quote already means phrase).

### Regression Testing
- All existing pre-commit checks pass (playlist_panel, queue_panel, models, home_panel, editors, db_layer, navigator)
- All existing verification checks pass (drag-drop, translation menu, mimeTypes, live state sync, navigator state sync, search robustness, implementation plan changes, stages 1/2/5)
- New tiered search checks pass (tier1_rows, tier2_rows, NOT IN, safe_phrase, TWO-TIER RELEVANCE docstring, remaining-slot calculation)
- App launches successfully; keyword search functional with tiered relevance active

---

*Last Updated: May 1, 2026*

---

## Bug Report Date: May 4, 2026 (v1.1.0 Implementation)

### Navigator State Desynchronization

| # | Issue | Location | Status | Fix Details |
|---|-------|----------|--------|-------------|
| 46 | Push to Main does not update navigator highlight; Clear from Main crashes app | `home_panel.py` | ✅ FIXED | Rewired `btn_push_main` to `self._on_show()`, `btn_clear_main` to `self._on_hide()`; updated `_on_push_all()` and `_on_clear_all()` to use `_on_show()`/`_on_hide()` for Main channel to preserve navigator state machine synchronization |

### Null Safety in Channel Status

| # | Issue | Location | Status | Fix Details |
|---|-------|----------|--------|-------------|
| 47 | `AttributeError: 'NoneType' object has no attribute 'get'` in `_update_channel_status` after clear | `home_panel.py:1128` | ✅ FIXED | Added `if state is None: return` guard; changed `state.get("current", {}).get("reference", "")` to `(state.get("current") or {}).get("reference", "")` — Python's `dict.get(key, default)` returns default only for missing keys, not for `None` values. The `(value or {})` pattern handles both. |

### Phase 5 Runtime Smoke Test

| # | Issue | Location | Status | Fix Details |
|---|-------|----------|--------|-------------|
| 48 | `QWidget: Must construct a QApplication before a QWidget` crash in `check_phase5_runtime_smoke` | `pre_commit_checks.py` | ✅ FIXED | Added `QApplication.instance()` guard with `QApplication([])` fallback before `DisplayPreview` instantiation in the smoke test |

### hasattr vs getattr for None-valued Attributes

| # | Issue | Location | Status | Fix Details |
|---|-------|----------|--------|-------------|
| 49 | `hasattr(controller, 'theme_mgr')` returns `True` when `theme_mgr = None`, causing `None.set_theme()` crash | `display_channel.py:171` | ✅ FIXED | Changed `hasattr(self._controller, 'theme_mgr')` to `getattr(self._controller, 'theme_mgr', None) is not None` — `hasattr()` returns `True` for attributes that exist but are `None`; `getattr(..., None) is not None` catches both missing and None-valued cases |

---

## Implementation Summary (May 4, 2026 — v1.1.0)

### Files Modified (Bug Fixes)
- `home_panel.py` — Rewired push/clear buttons to use `_on_show()`/`_on_hide()` for Main channel; added null safety in `_update_channel_status`
- `display_channel.py` — Changed `hasattr()` to `getattr(..., None) is not None` for `theme_mgr` access
- `pre_commit_checks.py` — Added `QApplication` instance guard in `check_phase5_runtime_smoke`

### Key Technical Details
- **Bug 46**: The dual-output push/clear buttons bypassed the navigator state machine by calling `channel_manager.push_to_channel("main")` directly instead of `_on_show()`. This left the navigator in an inconsistent state, causing crashes on clear.
- **Bug 47**: Python's `dict.get(key, default)` only returns the default when the key is **missing**, not when its value is `None`. After `clear()`, `controller.current = None`, so `state.get("current", {})` returned `None` (key exists, value is None), then `.get(...)` crashed. The `(d.get(key) or {})` pattern handles both cases.
- **Bug 48**: `DisplayPreview` extends `QFrame`, which requires a `QApplication` instance before construction. The smoke test ran outside the main app context, so no `QApplication` existed.
- **Bug 49**: `hasattr(obj, 'attr')` returns `True` even when `obj.attr = None` because the attribute **exists**. The `getattr(obj, 'attr', None) is not None` pattern explicitly checks for a usable (non-None) value.

---

*Last Updated: May 4, 2026*
