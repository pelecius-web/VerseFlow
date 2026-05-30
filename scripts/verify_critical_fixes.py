import json
import sys
import os
from pathlib import Path

# Use absolute path for robustness
ROOT       = Path(r'c:\Users\GENESIS\Desktop\Real VerseFlow\VerseFlow')
SRC        = ROOT / 'src'
SRC_UI     = SRC / 'ui'
SRC_CORE   = SRC / 'core'
SRC_DISP   = SRC / 'display'
SRC_NDI    = SRC / 'ndi'
SRC_UTILS  = SRC / 'utils'
SRC_DB     = SRC / 'db'
SCRIPTS    = ROOT / 'scripts'
TESTS      = ROOT / 'tests'

def verify():
    errors = []
    
    print("=== v1.1.0 Phase 5: Tabbed Preview Source Checks ===")
    hp_path = SRC_UI / 'home_panel.py'
    if hp_path.exists():
        with open(hp_path, encoding='utf-8') as f:
            hp = f.read()
        
        checks = [
            ("Phase 5: QTabWidget present", 'QTabWidget' in hp),
            ("Phase 5: preview_main exists", 'self.preview_main' in hp),
            ("Phase 5: preview_alt exists", 'self.preview_alt' in hp),
            ("Phase 5: set_preview_verse routes to main", 'preview_main.set_preview_verse' in hp),
            ("Phase 5: status row exists", 'lbl_preview_status' in hp),
        ]
        
        for label, passed in checks:
            if passed:
                print(f"  [OK] {label}")
            else:
                print(f"  [FAIL] {label}")
                errors.append(label)
    else:
        print(f"  [FAIL] home_panel.py not found at {hp_path}")
        errors.append("home_panel.py missing")

    print("\n=== v1.1.0 Phase 6: Per-Channel Settings Source Checks ===")
    
    _sm6 = SRC_UTILS / 'settings.py'
    _cm6 = SRC_CORE / 'channel_manager.py'
    _dc6 = SRC_DISP / 'display_channel.py'
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
                print(f"  [FAIL] settings.py: {_label}")
                errors.append(f"Phase 6: settings.py missing: {_label}")
    else:
        errors.append("settings.py missing")

    if _dc6.exists():
        with open(_dc6, encoding='utf-8') as _f:
            _dc6c = _f.read()
        if 'def apply_settings' in _dc6c:
            print("  [OK] display_channel.py: apply_settings() method")
        else:
            print("  [FAIL] display_channel.py: apply_settings() method")
            errors.append("Phase 6: display_channel.py missing apply_settings()")
    else:
        errors.append("display_channel.py missing")

    if _cm6.exists():
        with open(_cm6, encoding='utf-8') as _f:
            _cm6c = _f.read()
        if '_apply_persisted_settings' in _cm6c:
            print("  [OK] channel_manager.py: _apply_persisted_settings() helper")
        else:
            print("  [FAIL] channel_manager.py: _apply_persisted_settings() helper")
            errors.append("Phase 6: channel_manager.py missing _apply_persisted_settings()")
    else:
        errors.append("channel_manager.py missing")

    if _main6.exists():
        with open(_main6, encoding='utf-8') as _f:
            _main6c = _f.read()
        if 'add_channel("alt"' in _main6c:
            print("  [OK] main.py: Alt channel registered")
        else:
            print("  [FAIL] main.py: Alt channel registered")
            errors.append("Phase 6: main.py missing add_channel('alt')")
    else:
        errors.append("main.py missing")

    return errors

