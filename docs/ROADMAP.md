# VerseFlow Unified Roadmap

> **Consolidated from:** `First draft..txt`, `Verseflow help.txt`, `PROJECT_PLAN.md`  
> **Last Updated:** May 27, 2026
> **Current Status:** v1.2.0 — NDI Output COMPLETE — v1.3.0 Phase 1 ✅ SIGNED OFF (May 16) — v1.3.0 Phase 2 Theme Designer UI ✅ SIGNED OFF (May 19) — v1.3.0 Phase 3 Advanced Properties ✅ SIGNED OFF (May 23) — v1.3.0 Phase 4 ✅ SIGNED OFF (May 24) — v1.3.1 Phase 0 ✅ COMPLETE — v1.3.1 Phase 1 ✅ COMPLETE (May 25) — v1.3.1 Phase 2 ✅ COMPLETE (May 25) — v1.3.1 Phase 3 ✅ COMPLETE (May 27) — v1.3.1 Phase 4 ✅ SIGNED OFF (May 27) — v1.3.1 COMPLETE

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
| **v1.1.1** | 2a | Output Target Routing (Link Channels replacement) | — | ✅ Done (May 12, 2026) |
| **v1.2.0** | 3 | NDI Output (HTTP/WebSocket API deferred) | 6 weeks | ✅ Done (May 13, 2026) |
| **v1.3.0** | 4 | Theme Designer + Background Images/Video | 4 weeks | ✅ Done (May 24) |

> **Deviation Note (May 12, 2026):** v1.1.1 — Output Target Routing completes the v1.1.0 Dual Output Channels architecture. The original v1.1.0 shipped with a binary "Link Channels" toggle that only mirrored Main↔Alt. The three-mode Output Target selector (Main / Alt / All) with state-aware `switch_target` propagation is the finished channel architecture originally scoped for v1.1.0. Two bugs discovered and fixed during final QA: (1) `switch_target` cleared channels before capturing the last-live verse, and (2) lazy display window creation fired a stale `display_opened` signal that reset navigator State 2.
| **v1.3.1** | 4a | UI Polish & Consistency (operator panel chrome) | 2.5 weeks | ✅ Phase 0 + Phase 1 Complete |
| **v1.3.2** | 4b | Interaction Polish & Layout Hardening (operator panel) | ~1 week | 📋 Planned |
| **v1.4.0** | 5 | AI Speech Transcription | 6 weeks | 📋 Planned |
| **v2.0.0** | 6 | AI Sermon Notes Export (Production Ready) | 2 weeks | 📋 Planned |

**Total Estimated Development Time:** 25.5 weeks (~6.5 months) from v1.0.0 to v2.0.0.

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

| Feature | Description | Status |
|---------|-------------|--------|
| **NDI Output** | Two independent NDI streams ("VerseFlow Main", "VerseFlow Alt") at 30/60 fps with alpha channel support (NDI 6.3). | ✅ Phase 1 (Main channel) complete |
| **NDI Stream Monitoring** | Health overlay in operator panel (bitrate, FPS, frame drops). | 📋 Phase 2 |
| **HTTP REST API** | Endpoints for verse lookup (`GET /api/verses`) and display control (`POST /api/display/push`, `POST /api/display/clear`). | ⏸️ Deferred indefinitely |
| **WebSocket API** | JSON-RPC over WebSocket for real-time bidirectional control with live state push. | ⏸️ Deferred indefinitely |
| **OBS Browser Source Overlay** | HTTP endpoint (`/overlay`) serving HTML/CSS that mirrors congregation display. | ⏸️ Deferred indefinitely |
| **Bitfocus Companion Module** | Pre-built module for Stream Deck integration. | ⏸️ Deferred indefinitely |

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

