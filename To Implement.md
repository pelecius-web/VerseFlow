Here is the combined robust Phase 5 plan:

---

## Phase 5 — Tabbed Preview & Channel Status UI

### Goal
Convert the single-channel `DisplayPreview` (Main only, 300px fixed height) into a tabbed preview showing both Main and Alt channels with a status info row below.

### Architecture Decisions

| Decision | Rationale |
|---|---|
| Access Alt controller via `ChannelManager` | `channel_manager.get_channel("alt").controller` — no `main.py` change needed |
| No wrapper class | `DisplayPreview(display, parent)` already accepts any display-like controller; just instantiate twice |
| Keep status row below preview | Matches sub-roadmap mockup; removes redundancy with center column labels |
| `set_preview_verse` routes to Main tab | Queue/playlist previews are part of the Main workflow |
| QTabWidget for tab switching | Standard Qt pattern; tab bar styled to match dark theme |

### Files Modified

| File | Changes |
|---|---|
| `home_panel.py` | Replace single preview with QTabWidget + status row; update `set_preview_verse`; update `_update_channel_status` |
| `pre_commit_checks.py` | Add Phase 5 static guards |
| `verify_critical_fixes.py` | Add Phase 5 source checks |
| `display_channel.py` | No changes — `.controller` property already exists |
| `main.py` | No changes — Alt controller accessed via ChannelManager |

---

### Implementation Steps

#### Step 1: Replace single preview with QTabWidget

**File:** `home_panel.py` — lines ~596-620

Replace:
```python
# TOP: Display Preview (300px)
preview_box = QFrame()
preview_box.setProperty("panel", True)
preview_box.setFixedHeight(300)
...
self.preview = DisplayPreview(self.display)
preview_layout.addWidget(self.preview)
right_layout.addWidget(preview_box)
```

With:
```python
# TOP: Tabbed Preview (300px)
preview_box = QFrame()
preview_box.setProperty("panel", True)
preview_box.setFixedHeight(300)
preview_layout = QVBoxLayout(preview_box)
preview_layout.setContentsMargins(0, 0, 0, 0)
preview_layout.setSpacing(0)

from PyQt6.QtWidgets import QTabWidget
self.preview_tabs = QTabWidget()
self.preview_tabs.setFixedHeight(280)
self.preview_tabs.setStyleSheet("""
    QTabWidget::pane { border: none; background: transparent; }
    QTabBar::tab { 
        background: rgba(30,30,50,0.6); color: rgba(200,160,60,0.5);
        padding: 4px 16px; font-weight: bold; border: none;
    }
    QTabBar::tab:selected { color: #c8a03c; background: rgba(200,160,60,0.12); }
    QTabBar::tab:hover { color: #d4a84b; }
""")

# Tab 0: Main
self.preview_main = DisplayPreview(self.display)
self.preview_tabs.addTab(self.preview_main, "Main")

# Tab 1: Alt
alt_controller = self.channel_manager.get_channel("alt").controller
self.preview_alt = DisplayPreview(alt_controller)
self.preview_tabs.addTab(self.preview_alt, "Alt")

preview_layout.addWidget(self.preview_tabs)

# Status info row below tabs
self.lbl_preview_status = QLabel("MAIN · CLEAR — Fullscreen    ALT · CLEAR — Lower Third")
self.lbl_preview_status.setFont(QFont("Segoe UI", 8))
self.lbl_preview_status.setStyleSheet("color: rgba(255,255,255,0.35); background: transparent; padding: 4px 8px;")
self.lbl_preview_status.setFixedHeight(20)
preview_layout.addWidget(self.lbl_preview_status)

right_layout.addWidget(preview_box)
```

#### Step 2: Remove redundant center-column status labels

**File:** `home_panel.py`

Remove `lbl_main_status` and `lbl_alt_status` from center column. The info row below the preview tabs (Step 1) replaces them.

Also remove the DUAL OUTPUT section's status label references from `_update_channel_status`.

#### Step 3: Update `_update_channel_status` for tab indicators + status row

**File:** `home_panel.py`

Replace the center-column label updates with tab indicator updates + single status row:

