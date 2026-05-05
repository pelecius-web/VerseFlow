# VerseFlow Progress Log (Development Memory)

This log tracks every implemented task and bug fix. It serves as the primary memory when checking progress against [ROADMAP.md](file:///C:/Users/GENESIS/Desktop/VerseFlow%20Antigravity/VerseFlow/ROADMAP.md).

---

## 2026-04-20: Entry Identity & UX Hardening Fixes
**Status:** ✅ COMPLETED
**Roadmap Reference:** Phase 2.5 (Category 1 Cleanup)

### Summary
Completed the surgical fix pass that restored undo/redo integrity, normalized legacy playlist loading, and hardened file-operation UX.

- **[FIX] Playlist Undo/Redo Integrity**: Added `find_row_by_entry_id()` to `PlaylistModel` and updated command logic to use `entry_id` safely for add/remove/move flows.
- **[FIX] Legacy Playlist Migration**: Normalized loaded `.verseplaylist` files so every item receives a valid string `entry_id` while preserving the original verse/database `id`.
- **[FIX] File Error UX**: Added blocking error dialogs for open/save/save-as failures so operators are not left with silent console-only errors.
- **[UI] Toolbar Icons**: Kept the icon-based playlist toolbar and added a safe text fallback that expands to fit without truncation when an icon is unavailable.

---

## 📌 PENDING: Category 1 Cleanup & Transition
**Status:** ⏳ IN PROGRESS — Cross-refs ✅, Accelerators ✅, Hotkeys ⬜
**Goal:** Finalize any remaining UX hurdles before moving to Category 2 (Advanced Display).

- **[DONE] Cross-Reference System Wiring**: `highlighted_verse_changed` signal wired; cross-ref panel now updates live on every verse highlight change.
- **[DONE] Keyboard Accelerator Pass**: `Ctrl+L` (search focus), `Esc` (clear navigator), `Ctrl+Z/Y` (undo/redo), `Enter` (push) all fully wired.
- **[DONE] Edit Menu**: "Edit" menu added to MainWindow with Undo, Redo, and Save Playlist actions and standard shortcuts.
- **[TASK] Global Hotkey Manager**: Implement `hotkey_manager.py` for system-wide shortcuts (e.g., `Ctrl+Shift+V`) when app is in background.
- **[TASK] Cross-Platform Testing**: Verify shortcut consistency and UI transparency on macOS and Linux.

---

## 2026-04-19: Cross-Reference Fix & Keyboard Accelerators (Stage 7)
**Status:** ✅ COMPLETED
**Roadmap Reference:** Phase 2.5 (Category 1 Cleanup)

### Summary
Fixed the "Broken Wire" in the Cross-Reference system and added professional keyboard accelerators for live service use.

- **[FIX] Cross-Reference Wiring**: Added `highlighted_verse_changed = pyqtSignal(dict)` to `VerseNavigator`. Signal emits in `load_chapter()`, `_on_select()`, and `_move_highlight()`. Wired to `xref_panel.load_for_verse()` in `HomePanel`. Added secondary trigger from `display.verse_changed` for pushes originating from queue/history panels.
- **[NEW] Ctrl+L Shortcut**: "Focus Search" accelerator — clears navigator and focuses/selects-all search input for instant new lookup.
- **[NEW] Edit Menu**: Professional "Edit" menu in `MainWindow` with Undo (`Ctrl+Z`), Redo (`Ctrl+Y`), Save Playlist (`Ctrl+S`) wired to `DocumentManager`.
- **[UI] Premium Trash Icons**: Replaced the truncated "Clear" buttons on the Queue and Live History panels with professional 24x24px "Trash" icon buttons, styled with custom tooltip and red-glow hover states for standardized, truncation-free aesthetic.
- **[NEW] _save_playlist()**: Centralised save helper in `MainWindow` that shows status bar feedback on success/failure and prompts for path on new files.
- **[DATA] Cross-Reference Naming Cleanup**: Synchronized naming conventions in `data/cross_references.json`. All instances of "Psalm " were updated to "Psalms " to match the Bible database and UI logic, and "Revelations " was standardized to "Revelation ". This fixes the issue where Psalm verses would previously return no references.

---

## 2026-04-18: Final Audit & UI/UX Polish (Stage 6)
**Status:** ✅ COMPLETED
**Roadmap Reference:** Phase 2.5 (Category 1) & Phase 3 (Stage 6 Polish)

### Summary
Consolidated all final Category 1 audit items and addressed critical UI/UX friction in the Playlist and Search workflows.

- **[FIX] Hardened Toggle Engine**: Implemented "intent-based" source tracking and `_sync_push_tracker` in `main.py` to fix the 'Red X' toggle bug.
- **[FIX] Display-Aware Undo**: Integrated `DisplayController` with queue commands; screen now clears/restores correctly during Undo/Redo operations.
- **[FIX] _on_hide Race Condition**: Resolved a logic error that caused the screen to flicker when toggling off.
- **[FIX] Item Identity (P0)**: Ensured unique UUID generation for all playlist/queue items to prevent destructive collisions.
- **[FIX] Dirty State Logic (P0)**: Refactored document-management to use `QUndoStack.cleanChanged` for accurate "Save" prompts.
- **[FIX] Backup Integrity (P1)**: Fixed the rotation order to protect user data during saves.
- **[UI] Playlist Action Glyphs**: Replaced text buttons (NEW, OPEN, etc.) with Unicode symbols (✦, ⏏, ⬇, ⇗, ⚙) to prevent layout clipping at high DPI.
- **[UX] Search Select-All**: Implemented `SearchLineEdit` and global event filter updates to enable instant overwritten searches on single-click.

---



## 2026-04-14: Category 1 Foundation & UI Reshuffle
**Status:** ✅ STAGE 1 & 2 COMPLETED  
**Roadmap Reference:** Phase 2.5 (Category 1)

### Summary
Completed the surgical UI reshuffle and the modular data foundation required for the Verse Queue and Service Playlist systems.

- **[UI] 3-Column Layout**: Successfully implemented the 3-column operator layout (Draft Editor | Search & Playlist | Preview & Navigator).
- **[NEW] models.py**: Created `PlaylistModel` and `QueueModel` (QAbstractListModel) with internal drag-and-drop and live-state tracking.
- **[NEW] document_manager.py**: Implemented centralized document lifecycle (New/Open/Save/Undo) with atomic writes and auto-backups.
- **[NEW] queue_panel.py**: Created the functional `QueuePanel` and `QueueItemDelegate` for verse staging (currently being integrated).
- **[ARCH] Modular Refactor**: Decoupled core logic from `main.py` into separate modules for better maintainability.

---

## 2026-04-14: Stability & Workflow Fixes
**Status:** ✅ COMPLETED  
**Roadmap Reference:** Phase 2 (Navigator & Workflow)

### Summary
Fixed 5 critical bugs that prevented the application from launching or behaving correctly after the initial UI reshuffle for Category 1.

- **[FIX] DisplayPreview Recursion Crash**: Added `_fitting` flag to prevent infinite layout-induced resize loops.
- **[FIX] History Restore Logic**: Corrected argument types in `load_chapter` and switched state transitions to `_on_card_pushed`.
- **[FIX] Keyword Workflow**: Standardized transition to State 2 (Live) when pushing verses from keyword results.
- **[FIX] Keyword Clear Logic**: Replaced destructive `display.clear()` with selective `push_verse({})` to preserve the display window.

---

## 2026-04-09: Phase 2 Completion
**Status:** ✅ COMPLETED  
**Roadmap Reference:** Phase 2 (Dual-Monitor)

### Summary
Successfully implemented the separated operator/congregation display system.

- **[NEW] DisplayWindow**: Multi-monitor support and fullscreen rendering.
- **[NEW] DisplayController IPC**: Signal-based communication between windows.
- **[NEW] VerseNavigator State Machine**: 3-state workflow for BibleShow-style navigation.
- **[NEW] Translation Selector**: Overlay/Override support with dynamic font fitting.

---

## 2026-04-01: Phase 1 Completion
**Status:** ✅ COMPLETED  
**Roadmap Reference:** Phase 1 (Core UI)

### Summary
Foundational UI features and theme engine.

- **[NEW] ThemeManager**: JSON-based skinning (Dark Gold, Light, High Contrast).
- **[NEW] Draft Editor**: Operator-only editing before publishing live.
- **[NEW] Cross-Reference System**: Automated related verse discovery.
- **[NEW] Layout Selector**: Chapter/Single/Overlay modes.

---

## 2026-04-20: Hotkey Stage 1 Baseline
**Status:** COMPLETED
**Roadmap Reference:** Phase 2.5 (Category 1 Cleanup)

### Summary
Captured a clean pre-implementation baseline before adding the global hotkey manager.

- **[CHECK] Compile Baseline**: Verified the current core modules compile cleanly in the project `.venv`.
- **[CHECK] Import Baseline**: Verified the current core modules import successfully in the project `.venv`.
- **[CHECK] Hotkey Surface**: Confirmed `hotkey_manager.py` does not yet exist, so the next stage can be added surgically without conflicting work.

---

## 2026-04-20: Hotkey Stage 2 Skeleton
**Status:** COMPLETED
**Roadmap Reference:** Phase 2.5 (Category 1 Cleanup)

### Summary
Added the global hotkey manager scaffold without wiring native hotkey registration yet.

- **[NEW] Hotkey Manager Facade**: Created `HotkeyManager` with `register_action()`, `start()`, `stop()`, `available()`, and `status_summary()`.
- **[NEW] Backend Contract**: Added `HotkeyBackendBase` plus safe `NullHotkeyBackend` and `WindowsHotkeyBackend` stubs.
- **[CHECK] Import Safety**: Verified the new manager imports and instantiates cleanly in the project `.venv`.

---

## 2026-04-20: Hotkey Stage 3 Windows Native Backend
**Status:** COMPLETED
**Roadmap Reference:** Phase 2.5 (Category 1 Cleanup)

### Summary
Implemented native Windows global hotkey registration using Win32 APIs with guarded parsing and lifecycle cleanup.

- **[NEW] Native Registration**: `WindowsHotkeyBackend` now uses `RegisterHotKey` and `UnregisterHotKey` through `ctypes`.
- **[NEW] Event Bridge**: Added a Qt native event filter that listens for `WM_HOTKEY` and dispatches registered actions back into `HotkeyManager`.
- **[NEW] Shortcut Parsing**: Added parser support for modifier combinations and common key tokens (`A-Z`, `0-9`, `F1-F24`, arrows, `Esc`, `Enter`, etc.).
- **[CHECK] Runtime Probe**: Verified start/register/trigger/stop behavior in `.venv` with a live `QApplication`.
- **[FIX] Guardrail Compliance**: Hotkey start-up now surfaces partial registration failures with action-level detail, and native event type matching now accepts byte-based Qt event names to avoid dropped `WM_HOTKEY` dispatch.

---

## 2026-04-20: Hotkey Stage 4 Settings Integration
**Status:** COMPLETED
**Roadmap Reference:** Phase 2.5 (Category 1 Cleanup)

### Summary
Added the `hotkeys` settings section and normalization/validation helpers for configured global shortcuts.

- **[NEW] Hotkey Defaults**: Added `enabled` plus the four planned global shortcut defaults to the settings schema.
- **[NEW] Hotkey Normalization**: Settings now normalize invalid or duplicate hotkey values back to safe defaults on load, set, and save.
- **[NEW] Hotkey Validation**: Added `validate_hotkeys()` to report invalid or duplicate shortcuts from raw config input before registration time.
- **[CHECK] Runtime Probe**: Verified raw invalid/duplicate hotkey configs normalize and validate correctly in the project `.venv`.

---

## 2026-04-20: Hotkey Stage 5 App Wiring
**Status:** COMPLETED
**Roadmap Reference:** Phase 2.5 (Category 1 Cleanup)

### Summary
Wired the hotkey manager into the main application lifecycle using the existing operator actions and config-backed shortcuts.

- **[NEW] MainWindow Integration**: `MainWindow` now instantiates `HotkeyManager` after `HomePanel` exists and binds the four planned actions to existing handlers.
- **[NEW] Config-Backed Actions**: Action shortcuts are loaded from normalized hotkey settings instead of being hardcoded in the UI layer.
- **[NEW] Lifecycle Cleanup**: Hotkeys are started on launch when enabled and stopped during `closeEvent()` after save confirmation.
- **[NEW] Queue Helper**: Added `HomePanel._add_highlighted_to_queue()` for the planned `add_highlighted_to_queue` action.
- **[CHECK] Runtime Probe**: Verified `main.py` still compiles and imports cleanly with the new wiring in the project `.venv`.

---

## 2026-04-20: Hotkey Stage 6 Guardrails
**Status:** COMPLETED
**Roadmap Reference:** Phase 2.5 (Category 1 Cleanup)

### Summary
Completed the hardening pass for startup safety, duplicate registration prevention, and unsupported-platform behavior.

- **[FIX] Idempotent Start**: `HotkeyManager.start()` is now idempotent and does not re-register the same actions on repeated calls.
- **[FIX] Safe Rebind**: `WindowsHotkeyBackend.register_hotkey()` now replaces existing action registrations cleanly instead of accumulating stale global bindings.
- **[CHECK] Unsupported Platform Safety**: Verified non-Windows backend returns unavailable status without blocking startup.
- **[CHECK] Runtime Probe**: Verified repeated starts and action rebinds keep active registration count stable in `.venv`.