| Phase | Duration | Deliverables | Status |
|-------|----------|--------------|--------|
| **Phase 1: NDI Core** | 1.5 weeks | `NDISender` class, `ndi_bridge.py` ctypes wrapper, `NDIManager` coordinator, Main channel capture loop at 30fps, `DisplayChannel.display_window` forwarding property, graceful DLL-missing fallback. | ✅ Complete |
| **Phase 2: Per-Channel Senders** | 1 week | Alt channel sender, monitor disconnect handling, Push All/Clear All with NDI, verify mode-change-while-live handled naturally by grab(). | ✅ Complete |
| **Phase 3: Alpha Channel Validation** | 0.5 week | Verify lower-third RGBA transparency composites correctly in OBS; fix rendering bugs. | ✅ Complete |
| **Phase 4: NDI Operator Visibility** | 0.5 week | Status indicator in preview row, NDI config card in Settings panel. | ✅ Complete |
| **Phase 5: Settings Integration & Regression** | 0.5 week | Persist `ndi_enabled`/`ndi_source_name` per channel, full regression matrix. | ✅ Complete |
| ~~Phase 3: HTTP API Foundation~~ | ~~1 week~~ | ~~`aiohttp` server, REST endpoints, local-only binding.~~ | ⏸️ Deferred |
| ~~Phase 4: WebSocket API~~ | ~~1 week~~ | ~~JSON-RPC over WebSocket, real-time state push.~~ | ⏸️ Deferred |
| ~~Phase 5: OBS Overlay & Companion~~ | ~~1 week~~ | ~~Browser source endpoint, Companion module.~~ | ⏸️ Deferred |
| ~~Phase 6: Polish & Testing~~ | ~~1 week~~ | ~~Cross-platform NDI performance, API documentation, security audit.~~ | ⏸️ Deferred |

**Total: 6 weeks**

---

## 6. Category 4: Customization & Theming (v1.3.0)

### 6.1 Features

| Feature | Description |
|---------|-------------|
| **In-App Theme Designer** | Three-panel interface: saved themes list (left), embedded `DisplayWidget` preview (center), property editor (right). |
| **Font Customization** | Import custom fonts (`.ttf`, `.otf`) via `QFontDatabase.addApplicationFont()`. |
| **Animation/Transitions** | Fade transitions (v1.3.0); slide transitions deferred to v1.3.x. |
| **Background Images** | PNG/JPEG/SVG image backgrounds (v1.3.0). MP4 video backgrounds deferred to v1.3.x — handled downstream by broadcast chain (OBS/vMix). |
| **Preset Theme Library** | 8-10 professionally designed themes shipped with application. |
| **Per-Channel Themes** | Each output channel (Main/Alt) can use different themes. |

### 6.2 Implementation Phases

| Phase | Duration | Deliverables |
|-------|----------|--------------|
| **Phase 1: Theme Engine Foundation** | 1.5-2 weeks | `Theme` data class, JSON serialization (`.json` + `schema_version`), `ThemeManager` per-channel support, `DisplayWidget` extraction. |
| **Phase 2: Theme Designer UI** | 1.5 weeks | Three-panel interface, embedded `DisplayWidget` preview (pixel-identical to live display), live updates. |
| **Phase 3: Advanced Properties** | 1 week | Font import, fade transitions, image background support (PNG/JPEG/SVG). | ✅ Complete (May 23) |
| **Phase 4: Preset Library & Polish** | 1 week | Create 8-10 preset themes, final testing, documentation. | ✅ Complete (May 24) |

**Total: 4 weeks**

---

## 6a. Category 4a: UI Polish & Consistency (v1.3.1)

### 6a.1 Features

| Feature | Description |
|---------|-------------|
| **Token-based typography system** | Phase 0 introduces a `typography` section in every theme JSON. `generate_stylesheet()` emits one selector per named scale via a loop. Adding a new size is a JSON edit. Themes can override per-scale (high contrast may want larger sizes for accessibility). |
| **Property-based QSS migration** | All operator panels (settings, home, theme designer) migrate from inline `setStyleSheet()` calls to `setProperty()`-based QSS rules in `theme.py:generate_stylesheet()`. Single source of truth. |
| **Two-scale typographic hierarchy** | `compact` variant (9px uppercase letterspaced) for sidebars and inline metadata; `standard` variant (13–14px normal case) for full-width sections. Both are entries in the typography system, not hardcoded selectors. Fixes the inverted hierarchy in settings panel. |
| **Section iconography** | 16px icons next to every section header (keyboard / gear / layers / broadcast / palette). Theme-aware tinting via `icons.py` factory extension. |
| **Hover affordance correction** | Hover states removed from non-interactive cards. Reserved for buttons, links, queue/history items. |
| **Layout fragility fixes** | NDI rows reflow on narrow windows; Hotkey Diagnostics buttons placed side-by-side; Channel Settings card reorders to put primary controls before navigation. |
| **Error color promoted to theme token** | New `red_text` token across all 10 themes; `QLabel[error="true"]` selector. Eliminates the last inline `setStyleSheet()` in settings panel. |

### 6a.2 Implementation Phases