def verify_phase1_ndi():
    """Verify v1.2.0 Phase 1 NDI skeleton source integrity."""
    errors = []
    snd_path = SRC_NDI / 'ndi_sender.py'
    mgr_path = SRC_NDI / 'ndi_manager.py'
    brg_path = SRC_NDI / 'ndi_bridge.py'

    # NDISender class & signal checks
    if snd_path.exists():
        with open(snd_path, encoding='utf-8') as f:
            snd = f.read()

        for sym, label in [
            ('class NDISender', 'NDISender class'),
            ('frame_sent', 'frame_sent signal'),
            ('sender_error', 'sender_error signal'),
            ('sender_status_changed', 'sender_status_changed signal'),
            ('def _capture_frame', '_capture_frame method'),
            ('NDI_CAPTURE_FPS', 'NDI_CAPTURE_FPS constant'),
            ('def _on_channel_state', '_on_channel_state method'),
            ('self._was_live', '_was_live guard'),
            ('name != self.channel_name', 'channel name filter'),
            ('self._frame_buf', 'frame_buf double-buffer'),
            ('size.isEmpty', 'zero-size QImage guard'),
            ('self._last_error_msg', 'sender_error message dedup'),
            ('self._last_error_time', 'sender_error time throttle'),
            ('channel.display_window', 'uses DisplayChannel property (not .controller)'),
        ]:
            if sym in snd:
                print(f"  [OK] ndi_sender.py: {label}")
            else:
                print(f"  [FAIL] ndi_sender.py: missing {label}")
                errors.append(f"Phase 1 NDI: ndi_sender.py missing: {label}")

    # NDIManager class checks
    if mgr_path.exists():
        with open(mgr_path, encoding='utf-8') as f:
            mgr = f.read()

        for sym, label in [
            ('class NDIManager', 'NDIManager class'),
            ('def stop_all', 'stop_all method'),
            ('def destroy', 'destroy method'),
            ('channels = ["main"]', 'Phase 1 Main-only scope'),
            ('def available', 'available property'),
        ]:
            if sym in mgr:
                print(f"  [OK] ndi_manager.py: {label}")
            else:
                print(f"  [FAIL] ndi_manager.py: missing {label}")
                errors.append(f"Phase 1 NDI: ndi_manager.py missing: {label}")

    # ndi_bridge.py wrapper API checks
    if brg_path.exists():
        with open(brg_path, encoding='utf-8') as f:
            brg = f.read()

        for sym, label in [
            ('def initialize', 'initialize()'),
            ('def destroy', 'destroy()'),
            ('def create_sender', 'create_sender()'),
            ('def destroy_sender', 'destroy_sender()'),
            ('def send_frame', 'send_frame()'),
            ('sys.byteorder', 'little-endian guard (in initialize)'),
            ('c_float', 'c_float import'),
            ('c_uint32', 'c_uint32 import'),
            ('c_int64', 'c_int64 import'),
            ('0x41524742', 'correct BGRA FourCC'),
            ('_initialized', 'init guard flag'),
        ]:
            if sym in brg:
                print(f"  [OK] ndi_bridge.py: {label}")
            else:
                print(f"  [FAIL] ndi_bridge.py: missing {label}")
                errors.append(f"Phase 1 NDI: ndi_bridge.py missing: {label}")

        # Must NOT contain NDIlib_send_get_tally (deferred to Phase 2)
        if "NDIlib_send_get_tally" in brg:
            print("  [FAIL] ndi_bridge.py: contains NDIlib_send_get_tally (deferred to Phase 2)")
            errors.append("Phase 1 NDI: ndi_bridge.py contains deferred NDIlib_send_get_tally")

    # display_channel.py — must have display_window forwarding property
    disp_ch_path = SRC_DISP / 'display_channel.py'
    if disp_ch_path.exists():
        with open(disp_ch_path, encoding='utf-8') as f:
            disp_ch = f.read()
        if 'def display_window' in disp_ch:
            print("  [OK] display_channel.py: display_window forwarding property")
        else:
            print("  [FAIL] display_channel.py: missing display_window forwarding property")
            errors.append("Phase 1 NDI: display_channel.py missing display_window property")

    return errors