```python
def _update_channel_status(self, channel_name: str, state: dict):
    if state is None:
        return

    # Update tab indicators (● live, ○ clear)
    is_live = state.get("is_live")
    tab_index = 0 if channel_name == "main" else 1
    indicator = "●" if is_live else "○"
    name = "Main" if channel_name == "main" else "Alt"
    self.preview_tabs.setTabText(tab_index, f"{name} {indicator}")

    # Update single status row below preview
    self._update_preview_status_row()
```

Add helper:
```python
def _update_preview_status_row(self):
    main_state = self.channel_manager.get_channel("main").get_state()
    alt_state = self.channel_manager.get_channel("alt").get_state()

    def _status_text(state, label):
        status = state.get("is_live")
        mode = state.get("display_mode", "fullscreen").replace("_", " ").title()
        ref = (state.get("current") or {}).get("reference", "")
        trans = (state.get("current") or {}).get("translation", "")
        if status and ref:
            text = f"{label} — LIVE — {mode} — {ref}"
            if trans:
                text += f" {abbreviate_translation(trans)}"
        else:
            text = f"{label} — CLEAR — {mode}"
        return text

    main_text = _status_text(main_state, "MAIN")
    alt_text = _status_text(alt_state, "ALT")
    self.lbl_preview_status.setText(f"{main_text}    {alt_text}")
```

#### Step 4: Route `set_preview_verse` to Main tab

**File:** `home_panel.py` — line ~1282

Replace:
```python
self.preview.set_preview_verse(verse)
```

With:
```python
self.preview_main.set_preview_verse(verse)
self.preview_tabs.setCurrentIndex(0)  # Switch to Main tab
```

#### Step 5: Add Phase 5 static guards

**File:** `pre_commit_checks.py`

```python
def check_phase5_tabbed_preview():
    errors = []
    with open(SRC / 'home_panel.py', encoding='utf-8') as f:
        hp = f.read()
    if 'QTabWidget' not in hp:
        errors.append("CRITICAL: Phase 5: home_panel.py missing QTabWidget")
    if 'preview_main' not in hp:
        errors.append("CRITICAL: Phase 5: missing preview_main DisplayPreview")
    if 'preview_alt' not in hp:
        errors.append("CRITICAL: Phase 5: missing preview_alt DisplayPreview")
    if 'preview_tabs' not in hp:
        errors.append("CRITICAL: Phase 5: missing preview_tabs QTabWidget")
    if 'lbl_preview_status' not in hp:
        errors.append("CRITICAL: Phase 5: missing status info row")
    if 'controller' not in hp or 'get_channel("alt")' not in hp:
        errors.append("CRITICAL: Phase 5: Alt controller access broken")
    return errors
```

#### Step 6: Add Phase 5 source checks

**File:** `verify_critical_fixes.py`

```python
("Phase 5: QTabWidget present", 'QTabWidget' in hp),
("Phase 5: preview_main exists", 'self.preview_main' in hp),
("Phase 5: preview_alt exists", 'self.preview_alt' in hp),
("Phase 5: set_preview_verse routes to main", 'preview_main.set_preview_verse' in hp),
("Phase 5: status row exists", 'lbl_preview_status' in hp),
```

---

### Regression Guard Checklist

- [ ] Push Main → Main tab shows verse, Alt tab unchanged, status row updates
- [ ] Push Alt → Alt tab shows verse, Main tab unchanged
- [ ] Push All → Both tabs update, status row shows both live
- [ ] Clear Main → Main tab clears (○), status row updates
- [ ] Clear Alt → Alt tab clears (○), status row updates
- [ ] Clear All → Both tabs clear
- [ ] Hotkey push/clear → Main preview updates
- [ ] Queue `set_preview_verse` → routes to Main tab, switches to it
- [ ] Tab switch → no display state change (purely visual)
- [ ] Resize window → preview box stays 300px, status row stays 20px
- [ ] `pre_commit_checks.py` and `verify_critical_fixes.py` pass

---

## Phase 6 — Per-Channel Settings and Theme Foundation

### Goal
Persist display mode/theme information per channel without building the full v1.3.0 theme designer.

### Architecture Decisions