| Phase | Duration | Deliverables |
|-------|----------|--------------|
| **Phase 0: Typography System Foundation** | 1 day | ✅ Complete. New `typography` section in all 10 theme JSONs (4 named scales: compact/standard/body/hint); `Theme.typography` parser; `generate_stylesheet()` emits typography selectors via loop. |
| **Phase 1: Settings Panel Polish Closeout** | 0.5 week | ✅ Complete (May 25). `red_text` token in all 10 themes; `QLabel[error="true"]` selector; hover-on-card/panel removal; section header variant migration; deprecated alias removed; NDI reflow; Hotkey/Channel layout fixes; guard scripts updated. |
| **Phase 2: Iconography System & Settings Icons** | 0.5 week | ✅ Complete (May 25). 5 new SVG factory functions in `icons.py`; `_make_section_header()` accepts optional icon; settings panel + designer header icons applied; `_refresh_section_header_icons()` for theme-switch retinting; pytest test suite; guard script check added. |
| **Phase 3: Home Panel Migration** | 0.5 week | ✅ Complete (May 25). `home_panel.py` inline stylesheets reduced from 43 to ≤ 6 (deviated from ≤3 — see Phase 3 Implementation Plan Deviation 7); sidebar keeps compact variant; non-interactive panel hover removed. |
| **Phase 4: Theme Designer Polish & Sign-Off** | 0.5 week | ✅ Complete (May 27). `theme_designer.py` migrated to property-based QSS (40 → 4 category-(a) inline calls); 14 new selectors in `generate_stylesheet()`; helper methods removed; column headers added; mode buttons use value-encoded property selectors with unpolish/polish; guard scripts updated. |

**Total: 2.5 weeks**

---

## 6b. Category 4b: Interaction Polish & Layout Hardening (v1.3.2)

> **Prerequisite:** v1.3.1 UI Polish & Consistency must be complete before v1.3.2 begins. The v1.3.1 QSS migration pipeline must be stable — v1.3.2 depends on property-based selectors being the canonical styling pattern.

### 6b.1 Features

| Feature | Description |
|---------|-------------|
| **Column width rebalancing** | Redistribute Home panel left/center/right proportions. Consider collapsing sidebar to an icon rail (~56px) or reducing to ~220px to free control-column space. The center column (search, mode toggle, display controls, output target) is the most interaction-dense zone and currently gets only 320px (25% of default window width). |
| **Search loading indicator** | Add a spinner or progress pulse during `_do_search` chapter lookups and keyword searches. The 250ms debounce is correct, but the silent wait after it isn't — operators need feedback that work is in progress. |
| **Destructive action confirmations** | Add confirmation dialogs for live history clear and queue clear. The red trash icon alone is insufficient defense for an operator mid-service. |
| **NDI status visibility** | Promote the NDI indicator from the 8px preview status footnote to a colored dot badge in the preview tab header or alongside the output target selector. NDI capture state is mission-critical and must be scannable at a glance. |
| **Mode dropdown sizing** | Increase the "Fullscreen" / "Lower Third" dropdowns from 26px height / 9px font to a more comfortable target size. These control critical output behavior. |
| **Theme Designer Apply feedback** | When the operator clicks Apply in the Theme Designer, the confirmation writes to the main window status bar — which may be obscured when the designer is the active stacked widget. Add in-panel confirmation or a toast. |
| **Compact typography letter-spacing review** | The `compact` variant (9px / 2px letter-spacing / uppercase) is retained for sidebars per Decision 2, but the 2px letter-spacing at 9px font size (~22% of font size in inter-character space) should be evaluated for legibility. May reduce to 1.5px or 1px depending on visual review after v1.3.1 ships. |

### 6b.2 Implementation Phases

| Phase | Duration | Deliverables |
|-------|----------|--------------|
| **Phase 1: Interaction fixes** | 0.5 week | Search loading indicator, destructive confirm dialogs, Theme Designer Apply feedback, NDI status badge promotion. |
| **Phase 2: Layout hardening** | 0.5 week | Column width redistribution, mode dropdown sizing, compact typography letter-spacing review. |

**Total: ~1 week**

### 6b.2 Non-Regression

- No theme schema changes. No new JSON keys. No `generate_stylesheet()` modifications required (NDI badge and loading indicators may add selectors, but they use existing color tokens).
- No congregation display rendering changes. All changes are operator panel only.
- No NDI pipeline changes — only operator visibility of existing NDI state.
- All v1.3.1 hotkey, channel, and theme behavior preserved.

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

**v0.7 Code verified at:**
- `models.py:177` — `dest = min(dest, n)` in `PlaylistModel.move_item()`
- `models.py:359` — `dest = min(dest, n)` in `QueueModel.move_item()`
- `models.py:333-335` — live-index shift on insert
- `models.py:363-375` — full live-index tracking on move
- `playlist_panel.py:209` — `to_row = self.model().rowCount()` (empty list fix)
- `document_manager.py:53` — `backup_warning` signal defined
- `document_manager.py:296` — `backup_warning.emit(msg)` on failure