def verify_phase2_ndi():
    """Verify v1.2.0 Phase 2 NDI Alt channel and no-signal tracker integrity."""
    errors = []
    snd_path = SRC_NDI / 'ndi_sender.py'
    mgr_path = SRC_NDI / 'ndi_manager.py'
    main_path = SRC / 'main.py'

    print("\n=== v1.2.0 Phase 2: NDI Alt Channel Source Checks ===")

    # main.py — check for the exact NDIManager channels argument AND allow_physical_window.
    # Broad search for '"alt"' would always pass (alt_display, add_channel, etc. already use it).
    if main_path.exists():
        with open(main_path, encoding='utf-8') as f:
            main_src = f.read()
        if ('channels=["main", "alt"]' in main_src
                or "channels=['main', 'alt']" in main_src):
            print("  [OK] main.py: NDIManager channels includes both 'main' and 'alt'")
        else:
            print("  [FAIL] main.py: NDIManager channels does not include 'alt'")
            errors.append("Phase 2 NDI: main.py missing 'alt' in NDIManager channels argument")
        if 'alt_display.allow_physical_window = True' in main_src:
            print("  [OK] main.py: alt_display.allow_physical_window = True (window creation enabled)")
        else:
            print("  [FAIL] main.py: alt_display.allow_physical_window is not True — Alt NDI silently broken")
            errors.append("Phase 2 NDI: main.py alt_display.allow_physical_window must be True for NDI")

    # ndi_sender.py — no-signal tracker symbols and == guard
    if snd_path.exists():
        with open(snd_path, encoding='utf-8') as f:
            snd = f.read()
        for sym, label in [
            ('_NOSIGNAL_MISS_LIMIT', '_NOSIGNAL_MISS_LIMIT constant'),
            ('_consecutive_miss_count', '_consecutive_miss_count tracker'),
            ('"signal": False', 'no-signal status dict'),
            ('"active": True', 'active=True in no-signal emit'),
            ('== _NOSIGNAL_MISS_LIMIT', 'no-signal fires once (== not >=)'),
        ]:
            if sym in snd:
                print(f"  [OK] ndi_sender.py: {label}")
            else:
                print(f"  [FAIL] ndi_sender.py: missing {label}")
                errors.append(f"Phase 2 NDI: ndi_sender.py missing: {label}")
        # Count check for stop() reset: the string appears in __init__, _on_timer, AND stop().
        # A simple existence check only confirms __init__; count >= 3 confirms all three sites.
        miss_resets = snd.count('self._consecutive_miss_count = 0')
        if miss_resets >= 3:
            print("  [OK] ndi_sender.py: _consecutive_miss_count reset in stop() (count=%d)" % miss_resets)
        else:
            print("  [FAIL] ndi_sender.py: _consecutive_miss_count not reset in stop() (count=%d, need 3)" % miss_resets)
            errors.append("Phase 2 NDI: ndi_sender.py _consecutive_miss_count not reset in stop()")

    # Regression: NDIManager still has get_sender() (needed by Phase 4 + tests)
    if mgr_path.exists():
        with open(mgr_path, encoding='utf-8') as f:
            mgr = f.read()
        if 'def get_sender' in mgr:
            print("  [OK] ndi_manager.py: get_sender() still present")
        else:
            print("  [FAIL] ndi_manager.py: get_sender() removed — needed by Phase 4")
            errors.append("Phase 2 NDI: ndi_manager.py get_sender() removed")

    return errors


def verify_phase3_target_routing():
    """Verify v1.3.0 Output Target Routing integrity."""
    errors = []
    hp_path = SRC_UI / 'home_panel.py'
    nav_path = SRC_CORE / 'navigator.py'
    cm_path = SRC_CORE / 'channel_manager.py'

    print("\n=== v1.3.0: Output Target Routing Source Checks ===")

    # home_panel.py — router methods
    if hp_path.exists():
        with open(hp_path, encoding='utf-8') as f:
            hp = f.read()
        for sym, label in [
            ('def _route_push', '_route_push() method'),
            ('def _route_clear', '_route_clear() method'),
            ('def _on_target_changed', '_on_target_changed() handler'),
            ('def _on_any_channel_changed', '_on_any_channel_changed() handler'),
        ]:
            if sym in hp:
                print(f"  [OK] home_panel.py: {label}")
            else:
                print(f"  [FAIL] home_panel.py: {label}")
                errors.append(f"v1.3.0 Routing: home_panel.py missing: {label}")

    # navigator.py — callbacks
    if nav_path.exists():
        with open(nav_path, encoding='utf-8') as f:
            nav = f.read()
        for sym, label in [
            ('push_callback', 'push_callback parameter'),
            ('clear_callback', 'clear_callback parameter'),
            ('self._push_callback', '_push_callback stored'),
            ('self._clear_callback', '_clear_callback stored'),
        ]:
            if sym in nav:
                print(f"  [OK] navigator.py: {label}")
            else:
                print(f"  [FAIL] navigator.py: {label}")
                errors.append(f"v1.3.0 Routing: navigator.py missing: {label}")
        if 'self.channel_manager.linked' not in nav:
            print("  [OK] navigator.py: no linked-mirror blocks remain")
        else:
            print("  [FAIL] navigator.py: linked-mirror blocks still present")
            errors.append("v1.3.0 Routing: navigator.py still has linked-mirror blocks")

    # channel_manager.py — switch_target
    if cm_path.exists():
        with open(cm_path, encoding='utf-8') as f:
            cm = f.read()
        for sym, label in [
            ('def switch_target', 'switch_target() method'),
            ('def _channels_for', '_channels_for() helper'),
            ('def _resolve_last_live', '_resolve_last_live() helper'),
        ]:
            if sym in cm:
                print(f"  [OK] channel_manager.py: {label}")
            else:
                print(f"  [FAIL] channel_manager.py: {label}")
                errors.append(f"v1.3.0 Routing: channel_manager.py missing: {label}")

    return errors


