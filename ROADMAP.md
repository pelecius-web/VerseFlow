# VerseFlow Unified Roadmap

> **Consolidated from:** `First draft..txt`, `Verseflow help.txt`, `PROJECT_PLAN.md`  
> **Last Updated:** April 23, 2026  
> **Current Status:** v1.1.0 — Release Hardening (All phases implemented, final regression testing)

---

## 1. Project Overview

VerseFlow is a professional Bible projection application for churches and live production environments. It provides a robust operator panel, dual-monitor congregation display, AI-powered speech transcription, NDI streaming, and a built-in theme designer.

### Core Philosophy
- **Dual-Pane Architecture:** Operator control window + Congregation display window
- **State Machine Workflow:** READY → LIVE → CLEAR with undo/redo at every step
- **Production-First:** Reliable document lifecycle, global hotkeys, and fail-safe operations

---

## 2. Version Release Plan

| Version | Categories | Description | Est. Duration | Status |
|---------|------------|-------------|---------------|--------|
| **v0.7.9** | 1 | Category 1 Complete — Verse Queue + Service Playlist + Global Hotkeys | 5 weeks | ✅ Done |
| **v1.0.0** | — | Stable Release Candidate | — | 📋 Testing |
| **v1.1.0** | 2 | Lower-Third Display + Dual Output Channels | 5 weeks | ✅ Done |
| **v1.2.0** | 3 | NDI Output + HTTP/WebSocket API | 6 weeks | 📋 Planned |
| **v1.3.0** | 4 | Theme Designer + Background Images/Video | 4 weeks | 📋 Planned |
| **v1.4.0** | 5 | AI Speech Transcription | 6 weeks | 📋 Planned |
| **v2.0.0** | 6 | AI Sermon Notes Export (Production Ready) | 2 weeks | 📋 Planned |

**Total Estimated Development Time:** 23 weeks (~6 months) from v1.0.0 to v2.0.0.

> **Note:** v0.7.9 represents Category 1 completion. All foundation work (identity model, undo/redo, hotkeys, document lifecycle) is production-ready.

---

## 3. Category 1: Core Workflow & Operator UX (v1.0.0)

### 3.1 Features

| Feature | Description |
|---------|-------------|
| **Verse Queue Panel** | Temporary staging area for verses before display. Side-by-side with Live History. Cards show reference, translation, confidence badge. |
| **Service Playlist Panel** | Named, saveable playlists (`.verseplaylist` JSON files) with drag-and-drop reordering. Supports operator notes per item. |
| **Document Manager** | Handles open/save/save-as lifecycle with dirty state tracking via `QUndoStack`. |
| **Undo/Redo Stack** | `Ctrl+Z` / `Ctrl+Shift+Z` for all queue/playlist modifications. |
| **Global Hotkeys** | Configurable shortcuts (`Ctrl+Shift+V`, `Ctrl+Shift+C`, `Ctrl+Shift+Left/Right`) work even when app is in background. |
| **UI Layout** | Three-column design: left sidebar (280px), center space (320px), right content (expanding). |

### 3.2 Data Model

#### `.verseplaylist` File Format (v1.0)

```json
{
  "version": "1.0",
  "metadata": {
    "title": "Sunday Morning Service",
    "created": "2026-04-14T10:30:00Z",
    "modified": "2026-04-14T12:15:00Z",
    "service_date": "2026-04-20",
    "preacher": "Pastor John",
    "church": "Grace Community",
    "tags": ["easter", "resurrection"]
  },
  "items": [
    {
      "entry_id": "uuid-1234",
      "type": "verse",
      "id": 12345,
      "reference": "John 3:16",
      "translation": "NKJV",
      "text": "For God so loved the world...",
      "book": "John",
      "chapter": 3,
      "verse": 16,
      "notes": "Pastor's key verse"
    },
    {
      "entry_id": "uuid-5678",
      "type": "queue_group",
      "label": "Worship Scripture Block",
      "queue_items": [
        {
          "entry_id": "uuid-9012",
          "type": "verse",
          "id": 23456,
          "reference": "Romans 8:28",
          "translation": "ESV",
          "text": "And we know that all things work together...",
          "book": "Romans",
          "chapter": 8,
          "verse": 28
        }
      ]
    }
  ]
}
```

**Field Definitions:**