**v1.1.0 — v1.3.0 Automated Verification:**
- **`scripts/pre_commit_checks.py`** — 10 check groups (Phase 5-6, NDI Phases 1-4, Theme Engine Phases 1-4, Typography Phase 0, Output Target Routing)
- **`scripts/verify_critical_fixes.py`** — 7 verify groups (Phase 5-6, NDI Phases 1-2, Target Routing, Theme Designer, Advanced Properties, Preset Library, Color Consistency)
- **`tests/test_preset_library.py`** — 18/18 tests pass (JSON integrity, color consistency, ThemeCardWidget, thumbnail cleanup, grid layout)
- **`tests/test_theme_engine.py`** — Theme schema v2, upgrade, persistence API
- **`docs/REGRESSION_TESTING.md`** — Manual test matrices §8–§18

---

## 10. Technical Stack

| Layer | Technology |
|-------|------------|
| **UI Framework** | PyQt6 / Qt 6.x |
| **Database** | SQLite 3 (WAL mode) |
| **Theme Engine** | JSON + QSS stylesheets |
| **Display Rendering** | PyQt6 `QWidget.paintEvent()` — `DisplayWidget` extracted from `DisplayWindow` |
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
├── src/
│   ├── main.py              # Application entry, MainWindow
│   ├── core/                # ChannelManager, settings, models
│   ├── display/             # DisplayWindow, DisplayWidget, DisplayChannel
│   ├── ui/                  # HomePanel, SettingsPanel, ThemeDesigner
│   ├── ndi/                 # NDI bridge, sender, manager
│   └── utils/               # Theme engine, icons, constants
├── database/                # Bible translations (SQLite)
├── data/                    # User preferences, cross-refs
└── docs/                    # Documentation
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
8. ✅ Complete Phase 7 release hardening and full regression

### Next (v1.2.0 Development) — ✅ COMPLETE