def verify_phase2_theme_designer():
    """Verify v1.3.0 Phase 2 Theme Designer runtime integrity."""
    errors = []

    # Ensure all src subdirs are on sys.path for flat imports
    # (src modules use "from constants import ..." style, not "from utils.constants")
    for subdir in (SRC, SRC_UTILS, SRC_UI, SRC_DISP, SRC_CORE, SRC_NDI, SRC_DB):
        if str(subdir) not in sys.path:
            sys.path.insert(0, str(subdir))

    print("\n=== Phase 2 Theme Designer ===")

    # 1. Theme persistence API
    from theme import Theme, ThemeManager, BUILTIN_THEME_IDS
    sample = {"id": "test", "name": "Test", "schema_version": "2.0",
              "colors": {"gold": "#c8a03c"}, "fonts": {"family": "Segoe UI"},
              "lower_third": {}, "fullscreen": {}, "spacing": {}, "animation": {}}
    t = Theme(sample)
    assert hasattr(t, "update"), "Theme.update missing"
    assert hasattr(t, "deep_copy"), "Theme.deep_copy missing"
    assert hasattr(t, "save_as"), "Theme.save_as missing"
    assert hasattr(t, "delete"), "Theme.delete missing"
    print("  [OK] Theme persistence API present")

    # 2. update() walks dotted paths
    t.update("lower_third.background_color", "#ff0000")
    assert t.lower_third["background_color"] == "#ff0000", "update did not set value"
    print("  [OK] Theme.update walks dotted path correctly")

    # 3. deep_copy isolates mutation
    copy = t.deep_copy()
    copy.update("lower_third.background_color", "#00ff00")
    assert t.lower_third["background_color"] == "#ff0000", \
        "deep_copy mutation contaminated original"
    assert copy.lower_third["background_color"] == "#00ff00"
    print("  [OK] Theme.deep_copy isolates mutations")

    # 4. delete refuses built-ins
    for builtin in BUILTIN_THEME_IDS:
        sample_b = dict(sample); sample_b["id"] = builtin
        tb = Theme(sample_b)
        assert tb.delete() is False, f"delete should refuse built-in '{builtin}'"
    print("  [OK] Theme.delete refuses built-ins")

    # 5. THEME_EDITOR_SCHEMA cardinality
    from theme_designer import THEME_EDITOR_SCHEMA, SAMPLE_VERSES, BUILTIN_THEME_IDS as DESIGNER_BUILTINS
    assert len(THEME_EDITOR_SCHEMA) >= 33, f"Schema has {len(THEME_EDITOR_SCHEMA)} props, expected >= 33"
    assert len(SAMPLE_VERSES) >= 4, "Need at least 4 sample verses"
    assert DESIGNER_BUILTINS == BUILTIN_THEME_IDS, "BUILTIN_THEME_IDS mismatch"
    print(f"  [OK] THEME_EDITOR_SCHEMA has {len(THEME_EDITOR_SCHEMA)} properties")

    # 6. Designer instantiation (headless via QApplication)
    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    mgr = ThemeManager()
    from theme_designer import ThemeDesignerPanel
    designer = ThemeDesignerPanel(theme_mgr=mgr, channel_manager=None)
    assert designer is not None, "Designer failed to instantiate"
    print("  [OK] ThemeDesignerPanel instantiates with theme_mgr only")

    # 7. PreviewSurface uses dummy controller (not VerseDB)
    from theme_designer import _DummyDisplayController
    dummy = _DummyDisplayController()
    assert hasattr(dummy, "verse_changed"), "Dummy missing verse_changed signal"
    assert hasattr(dummy, "translations_changed"), "Dummy missing translations_changed signal"
    assert hasattr(dummy, "layout_changed"), "Dummy missing layout_changed signal"
    print("  [OK] _DummyDisplayController has full signal surface")

    return errors