| Field | Type | Description |
|-------|------|-------------|
| `entry_id` | UUID | **UI/document identity** — unique for every queue/playlist entry |
| `id` | integer | **Verse/database identity** — preserved from Bible database |
| `type` | string | `"verse"` or `"queue_group"` |
| `reference` | string | Full verse citation (e.g., `"John 3:16"`) |
| `translation` | string | Bible translation abbreviation |
| `text` | string | Full verse text (embedded for portability) |
| `notes` | string | Operator notes (never displayed to congregation) |

### 3.3 Implementation Phases ✅ COMPLETE

| Phase | Status | Deliverables |
|-------|--------|--------------|
| **Phase 1: Foundation** | ✅ Done | `DocumentManager`, `.verseplaylist` schema, file I/O, `PlaylistModel`, `QueueModel` skeletons |
| **Phase 2: Queue Panel** | ✅ Done | `QueuePanel` widget, `QueueItemWidget`, interactions (preview, send, remove), `DisplayController` integration |
| **Phase 3: Playlist Panel** | ✅ Done | `PlaylistPanel` widget, file operations toolbar, drag-and-drop between playlist and queue |
| **Phase 4: Undo/Redo** | ✅ Done | `QUndoStack` integration, command classes (`AddToPlaylistCommand`, `RemoveFromQueueCommand`, etc.) |
| **Phase 5: Global Hotkeys** | ✅ Done | `HotkeyManager` with Windows native backend (`RegisterHotKey`), settings integration, 4 actions wired |
| **Phase 6: Polish & Bug Fixes** | ✅ Done | Entry identity model (P0), dirty state tracking (P0), backup integrity (P1), file error UX, drag-drop fixes |

**Total: 5 weeks — COMPLETED as of v0.7.9**

### 3.4 Integration Points

| Existing Component | Modification Required |
|--------------------|-----------------------|
| `HomePanel` | Replace "Coming Soon" panel with `QueuePanel` and add `PlaylistPanel` |
| `DisplayController` | Add signal `queue_item_went_live` for history logging |
| `VerseNavigator` | Emit `verse_went_live`; connect to `QueueModel.add_verse()` (optional auto-add) |
| `SettingsManager` | Add `hotkeys` section with default mappings |
| `MainWindow` | Instantiate `HotkeyManager`, connect signals to `HomePanel` slots |

---

## 4. Category 2: Advanced Display Modes (v1.1.0)

### 4.1 Features

| Feature | Description |
|---------|-------------|
| **Lower-Third Display Mode** | Semi-transparent band at bottom 25-30% of monitor with gradient fade. Two-line layout: abbreviated reference + verse text. Logo in bottom-left with vertical separator. |
| **Dual Output Channels** | Independent "Main" and "Alt" channels with separate monitor assignments, show/hide states, and layout modes. |
| **Push to All** | Single button sends verse to both channels simultaneously. |
| **Tabbed Preview** | Two-tab preview widget (Main/Alt) in operator panel. |
| **Per-Channel Theme Foundation** | `ThemeManager` extended for per-channel storage (full editor in Category 4). |

### 4.1.1 Architecture Decision

v1.1.0 should use **Option A — Adapter-First Channel Architecture**.

Do **not** replace `DisplayController` in one large rewrite. Instead:

- Keep the existing `DisplayController` as the working Main display implementation.
- Introduce `ChannelManager` and `DisplayChannel` as a wrapper layer first.
- Register the existing `DisplayController` as the initial `main` channel.
- Keep all current `display.*` consumers working while new channel-aware UI is added.
- Migrate display controls, preview, navigator, queue, playlist, history, hotkeys, and future integrations gradually.

Reason: the current operator UI, preview, queue, playlist, navigator, hotkeys, and translation overlay behavior are tightly coupled to `DisplayController` signals such as `verse_changed` and `translations_changed`. The adapter-first path has the lowest regression risk while still establishing the future public output API for dual channels, NDI/API control, and per-channel themes.

Architecture direction:

```text
v1.1.0 start:
MainWindow
  -> DisplayController
  -> ChannelManager
       -> main = DisplayChannelAdapter(existing DisplayController)

v1.1.0 later:
ChannelManager
  -> main = DisplayChannelAdapter(existing DisplayController)
  -> alt = DisplayChannel

future:
ChannelManager
  -> main = DisplayChannel
  -> alt = DisplayChannel
```

Architectural rules:

- Existing workflows target `Main` by default.
- New output features should call `ChannelManager`, not UI internals.
- Existing `DisplayController` behavior must remain backward-compatible during migration.
- `HomePanel` should keep its three-column structure; new output controls belong near the current display controls, and preview tabs should adapt the existing preview area.
- Future v1.2.0 NDI/API and v1.3.0 theme work should integrate through `ChannelManager`.

### 4.2 Lower-Third Technical Requirements

| Requirement | Implementation |
|-------------|----------------|
| **Window Transparency** | `Qt.FramelessWindowHint` + `Qt.WA_TranslucentBackground` |
| **Gradient Background** | Initial implementation should prefer QWidget/QSS or a stable semi-transparent painted widget; QML may be introduced later only if it does not increase regression risk. |
| **Logo Support** | Static placeholder rectangle (v1.1.0); PNG/SVG image loading deferred to v1.3.0 (Theme Designer). Positioned bottom-left with thin vertical rule separator. |
| **NDI Alpha Channel** | NDI 6.3 RGBA support for overlay without green screen |
| **Text Scaling** | Dynamic sizing: reference font ~60% of body font size |

### 4.3 Implementation Phases

| Phase | Duration | Deliverables |
|-------|----------|--------------|
| **Phase 1: ChannelManager Wrapper Foundation** | 1 week | `ChannelManager`, `DisplayChannel` adapter classes. Wrap existing `DisplayController` as Main without migrating all consumers. |
| **Phase 2: Renderer/Mode Preparation** | 0.5 week | Add explicit fullscreen/lower-third mode constants and rendering seams while preserving current fullscreen behavior. |
| **Phase 3: Lower-Third Mode** | 1.5 weeks | Stable lower-third renderer with semi-transparent band, gradient/fade if feasible, logo placeholder, text layout, separator, and mode switching. |
| **Phase 4: Dual Output UI** | 1 week | Add Alt channel, channel selector in operator panel, Push Main/Alt/All, Clear Main/Alt/All, and independent state. |
| **Phase 5: Tabbed Preview** | 0.5 week | Adapt existing preview area into Main/Alt tabbed preview with channel status. |
| **Phase 6: Per-Channel Theme Stubs** | 0.5 week | Extend settings/theme foundation for per-channel mode and theme storage. |
| **Phase 7: Polish & Testing** | 1 week | Cross-platform transparency, monitor hot-swap, layout balance, regression testing. |

**Total: 5 weeks**

---

## 5. Category 3: Integration & Output (v1.2.0)

### 5.1 Features

| Feature | Description |
|---------|-------------|
| **NDI Output** | Two independent NDI streams ("VerseFlow Main", "VerseFlow Alt") at 30/60 fps with alpha channel support (NDI 6.3). |
| **HTTP REST API** | Endpoints for verse lookup (`GET /api/verses`) and display control (`POST /api/display/push`, `POST /api/display/clear`). |
| **WebSocket API** | JSON-RPC over WebSocket for real-time bidirectional control with live state push. |
| **OBS Browser Source Overlay** | HTTP endpoint (`/overlay`) serving HTML/CSS that mirrors congregation display. |
| **Bitfocus Companion Module** | Pre-built module for Stream Deck integration. |
| **NDI Stream Monitoring** | Health overlay in operator panel (bitrate, FPS, frame drops). |

### 5.2 API Specification