1. ~~Create feature branch `feature/v1.2.0-ndi-api`~~
2. ~~Implement NDI Bridge + NDISender skeleton + capture loop (Phase 1)~~ ✅ Complete (May 8, 2026)
3. Implement per-channel senders and lifecycle management (Phase 2)
4. Validate alpha channel compositing in OBS (Phase 3)
5. Add NDI operator visibility — status indicator, settings card (Phase 4)
6. Settings integration and full regression (Phase 5)
7. ~~Build HTTP REST API and WebSocket API~~ ⏸️ Deferred indefinitely
8. ~~Add OBS Browser Source overlay endpoint~~ ⏸️ Deferred indefinitely

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
| 2026-05-06 | v1.1.1 | **Typography Optimization** — Optimized lower-third font rendering by removing artificial 64pt cap, reclaiming vertical margins, and synchronizing layout padding for perfect centering. |
| 2026-05-07 | v1.1.2 | **LT Typography Refactoring** — Independent reference font fitting (dedicated 36px row height), square logo placeholder with church alias label below, Settings panel "General" card for church alias input, removed inaccurate line-count heuristic. Bugs 50–54 fixed. |
| 2026-05-08 | v1.2.0 Phase 1 | **NDI Bridge + NDISender Skeleton** — `ndi_bridge.py` ctypes wrapper (3-tier DLL search, correct FourCC 0x41524742, endianness guard), `ndi_sender.py` read-only observer with 30fps `grab()` capture loop and signal amplification guard, `ndi_manager.py` SDK lifecycle coordinator with `available` property, `DisplayChannel.display_window` forwarding property, `closeEvent` NDI-aware shutdown ordering, pre-commit and verify guard suites. Graceful fallback when NDI SDK not installed. HTTP/WebSocket API deferred indefinitely. |
| 2026-05-15 | v1.3.0 Phase 1 | **Theme Engine v2 + DisplayWidget Extraction** — 26 method/block units extracted (~900 lines) from DisplayWindow to new DisplayWidget; Theme Engine v2 with schema versioning (`KNOWN_SCHEMA_VERSIONS`), `_upgrade_to_v2`, `set_app_theme`; per-channel theme isolation; 3 JSON theme files updated to schema v2; DisplayChannel decoupled `apply_settings()`; `settings.py` defaults fixed (4x `"default"` → `"dark_gold"`); `main.py` wired `set_app_theme()` + per-channel loop; guard scripts migrated + `check_phase1_theme_engine()` added. Automated guard scripts pass. Bug 73 fixed & verified: overlay state machine reset via step reorder. |
| 2026-05-22 | v1.3.2 | **Technical debt logged** — Interaction Polish & Layout Hardening category added to roadmap as pre-v1.4.0 blocker. Covers: column width rebalancing, search loading indicator, destructive confirm dialogs, NDI status visibility, mode dropdown sizing, Theme Designer Apply feedback, compact typography letter-spacing review. Sub-roadmap to be drafted after v1.3.1 ships. |
| 2026-05-23 | v1.3.0 Phase 3 | **Advanced Properties** — Font import via `QFontDatabase.addApplicationFont()`; cross-fade transitions on verse change; PNG/JPEG/SVG background images with fill/fit/stretch modes; property editor schema (33 properties); theme designer crash fix (font family combo box extraction); settings panel QSS migration (25/26 inline stylesheets → property-based selectors). Automated guard scripts pass. ✅ |
| 2026-05-23 | v1.3.1 fix | **Color regression fix** — 6 hardcoded hex color fallbacks in `display_widget.py` replaced with dynamic theme token lookups (`self._theme.c()` / per-section `.get()`), enabling Display Colors → Verse text and per-section ref_color/verse_color to propagate correctly in both fullscreen and lower-third modes. |
| 2026-05-23 | v1.3.0 Phase 4 | **Preset Library & Polish** — 7 new preset themes (midnight_blue, warm_amber, forest_green, royal_purple, crimson_red, slate_gray, pastel_calm) — 46 colors each, WCAG AAA contrast. Grid-based ThemesListPanel with ThemeCardWidget thumbnails. Automatic 0.125x thumbnail generation on save/open. .thumb.png cleanup on theme delete. Property-based QSS for card hover/select/builtin states. 10 total built-in themes. |
| 2026-05-24 | v1.3.0 Phase 4 (fix) | **Color leak fix** — 6 dark presets had midnight_blue-tinted structural chrome (bg_sidebar, bg_sidebar_end, bg_panel_start/end, bg_input, bg_preview_center/edge, bg_statusbar, nav_active_text). Replaced with hue-matched values per preset. input_border switched from accented to neutral rgba(255,255,255,0.08) matching original 3 themes. royal_purple.json corruption repaired. All 11 guard checks pass. ✅ |
| 2026-05-28 | v1.3.x post-signoff polish | **Theme thumbnail polish** — built-in thumbnails now use per-theme `thumbnail_style` presentation modes to improve recognition and professionalism. Fixed the thumbnail lower-third key mapping (`background_color` / `background_alpha`), fixed readable verse text in thumbnails, regenerated all built-in `.thumb.png` files, and added `logs/thumbnails_contact_sheet.png` for visual QA. Thumbnail presentation is intentionally richer than the live display; live fidelity remains unchanged. |
| 2026-05-25 | v1.3.1 Phase 1 | **Settings Panel Polish Closeout** — red_text token in all 10 themes; QLabel[error="true"] selector; card/panel hover removed; _make_section_header variant migration; deprecated alias removed; hotkey buttons side-by-side; channel card reordered with separator; NDI two-row reflow; guard scripts updated (EXPECTED_COLOR_TOKENS→47, phase1 check function added). Both guard scripts pass with 0 errors. ✅ |
| 2026-05-25 | v1.3.1 Phase 2 | **Iconography System & Settings Icons** — 5 SVG factory functions added to icons.py (keyboard, gear, layers, broadcast, palette); _make_section_header() extended with optional QIcon parameter; 5 settings panel section headers receive icons (Hotkeys, General, Channel, NDI, Design); palette icon in Theme Designer header; _refresh_section_header_icons() retinting support; pre_commit_checks.py phase2 check function added; pytest test_icons.py with 4 tests for all SVGs. Guard script and pytest both pass with 0 errors. ✅ |
| 2026-05-27 | v1.3.1 Phase 3 | **Home Panel QSS Migration** — 43→6 inline setStyleSheet() calls in home_panel.py; property-based selectors for all remaining widgets (nav tabs, version badge, section headers, gold dots, navigation buttons, show/hide/destructive buttons, hint labels, output target buttons, combo modes, preview tabs, history panel). Phase 3 Implementation Plan documents 9 deviations. Guard script passes with 0 errors. 1 regression caught during manual testing: `#` character stripped from congregation display verse text (`_strip_extra()` in `display_widget.py`, `display_preview.py`) — fixed. ✅ |

---

*This document is the single source of truth for VerseFlow development. All other roadmap documents are deprecated in favor of this unified specification.*