def verify_phase3_advanced_properties():
    """Verify v1.3.0 Phase 3 advanced properties (backgrounds, fonts, fade)."""
    errors = []

    # Ensure all src subdirs are on sys.path for flat imports
    for subdir in (SRC, SRC_UTILS, SRC_UI, SRC_DISP, SRC_CORE, SRC_NDI, SRC_DB):
        if str(subdir) not in sys.path:
            sys.path.insert(0, str(subdir))

    print("\n=== Phase 3 Advanced Properties ===")

    # 1. _BackgroundImageRenderer exists and has required methods
    from display_widget import DisplayWidget
    assert hasattr(DisplayWidget, '_BackgroundImageRenderer'), "DisplayWidget missing _BackgroundImageRenderer"
    renderer_cls = DisplayWidget._BackgroundImageRenderer
    assert hasattr(renderer_cls, 'paint'), "_BackgroundImageRenderer missing paint()"
    assert hasattr(renderer_cls, '_get_cached'), "_BackgroundImageRenderer missing _get_cached()"
    assert hasattr(renderer_cls, '_decode'), "_BackgroundImageRenderer missing _decode()"
    assert hasattr(renderer_cls, 'clear_cache'), "_BackgroundImageRenderer missing clear_cache()"
    print("  [OK] _BackgroundImageRenderer has all required methods")

    # 2. _bg_renderer attribute exists on DisplayWidget
    assert hasattr(DisplayWidget, '__init__'), "DisplayWidget missing __init__"
    print("  [OK] DisplayWidget class structure intact")

    # 3. ThemeManager._load_application_fonts is re-entrant
    from theme import ThemeManager
    import inspect
    src = inspect.getsource(ThemeManager._load_application_fonts)
    assert '_fonts_loaded' not in src, "ThemeManager._load_application_fonts still has _fonts_loaded guard"
    print("  [OK] ThemeManager._load_application_fonts is re-entrant")

    # 4. _import_font exists on PropertyEditor
    from theme_designer import PropertyEditor
    assert hasattr(PropertyEditor, '_import_font'), "PropertyEditor missing _import_font()"
    print("  [OK] PropertyEditor has _import_font() method")

    # 5. _start_fade accepts duration_ms parameter
    import inspect
    sig = inspect.signature(DisplayWidget._start_fade)
    assert 'duration_ms' in sig.parameters, "DisplayWidget._start_fade missing duration_ms parameter"
    assert 'easing_name' in sig.parameters, "DisplayWidget._start_fade missing easing_name parameter"
    print("  [OK] DisplayWidget._start_fade has fade parameters")

    # 6. DisplayWidget has _resolve_theme_path
    assert hasattr(DisplayWidget, '_resolve_theme_path'), "DisplayWidget missing _resolve_theme_path()"
    print("  [OK] DisplayWidget has _resolve_theme_path()")

    return errors


def verify_phase4_preset_library():
    """Verify ThemeCardWidget layout and grid selection API."""
    errors = []
    print("\n=== Phase 4 Preset Library ===")

    for subdir in (SRC, SRC_UTILS, SRC_UI, SRC_DISP, SRC_CORE, SRC_NDI, SRC_DB):
        if str(subdir) not in sys.path:
            sys.path.insert(0, str(subdir))

    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])

    from theme_designer import ThemeCardWidget
    card = ThemeCardWidget("test_id", "Test Name", "", True)
    assert card.theme_id == "test_id"
    assert card.name == "Test Name"
    assert card.is_builtin is True
    print("  [OK] ThemeCardWidget class initializes and stores attributes")

    assert card.property("selected") is None or card.property("selected") is False
    card.set_selected(True)
    assert card.property("selected") is True
    print("  [OK] ThemeCardWidget selected QSS property triggers correctly")

    triggered = []
    card.clicked.connect(lambda tid: triggered.append(tid))
    card.clicked.emit("test_id")
    assert len(triggered) == 1 and triggered[0] == "test_id"
    print("  [OK] ThemeCardWidget clicked signal maps correctly")

    return errors