**REST Endpoints:**

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/verses?q={reference}` | Search verses by reference or keyword |
| `POST` | `/api/display/push` | Push verse to display (JSON body with reference, translation) |
| `POST` | `/api/display/clear` | Clear congregation display |
| `GET` | `/api/state` | Get current display state |

**WebSocket Events:**

| Event | Direction | Description |
|-------|-----------|-------------|
| `verse.pushed` | Server → Client | Broadcast when verse goes live |
| `display.cleared` | Server → Client | Broadcast when display cleared |
| `push.request` | Client → Server | Request to push verse |

### 5.3 Implementation Phases

| Phase | Duration | Deliverables |
|-------|----------|--------------|
| **Phase 1: NDI Core** | 1.5 weeks | `NDISender` class, `DisplayChannel` integration, off-screen QML rendering, alpha channel support. |
| **Phase 2: NDI Monitoring** | 0.5 week | Stream health UI, bandwidth adjustment, sender statistics. |
| **Phase 3: HTTP API Foundation** | 1 week | `aiohttp` server, REST endpoints, local-only binding (`127.0.0.1`). |
| **Phase 4: WebSocket API** | 1 week | JSON-RPC over WebSocket, real-time state push, optional API key auth. |
| **Phase 5: OBS Overlay & Companion** | 1 week | Browser source endpoint (`/overlay`), Companion module configuration. |
| **Phase 6: Polish & Testing** | 1 week | Cross-platform NDI performance, API documentation, security audit. |

**Total: 6 weeks**

---

## 6. Category 4: Customization & Theming (v1.3.0)

### 6.1 Features

| Feature | Description |
|---------|-------------|
| **In-App Theme Designer** | Three-panel interface: saved themes list (left), live QML preview (center), property editor (right). |
| **Font Customization** | Import custom fonts (`.ttf`, `.otf`) via Qt `FontLoader`. |
| **Animation/Transitions** | Fade/slide transitions, configurable duration and easing curves stored per theme. |
| **Background Images & Video** | MP4 video backgrounds with hardware acceleration. Per-theme configuration. |
| **Preset Theme Library** | 8-10 professionally designed themes shipped with application. |
| **Per-Channel Themes** | Each output channel (Main/Alt) can use different themes. |

### 6.2 Implementation Phases

| Phase | Duration | Deliverables |
|-------|----------|--------------|
| **Phase 1: Theme Engine Foundation** | 1 week | `Theme` data class, JSON serialization (`.vftheme`), `ThemeManager` per-channel support. |
| **Phase 2: Theme Designer UI** | 1.5 weeks | Three-panel interface, QML preview with `QQmlPropertyMap`, live updates. |
| **Phase 3: Advanced Properties** | 0.5 week | Font import, transition settings, video background support (MP4). |
| **Phase 4: Preset Library & Polish** | 1 week | Create 8-10 preset themes, final testing, documentation. |

**Total: 4 weeks**

---

## 7. Category 5: AI Speech Transcription (v1.4.0)

### 7.1 Features

| Feature | Description |
|---------|-------------|
| **Offline ASR Engine** | Qwen3-ASR-1.7B (primary) with Voxtral Mini 3B fallback for CPU-only systems. |
| **Direct Reference Detection** | Regex pattern matching with book alias resolution; <5ms lookup. |
| **Semantic/Paraphrase Detection** | all-mpnet-base-v2 embeddings + FAISS vector index; 0.55 cosine similarity threshold. |
| **Confidence Scoring** | Hybrid scoring (ASR + semantic + direct match boost). |
| **Auto-Display/Queue** | Auto-display ≥80% confidence; auto-queue 55-79% confidence. |
| **Transcript History** | SQLite storage with full text, timestamps, detected verses. |
| **Duplicate Suppression** | 30-second cooldown per verse reference. |

### 7.2 Hardware Requirements

| Configuration | Recommendation |
|---------------|----------------|
| **GPU-Accelerated** | 4GB VRAM GPU + 8GB RAM |
| **CPU-Only** | 16GB RAM (Qwen3-ASR on CPU) |

### 7.3 Implementation Phases

| Phase | Duration | Deliverables |
|-------|----------|--------------|
| **Phase 1: ASR Integration** | 1.5 weeks | Qwen3-ASR engine, VAD chunking, streaming/offline inference. |
| **Phase 2: Direct Reference Detection** | 1 week | Regex pattern matching, `BOOK_ALIAS_MAP`, <5ms lookup. |
| **Phase 3: Semantic Detection** | 1.5 weeks | MPNet embeddings, FAISS index builder, similarity search. |
| **Phase 4: Confidence & Auto-Mode** | 1 week | Hybrid scoring, auto-display/queue logic, cooldown mechanism. |
| **Phase 5: Transcript History** | 0.5 week | SQLite storage, review UI, multi-select export. |
| **Phase 6: Polish & Testing** | 0.5 week | Cross-platform testing, performance tuning. |

**Total: 6 weeks**

---

## 8. Category 6: AI Sermon Notes Export (v2.0.0)

### 8.1 Features

| Feature | Description |
|---------|-------------|
| **Local LLM Summarization** | LFM2-2.6B-Transcript (offline, <3GB RAM) for cloud-quality meeting summarization. |
| **Biblical Analysis (Optional)** | Baptist-Christian-Bible-Expert-v2.0-24B or Reformed-Christian-Bible-Expert-12B as downloadable enhancements. |
| **Structured Export** | Title, outline, key points, full verse texts, notable quotes, practical applications. |
| **Document Generation** | `.docx` export via `python-docx`. |
| **User-Friendly Dialog** | Select transcript session, click generate. ~6-7 second processing time. |

### 8.2 Implementation Phases

| Phase | Duration | Deliverables |
|-------|----------|--------------|
| **Phase 1: Summarization Integration** | 1 week | LFM2-2.6B-Transcript pipeline, prompt engineering. |
| **Phase 2: Document Generation** | 0.5 week | `python-docx` template, structured output. |
| **Phase 3: Polish & Testing** | 0.5 week | End-to-end testing, prompt refinement. |

**Total: 2 weeks**

---

## 9. Current Status

### 9.1 v0.7.9 — Category 1 Complete ✅

All stabilization issues from the v0.7.2 phase have been resolved:

| Priority | Issue | Status | Resolution |
|----------|-------|--------|------------|
| **P0** | Item Identity Model | ✅ Fixed | `entry_id` UUID system implemented; `new_entry_id()` helper; all commands target `entry_id` |
| **P0** | Dirty State Tracking | ✅ Fixed | `QUndoStack.setClean()` on save; `isClean()` for accurate save prompts |
| **P1** | Backup Rotation | ✅ Fixed | `_rotate_backups()` called before overwrite; `backup_warning` signal for failures |
| **P1** | Open Without Confirmation | ✅ Fixed | `_maybe_save_changes()` guards all Open/New operations with Save/Discard/Cancel dialog |
| **P1** | Empty Playlist Drop Target | ✅ Fixed | `dropEvent` uses `rowCount()` (not `rowCount() - 1`) for append semantic |
| **P1** | Queue Drag-Reorder Bug | ✅ Fixed | `move_item()` caps `dest = min(dest, n)`; full live-index tracking for all motion cases |

### 9.2 Verification

Code verified at:
- `models.py:177` — `dest = min(dest, n)` in `PlaylistModel.move_item()`
- `models.py:359` — `dest = min(dest, n)` in `QueueModel.move_item()`
- `models.py:333-335` — live-index shift on insert
- `models.py:363-375` — full live-index tracking on move
- `playlist_panel.py:209` — `to_row = self.model().rowCount()` (empty list fix)
- `document_manager.py:53` — `backup_warning` signal defined
- `document_manager.py:296` — `backup_warning.emit(msg)` on failure

---

## 10. Technical Stack

| Layer | Technology |
|-------|------------|
| **UI Framework** | PyQt6 / Qt 6.x |
| **Database** | SQLite 3 (WAL mode) |
| **Theme Engine** | JSON + QSS stylesheets |
| **Display Rendering** | QML (for lower-third hardware acceleration) |
| **NDI Output** | NDI 6.3 SDK |
| **HTTP/WebSocket** | `aiohttp` or `quart` |
| **ASR Engine** | Qwen3-ASR-1.7B, Voxtral Mini 3B |
| **Embeddings** | sentence-transformers (all-mpnet-base-v2) + FAISS |
| **LLM (Optional)** | LFM2-2.6B-Transcript, llama-cpp-python |
| **Document Export** | `python-docx` |

---

## 11. File Organization

```
VerseFlow/
├── 2. Source Code/
│   ├── main.py              # Application entry, MainWindow, HomePanel
│   ├── models.py            # PlaylistModel, QueueModel
│   ├── document_manager.py  # Document lifecycle, undo commands
│   ├── queue_panel.py       # QueuePanel UI implementation
│   ├── playlist_panel.py    # PlaylistPanel UI implementation
│   ├── display_window.py    # Congregation display
│   ├── theme.py             # Theme engine
│   ├── settings.py          # Settings manager
│   ├── hotkey_manager.py    # Global hotkey backend
│   └── icons.py             # SVG icon utilities
├── 3. Database/
│   └── verseflow.db         # Bible translations (SQLite)
├── data/
│   ├── settings.json        # User preferences
│   └── cross_references.json # Bible cross-references
└── themes/                  # Theme JSON files
```

---

## 12. Next Steps

### Immediate (v1.0.0 RC Preparation)

1. **Critical Code Quality Fixes (Post-v0.7.10):**
   - [x] Add `.gitignore` to exclude `__pycache__/`, `*.pyc`, `.backups/`, `.venv/` (v0.7.12 structural cleanup)
   - [x] Modularize monolithic `main.py` (3,745 → 303 lines) — extracted `db_layer.py`, `display_core.py`, `navigator.py`, `editors.py`, `home_panel.py`; deleted dead `NavButton` class (v0.7.11). ~~NOTE: This refactoring has not been audited.~~ **AUDITED v0.7.12**
   - [x] Replace `parent.parent()` traversal with signal-based communication — `stack_nav_requested` signal + `verse_clicked` signal (v0.7.12)
   - [x] Replace debug `print()` statements with `logging` module — 24 statements across 6 files (v0.7.12)

2. **Regression Testing:**
   - [x] Test all 6 bug fixes from v0.7.2 stabilization
   - [x] Verify global hotkeys work when app is in background
   - [ ] Test cross-platform behavior (Windows primary, Linux/macOS fallback)
   - [ ] Verify v0.7.10 fixes: drag-drop with malformed JSON, settings persistence, crossrefs error warnings
   - See `REGRESSION_TESTING.md` for detailed test procedures

3. **Performance Validation:**
   - [x] Large playlist handling (>200 items)
   - [x] Rapid undo/redo stress test
   - [x] Display preview font fitting at 4K resolution

4. **Documentation:**
   - [ ] Update user guide with hotkey reference
   - [ ] Document `.verseplaylist` file format for external tools

### Then (v1.1.0 Development) — ✅ COMPLETE

1. ✅ Create feature branch `feature/v1.1.0-lower-third`
2. ✅ Complete Phase 1 ChannelManager wrapper foundation
3. ✅ Complete Phase 2 fullscreen mode encapsulation / renderer seam preparation
4. ✅ Complete Phase 3 lower-third renderer with painted-widget implementation
5. ✅ Complete Phase 4 dual output channels (Main + Alt independence)
6. ✅ Complete Phase 5 tabbed preview (Main/Alt tabs with status row)
7. ✅ Complete Phase 6 per-channel settings and theme foundation
8. 🔄 Complete Phase 7 release hardening and full regression

### Next (v1.2.0 Development)

1. Create feature branch `feature/v1.2.0-ndi-api`
2. Implement NDI output with alpha channel support
3. Build HTTP REST API and WebSocket API
4. Add OBS Browser Source overlay endpoint

---

## 13. Changelog

| Date | Version | Changes |
|------|---------|---------|
| 2026-04-14 | v0.7.0 | Initial Stage 1 completion (operator panel enhancements) |
| 2026-04-18 | v0.7.2 | Stabilization: fixing identity model, document lifecycle, drag-drop issues |
| 2026-04-19 | v0.7.5 | Cross-reference wiring, keyboard accelerators (`Ctrl+L`, `Ctrl+Z/Y`), Edit menu |
| 2026-04-20 | v0.7.6 | Hotkey Manager Stages 1-3: Facade, backend contract, Windows native (`RegisterHotKey`) |
| 2026-04-20 | v0.7.7 | Hotkey Stage 4: Settings integration with validation/normalization |
| 2026-04-20 | v0.7.8 | Hotkey Stage 5: MainWindow wiring, 4 actions bound (`Ctrl+Shift+V/X/Q/L`) |
| 2026-04-20 | v0.7.9 | Hotkey Stage 6: Guardrails, idempotent start, safe rebind; **Category 1 COMPLETE** |
| 2026-04-22 | v0.7.10 | Critical fixes: json.loads security validation, platformdirs settings path, BOOK_NAMES constants extraction, crossrefs error exposure |
| 2026-04-22 | v0.7.11 | **main.py modularization** — 3,745 → 303 lines; extracted 5 new domain modules (`db_layer`, `display_core`, `navigator`, `editors`, `home_panel`); deleted dead `NavButton`; all 14 unit tests + end-to-end smoke test pass. |
| 2026-04-23 | v0.7.12 | **Modularization audit fixes + structural cleanup** — `parent.parent()` → signals (2 sites); `print()` → `logging` (24 stmts, 6 files); `db._conn()` → `get_chapter_verses()`; direct state mutation → public API; `.gitignore` added; `__pycache__` purged; PII relocated; legacy code archived; all 14 unit tests pass |
| 2026-05-04 | v1.1.0 | **Advanced Display Modes** — ChannelManager + DisplayChannel adapter architecture; lower-third renderer with logo placeholder; dual output channels (Main/Alt); tabbed preview with status row; per-channel settings persistence and theme foundation; 4 bug fixes (navigator state sync, null safety, QApplication guard, hasattr/getattr) |

---

*This document is the single source of truth for VerseFlow development. All other roadmap documents are deprecated in favor of this unified specification.*