| Decision | Rationale |
|---|---|
| Store settings in existing `settings.json` under `"channels"` key | Leverages existing Settings infrastructure; no new persistence layer |
| Channel settings keyed by channel name (`"main"`, `"alt"`) | Matches ChannelManager channel naming; extensible for future N channels |
| Each channel stores `mode`, `theme_id`, `monitor`, `logo_path` | Covers Phase 6 scope without premature v1.3.0 theme designer features |
| Default fallback chain: saved → `"fullscreen"` for mode, `"default"` for theme | Graceful degradation when settings missing or corrupted |
| Apply persisted mode at channel registration time in `main.py` | Ensures Alt channel starts with saved mode before any user interaction |
| `DisplayChannel` exposes `apply_settings()` method | Encapsulates channel-specific setting application; called by ChannelManager |
| Theme fallback: invalid `theme_id` → `"default"` | Prevents crashes from user-edited corrupted settings files |
| Logo fallback: invalid `logo_path` → `None` (shows placeholder) | Lower-third gracefully degrades to placeholder if logo missing |
| Settings saved on mode/theme change (not on every verse push) | Reduces disk I/O; settings represent configuration, not state |

### Files Modified

| File | Changes |
|---|---|
| `settings.py` | Add `get_channel_settings()`, `set_channel_settings()`, `ChannelSettings` dataclass |
| `settings_panel.py` | Add per-channel mode dropdown; wire to `ChannelManager.set_channel_mode()`; save on change |
| `channel_manager.py` | Add `apply_settings()` call in `add_channel()`; emit `channel_settings_changed` signal |
| `display_channel.py` | Add `apply_settings(settings_dict)` method; apply mode/theme on construction |
| `main.py` | After `add_channel("alt", ...)`, call `channel_manager.apply_settings("alt")` with persisted settings |
| `pre_commit_checks.py` | Add Phase 6 static guards |
| `verify_critical_fixes.py` | Add Phase 6 source checks |

### Implementation Steps

#### Step 1: Add channel settings dataclass and persistence

**File:** `settings.py`

Add at top-level:

```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class ChannelSettings:
    """Per-channel display configuration.

    JSON shape follows sub-roadmap spec (nested lower_third, enabled flag).
    """
    enabled: bool = True
    mode: str = "fullscreen"  # "fullscreen" or "lower_third"
    theme_id: str = "default"  # stored as "theme" key in JSON
    monitor: Optional[int] = None  # None = auto-select
    logo_path: Optional[str] = None  # stored inside "lower_third" in JSON
    show_logo_placeholder: bool = True  # stored inside "lower_third" in JSON
```

Add to `SettingsManager` class:

```python
def get_channel_settings(self, channel_name: str) -> ChannelSettings:
    """Load settings for a specific channel with defaults."""
    channels = self._settings.get("channels", {})
    ch = channels.get(channel_name, {})
    lt = ch.get("lower_third", {})

    # DEFENSIVE: Use `.get(key) or default` pattern for nullable values
    # (see SKILL in home_panel.py — handles missing keys AND None values)
    return ChannelSettings(
        enabled=ch.get("enabled", True),
        mode=(ch.get("mode") or "fullscreen"),
        theme_id=(ch.get("theme") or "default"),
        monitor=ch.get("monitor"),
        logo_path=lt.get("logo_path"),
        show_logo_placeholder=lt.get("show_logo_placeholder", True),
    )

def set_channel_settings(self, channel_name: str, settings: ChannelSettings) -> None:
    """Save settings for a specific channel."""
    if "channels" not in self._settings:
        self._settings["channels"] = {}
    self._settings["channels"][channel_name] = {
        "enabled": settings.enabled,
        "mode": settings.mode,
        "theme": settings.theme_id,
        "monitor": settings.monitor,
        "lower_third": {
            "logo_path": settings.logo_path,
            "show_logo_placeholder": settings.show_logo_placeholder,
        },
    }
    self.save()  # SettingsManager uses save(), not _save()
```

Also update `_apply_defaults()` inside `SettingsManager` to include a `"channels"` default, so a fresh install never raises `KeyError`:

```python
# Inside _apply_defaults(), add to the defaults dict:
"channels": {
    "main": {
        "enabled": True,
        "mode": "fullscreen",
        "theme": "default",
        "monitor": None,
        "lower_third": {"logo_path": None, "show_logo_placeholder": True},
    },
    "alt": {
        "enabled": True,
        "mode": "lower_third",
        "theme": "default",
        "monitor": None,
        "lower_third": {"logo_path": None, "show_logo_placeholder": True},
    },
},
```

#### Step 2: DisplayChannel applies settings on construction

**File:** `display_channel.py`

Add method to `DisplayChannel` class:

```python
def apply_settings(self, settings: dict):
    """Apply persisted settings to this channel.

    Called by ChannelManager after channel registration.
    Settings dict is a ChannelSettings.__dict__ from
    SettingsManager.get_channel_settings().
    """
    mode = settings.get("mode")
    if mode in (self.MODE_FULLSCREEN, self.MODE_LOWER_THIRD):
        self.set_display_mode(mode)
    else:
        logger.warning("[DisplayChannel] '%s': invalid mode '%s', using fullscreen",
                       self.name, mode)

    theme_id = settings.get("theme_id")
    if theme_id:
        # Use getattr with None default so we catch both missing AND None-valued
        # theme_mgr — more robust than hasattr() alone.
        theme_mgr = getattr(self._controller, 'theme_mgr', None)
        if theme_mgr is not None:
            # ThemeManager.set_theme() returns False for unknown ids — safe fallback.
            ok = theme_mgr.set_theme(theme_id)
        if not ok:
            logger.warning("[DisplayChannel] '%s': unknown theme_id '%s', keeping current",
                           self.name, theme_id)

    logo_path = settings.get("logo_path")
    if logo_path and hasattr(self._controller, 'set_logo_path'):
        self._controller.set_logo_path(logo_path)
```

#### Step 3: ChannelManager applies settings on add_channel

**File:** `channel_manager.py`

Modify `add_channel()` method:

```python
def add_channel(self, name: str, controller, parent=None):
    """Register a new output channel.

    Loads persisted settings for the channel if available.
    """
    if name in self._channels:
        raise ValueError(f"Channel '{name}' already registered")

    channel = DisplayChannel(name, controller, parent=parent or self)
    self._register_channel(channel)  # Use _register_channel for signal wiring

    # Apply persisted settings after registration so signals are connected.
    self._apply_persisted_settings(name, channel)

    logger.debug("[ChannelManager] Registered channel '%s'", name)
    return channel

def _apply_persisted_settings(self, name: str, channel: DisplayChannel):
    """Load and apply saved settings for a channel."""
    try:
        from settings import SettingsManager  # Correct class name
        settings = SettingsManager()
        ch_settings = settings.get_channel_settings(name)
        channel.apply_settings(ch_settings.__dict__)
    except Exception as exc:
        logger.warning("[ChannelManager] Failed to load settings for '%s': %s", name, exc)
```

#### Step 4: Main.py applies settings after channel registration

**File:** `main.py` — after `add_channel("alt", ...)`

```python
# Register Alt channel
self.channel_manager.add_channel("alt", self.alt_display)

# Settings applied automatically by add_channel via _apply_persisted_settings
# Mode is now restored before any user interaction
```

#### Step 5: Settings panel adds per-channel controls

**File:** `settings_panel.py`

First, update `SettingsPanel.__init__` to accept `channel_manager` and `theme_mgr`:

```python
def __init__(self, hotkey_manager, channel_manager=None, theme_mgr=None, parent=None):
    super().__init__(parent)
    self.hotkey_manager = hotkey_manager
    self.channel_manager = channel_manager  # Required for mode changes
    self.theme_mgr = theme_mgr              # Required for theme dropdown
    self._setup_ui()
```

Also update the instantiation in `main.py`:

```python
# Was:
self.settings_panel = SettingsPanel(self._hotkey_manager)
# Becomes:
self.settings_panel = SettingsPanel(
    self._hotkey_manager,
    channel_manager=self.channel_manager,
    theme_mgr=self._theme_mgr,
)
```

Then add the per-channel section builder and all required helpers:

```python
def _create_channel_section(self, channel_name: str, label: str):
    """Create settings controls for a single channel."""
    from PyQt6.QtWidgets import QComboBox
    section = QFrame()
    layout = QHBoxLayout(section)

    name_label = QLabel(label)
    name_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
    layout.addWidget(name_label)

    # Mode dropdown
    mode_combo = QComboBox()
    mode_combo.addItems(["Fullscreen", "Lower Third"])
    mode_combo.setCurrentText(self._get_saved_mode(channel_name))
    mode_combo.currentTextChanged.connect(
        lambda text: self._on_mode_changed(channel_name, text.lower().replace(" ", "_"))
    )
    layout.addWidget(mode_combo)

    # Theme dropdown
    theme_combo = QComboBox()
    self._populate_themes(theme_combo)
    theme_combo.setCurrentText(self._get_saved_theme(channel_name))
    theme_combo.currentTextChanged.connect(
        lambda text: self._on_theme_changed(channel_name, text)
    )
    layout.addWidget(theme_combo)

    return section

def _get_saved_mode(self, channel_name: str) -> str:
    """Return the persisted display mode for a channel, human-readable."""
    from settings import SettingsManager  # Correct class name
    ch = SettingsManager().get_channel_settings(channel_name)
    return "Lower Third" if ch.mode == "lower_third" else "Fullscreen"

def _get_saved_theme(self, channel_name: str) -> str:
    """Return the persisted theme id for a channel."""
    from settings import SettingsManager
    return SettingsManager().get_channel_settings(channel_name).theme_id

def _populate_themes(self, combo):
    """Populate a QComboBox with available theme names from ThemeManager."""
    if self.theme_mgr is None:
        combo.addItem("default")
        return
    for theme in self.theme_mgr.available_themes():  # ThemeManager.available_themes()
        combo.addItem(theme.id)

def _on_mode_changed(self, channel_name: str, mode: str):
    """Handle mode change — apply immediately and persist."""
    if self.channel_manager:
        self.channel_manager.set_channel_mode(channel_name, mode)
    from settings import SettingsManager, ChannelSettings  # Correct class name
    sm = SettingsManager()
    ch_settings = sm.get_channel_settings(channel_name)
    ch_settings.mode = mode
    sm.set_channel_settings(channel_name, ch_settings)

def _on_theme_changed(self, channel_name: str, theme_id: str):
    """Handle theme change — persist only (theme designer is v1.3.0 scope)."""
    from settings import SettingsManager
    sm = SettingsManager()
    ch_settings = sm.get_channel_settings(channel_name)
    ch_settings.theme_id = theme_id
    sm.set_channel_settings(channel_name, ch_settings)
```

#### Step 6: Add Phase 6 static guards

**File:** `pre_commit_checks.py`

```python
def check_phase6_channel_settings():
    """Verify v1.1.0 Phase 6 per-channel settings persistence."""
    errors = []

    # settings.py checks
    sp_path = SRC / 'settings.py'
    with open(sp_path, encoding='utf-8') as f:
        sp = f.read()
    
    if 'class ChannelSettings' not in sp:
        errors.append("CRITICAL: Phase 6: settings.py missing ChannelSettings dataclass")
    if 'def get_channel_settings' not in sp:
        errors.append("CRITICAL: Phase 6: settings.py missing get_channel_settings()")
    if 'def set_channel_settings' not in sp:
        errors.append("CRITICAL: Phase 6: settings.py missing set_channel_settings()")
    
    # display_channel.py checks
    dc_path = SRC / 'display_channel.py'
    with open(dc_path, encoding='utf-8') as f:
        dc = f.read()
    
    if 'def apply_settings' not in dc:
        errors.append("CRITICAL: Phase 6: DisplayChannel missing apply_settings()")
    
    # display_channel.py — theme method guard
    if 'set_theme' not in dc and 'apply_theme' in dc:
        errors.append("CRITICAL: Phase 6: display_channel.py uses apply_theme() — must be set_theme()")

    # channel_manager.py checks
    cm_path = SRC / 'channel_manager.py'
    with open(cm_path, encoding='utf-8') as f:
        cm = f.read()

    if '_apply_persisted_settings' not in cm:
        errors.append("CRITICAL: Phase 6: ChannelManager missing _apply_persisted_settings()")
    if 'def add_channel' not in cm:
        errors.append("CRITICAL: Phase 6: ChannelManager add_channel() missing")
    if 'SettingsManager' not in cm:
        errors.append("CRITICAL: Phase 6: channel_manager.py imports wrong class (must be SettingsManager)")

    # settings_panel.py checks (guard gap fixed)
    spp_path = SRC / 'settings_panel.py'
    with open(spp_path, encoding='utf-8') as f:
        spp = f.read()

    if '_create_channel_section' not in spp:
        errors.append("CRITICAL: Phase 6: settings_panel.py missing _create_channel_section()")
    if '_get_saved_mode' not in spp:
        errors.append("CRITICAL: Phase 6: settings_panel.py missing _get_saved_mode()")
    if '_populate_themes' not in spp:
        errors.append("CRITICAL: Phase 6: settings_panel.py missing _populate_themes()")

    # main.py checks
    main_path = SRC / 'main.py'
    with open(main_path, encoding='utf-8') as f:
        main = f.read()

    if 'add_channel("alt"' not in main:
        errors.append("CRITICAL: Phase 6: main.py missing add_channel('alt') call")

    return errors
```