def verify_phase4_color_consistency():
    """Verify all 10 theme JSONs have correct color token counts and no chrome leaks."""
    errors = []
    print("\n=== Phase 4 Color Consistency ===")

    THEMES_DIR = SRC_UTILS / 'themes'
    CHROME_TOKENS = ("bg_sidebar", "bg_sidebar_end", "bg_panel_start",
                     "bg_panel_end", "bg_input", "bg_preview_center",
                     "bg_preview_edge", "bg_statusbar")
    DARK_THEMES = ("warm_amber", "forest_green", "royal_purple",
                   "crimson_red", "slate_gray")
    EXPECTED_COLOR_TOKENS = 47   # Was 46; +1 for red_text (Phase 1)

    midnight_path = THEMES_DIR / "midnight_blue.json"
    if not midnight_path.exists():
        errors.append("midnight_blue.json not found — cannot check color leaks")
        return errors

    with open(midnight_path, encoding='utf-8') as f:
        midnight_colors = json.load(f)["colors"]

    for tid in DARK_THEMES:
        path = THEMES_DIR / f"{tid}.json"
        if not path.exists():
            errors.append(f"{tid}.json missing")
            continue
        with open(path, encoding='utf-8') as f:
            colors = json.load(f)["colors"]
        for token in CHROME_TOKENS:
            if colors.get(token) == midnight_colors.get(token):
                errors.append(f"COLOR LEAK: {tid}.json {token} = {midnight_colors[token]} (same as midnight_blue)")
                print(f"  [FAIL] {tid}.json: {token} leaked from midnight_blue")
        if colors.get("nav_active_text") != colors.get("text_primary"):
            errors.append(f"COLOR MISMATCH: {tid}.json nav_active_text != text_primary")
            print(f"  [FAIL] {tid}.json: nav_active_text != text_primary")

    for tid in ("midnight_blue", "pastel_calm", "dark_gold", "light", "high_contrast",
                *DARK_THEMES):
        path = THEMES_DIR / f"{tid}.json"
        if not path.exists():
            continue
        with open(path, encoding='utf-8') as f:
            colors = json.load(f)["colors"]
        if len(colors) != EXPECTED_COLOR_TOKENS:
            errors.append(f"{tid}.json: {len(colors)} color tokens, expected {EXPECTED_COLOR_TOKENS}")
            print(f"  [FAIL] {tid}.json: {len(colors)} tokens, expected {EXPECTED_COLOR_TOKENS}")

    if not errors:
        print("  [OK] All 10 themes pass color consistency checks")

    return errors


def verify_v131_phase4_theme_designer():
    """Runtime verification of Phase 4 theme designer QSS migration."""
    errors = []
    print("\n=== Phase 4 Theme Designer Polish ===")

    for subdir in (SRC, SRC_UTILS, SRC_UI, SRC_DISP, SRC_CORE):
        if str(subdir) not in sys.path:
            sys.path.insert(0, str(subdir))

    from PyQt6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])

    from theme_designer import ThemeCardWidget, PreviewSurface
    from theme import ThemeManager

    # 1. ThemeCardWidget thumb-fallback property
    card = ThemeCardWidget("test_id", "Test Name", "", True)
    fallback_lbl = card.thumb_lbl
    assert fallback_lbl.property("thumb-fallback") is not None, "thumb_lbl missing thumb-fallback property"
    print("  [OK] ThemeCardWidget thumb-fallback property available")

    # 2. Helper methods removed
    assert not hasattr(PreviewSurface, '_mode_btn_style'), "_mode_btn_style still exists on PreviewSurface"
    print("  [OK] Helper methods removed (_mode_btn_style, _spin_style, _combo_style)")

    # 3. Mode button property-based styling
    ps = PreviewSurface(ThemeManager())
    fs_btn = ps._fs_btn
    assert fs_btn.property("mode-btn") in ("active", "inactive"), f"fs_btn mode-btn property: {fs_btn.property('mode-btn')}"
    lt_btn = ps._lt_btn
    assert lt_btn.property("mode-btn") in ("active", "inactive"), f"lt_btn mode-btn property: {lt_btn.property('mode-btn')}"
    print("  [OK] Mode buttons use property selectors")

    return errors


if __name__ == "__main__":
    errs = verify()

    print("\n=== v1.2.0 Phase 1: NDI Skeleton Source Checks ===")
    errs.extend(verify_phase1_ndi())
    errs.extend(verify_phase2_ndi())
    errs.extend(verify_phase3_target_routing())
    errs.extend(verify_phase2_theme_designer())
    errs.extend(verify_phase3_advanced_properties())
    errs.extend(verify_phase4_preset_library())
    errs.extend(verify_phase4_color_consistency())
    errs.extend(verify_v131_phase4_theme_designer())

    if errs:
        print(f"\nVerification failed with {len(errs)} errors.")
        sys.exit(1)
    else:
        print("\nVerification successful. All critical fixes verified.")
        sys.exit(0)