#### Step 7: Add Phase 6 source checks

**File:** `verify_critical_fixes.py`

```python
print("\n=== v1.1.0 Phase 6: Per-Channel Settings Source Checks ===")

_sm6 = SRC / 'settings.py'
_cm6 = SRC / 'channel_manager.py'
_dc6 = SRC / 'display_channel.py'
_main6 = SRC / 'main.py'

if _sm6.exists():
    with open(_sm6, encoding='utf-8') as _f:
        _sm6c = _f.read()
    for _sym, _label in [
        ('class ChannelSettings', 'ChannelSettings dataclass'),
        ('def get_channel_settings', 'get_channel_settings() method'),
        ('def set_channel_settings', 'set_channel_settings() method'),
    ]:
        if _sym in _sm6c:
            print(f"  [OK] settings.py: {_label}")
        else:
            errors.append(f"  [FAIL] Phase 6: settings.py missing: {_label}")

if _dc6.exists():
    with open(_dc6, encoding='utf-8') as _f:
        _dc6c = _f.read()
    if 'def apply_settings' in _dc6c:
        print("  [OK] display_channel.py: apply_settings() method")
    else:
        errors.append("  [FAIL] Phase 6: display_channel.py missing apply_settings()")

if _cm6.exists():
    with open(_cm6, encoding='utf-8') as _f:
        _cm6c = _f.read()
    if '_apply_persisted_settings' in _cm6c:
        print("  [OK] channel_manager.py: _apply_persisted_settings() helper")
    else:
        errors.append("  [FAIL] Phase 6: channel_manager.py missing _apply_persisted_settings()")

if _main6.exists():
    with open(_main6, encoding='utf-8') as _f:
        _main6c = _f.read()
    if 'add_channel("alt"' in _main6c:
        print("  [OK] main.py: Alt channel registered")
    else:
        errors.append("  [FAIL] Phase 6: main.py missing add_channel('alt')")
```

### Regression Guard Checklist

- [ ] Fresh install → Main defaults to fullscreen, Alt defaults to lower_third
- [ ] Change Alt mode to fullscreen → `settings.json` contains `"alt": {"mode": "fullscreen"}`
- [ ] Restart app → Alt channel initializes in fullscreen mode automatically
- [ ] Corrupt settings file (invalid mode) → Falls back to default mode gracefully
- [ ] Missing `channels` key in settings → Both channels use defaults
- [ ] Missing `alt` channel in settings → Alt uses defaults, Main uses saved
- [ ] Settings panel shows current modes correctly on open
- [ ] Mode change in settings panel updates display immediately
- [ ] Mode change persists after app restart
- [ ] `pre_commit_checks.py` and `verify_critical_fixes.py` pass

---

# Phase 7 — Release Hardening and Full Regression

## Objective

Stabilize v1.1.0 for production use. No new features — only verification, documentation, and hardening.

## Scope

Include:

- Run all automated checks (`compileall`, `pre_commit_checks.py`, `verify_critical_fixes.py`).
- Full manual test matrix covering every v1.1.0 feature.
- Update `REGRESSION_TESTING.md` with v1.1.0 section.
- Update `BUGFIX_LOG.md` with bugs fixed during v1.1.0 implementation.
- Update `ROADMAP.md` to reflect v1.1.0 status.

Exclude:

- New features or code changes (unless a bug is discovered during testing).
- Cross-platform testing (Windows-only for now, per roadmap).
- NDI/API/theme designer work (future versions).

## Architecture Decisions

1. **No code changes unless bugs found.** Phase 7 is purely verification and documentation.
2. **Manual test matrix is the gate.** All 20 items must pass before v1.1.0 is declared done.
3. **Documentation must match code.** If a test reveals a discrepancy, the code is the source of truth — update the doc.
4. **BUGFIX_LOG entries are retrospective.** Only bugs actually fixed during v1.1.0 work are logged, not pre-existing issues.

## Files Modified

| File | Change |
|------|--------|
| `REGRESSION_TESTING.md` | Add `## 8. v1.1.0 Advanced Display Modes` section |
| `BUGFIX_LOG.md` | Add v1.1.0 implementation bug fixes |
| `ROADMAP.md` | Update v1.1.0 status from 📋 Planned → ✅ Done; update changelog |

No source code changes are expected.

## Implementation Steps

### Step 1: Run automated checks

Run the three automated verification commands from the sub-roadmap:

```powershell
python -m compileall "VerseFlow\2. Source Code"
python pre_commit_checks.py
python verify_critical_fixes.py
```

All three must exit with code 0 before proceeding.

### Step 2: Update REGRESSION_TESTING.md

Append a new section at the end of the file:

```markdown
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
```

### Step 3: Update BUGFIX_LOG.md

Append a new section documenting bugs fixed during v1.1.0 implementation:

```markdown
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
```

### Step 4: Update ROADMAP.md

Four changes required:

1. **Line 5** — Update status line:
   ```
   > **Current Status:** v1.1.0 — Release Hardening (All phases implemented, final regression testing)
   ```

2. **Line 26** — Update v1.1.0 row in version table:
   ```
   | **v1.1.0** | 2 | Lower-Third Display + Dual Output Channels | 5 weeks | ✅ Done |
   ```

3. **Lines 448-454** — Update "Then (v1.1.0 Development)" section:
   ```markdown
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
   ```

4. **Changelog** — Add v1.1.0 entry at the end of the changelog table:
   ```
   | 2026-05-04 | v1.1.0 | **Advanced Display Modes** — ChannelManager + DisplayChannel adapter architecture; lower-third renderer with logo placeholder; dual output channels (Main/Alt); tabbed preview with status row; per-channel settings persistence and theme foundation; 4 bug fixes (navigator state sync, null safety, QApplication guard, hasattr/getattr) |
   ```

### Step 5: Execute manual test matrix

Run through every item in the manual test matrix (Step 2). Mark each item `[x]` in `REGRESSION_TESTING.md` as it passes. If any item fails:

1. Log the failure with error message and reproduction steps.
2. Fix the bug in source code.
3. Add the fix to `BUGFIX_LOG.md`.
4. Re-run the automated checks.
5. Re-test the failed item.

### Step 6: Final sign-off

When all automated checks pass AND all manual test items are marked `[x]`:

1. Verify `REGRESSION_TESTING.md` has a completed v1.1.0 section.
2. Verify `BUGFIX_LOG.md` has v1.1.0 entries.
3. Verify `ROADMAP.md` reflects v1.1.0 completion.
4. Declare v1.1.0 Definition of Done met.

## Phase 7 Definition of Done

- [ ] `python -m compileall "VerseFlow\2. Source Code"` exits 0
- [ ] `python pre_commit_checks.py` exits 0
- [ ] `python verify_critical_fixes.py` exits 0
- [ ] `REGRESSION_TESTING.md` has completed v1.1.0 section
- [ ] `BUGFIX_LOG.md` has v1.1.0 bug fix entries
- [ ] `ROADMAP.md` shows v1.1.0 as ✅ Done
- [ ] All 21 manual test items pass (8.1–8.6)
- [ ] No regressions in existing v1.0.0 functionality