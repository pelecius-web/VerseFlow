import sys
import os
import json
from pathlib import Path

# Use absolute path for robustness
ROOT = Path(r'c:\Users\GENESIS\Desktop\Real VerseFlow\VerseFlow')
SRC       = ROOT / 'src'
SRC_UI    = SRC / 'ui'
SRC_CORE  = SRC / 'core'
SRC_DISP  = SRC / 'display'
SRC_NDI   = SRC / 'ndi'
SRC_UTILS = SRC / 'utils'
SCRIPTS   = ROOT / 'scripts'
TESTS     = ROOT / 'tests'

# Allow import from theme.py for BUILTIN_THEME_IDS (avoid hardcoded duplicates)
if str(SRC_UTILS) not in sys.path:
    sys.path.insert(0, str(SRC_UTILS))
from theme import BUILTIN_THEME_IDS

def check_phase5_tabbed_preview():
    errors = []
    hp_path = SRC_UI / 'home_panel.py'
    if not hp_path.exists():
        errors.append(f"CRITICAL: home_panel.py not found at {hp_path}")
        return errors

    with open(hp_path, encoding='utf-8') as f:
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

def check_phase6_channel_settings():
    """Verify v1.1.0 Phase 6 per-channel settings persistence."""
    errors = []

    # settings.py checks
    sp_path = SRC_UTILS / 'settings.py'
    if not sp_path.exists():
        errors.append(f"CRITICAL: settings.py not found at {sp_path}")
    else:
        with open(sp_path, encoding='utf-8') as f:
            sp = f.read()
        
        if 'class ChannelSettings' not in sp:
            errors.append("CRITICAL: Phase 6: settings.py missing ChannelSettings dataclass")
        if 'def get_channel_settings' not in sp:
            errors.append("CRITICAL: Phase 6: settings.py missing get_channel_settings()")
        if 'def set_channel_settings' not in sp:
            errors.append("CRITICAL: Phase 6: settings.py missing set_channel_settings()")
    
    # display_channel.py checks
    dc_path = SRC_DISP / 'display_channel.py'
    if not dc_path.exists():
        errors.append(f"CRITICAL: display_channel.py not found at {dc_path}")
    else:
        with open(dc_path, encoding='utf-8') as f:
            dc = f.read()
        
        if 'def apply_settings' not in dc:
            errors.append("CRITICAL: Phase 6: DisplayChannel missing apply_settings()")
        
        # display_channel.py — theme method guard
        if 'set_theme' not in dc and 'apply_theme' in dc:
            errors.append("CRITICAL: Phase 6: display_channel.py uses apply_theme() — must be set_theme()")

    # channel_manager.py checks
    cm_path = SRC_CORE / 'channel_manager.py'
    if not cm_path.exists():
        errors.append(f"CRITICAL: channel_manager.py not found at {cm_path}")
    else:
        with open(cm_path, encoding='utf-8') as f:
            cm = f.read()

        if '_apply_persisted_settings' not in cm:
            errors.append("CRITICAL: Phase 6: ChannelManager missing _apply_persisted_settings()")
        if 'def add_channel' not in cm:
            errors.append("CRITICAL: Phase 6: ChannelManager add_channel() missing")
        if 'SettingsManager' not in cm:
            # Note: The requirement is that it uses SettingsManager (not just Settings)
            errors.append("CRITICAL: Phase 6: channel_manager.py imports wrong class (must be SettingsManager)")

    # settings_panel.py checks
    spp_path = SRC_UI / 'settings_panel.py'
    if not spp_path.exists():
        errors.append(f"CRITICAL: settings_panel.py not found at {spp_path}")
    else:
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
    if not main_path.exists():
        errors.append(f"CRITICAL: main.py not found at {main_path}")
    else:
        with open(main_path, encoding='utf-8') as f:
            main = f.read()

        if 'add_channel("alt"' not in main:
            errors.append("CRITICAL: Phase 6: main.py missing add_channel('alt') call")

    return errors

def check_phase1_ndi_skeleton():
    """Verify v1.2.0 Phase 1 NDI skeleton integrity."""
    errors = []

    # File existence
    for filename in ("ndi_bridge.py", "ndi_sender.py", "ndi_manager.py"):
        path = SRC_NDI / filename
        if not path.exists():
            errors.append(f"CRITICAL: Phase 1 NDI: {filename} missing")

    # ndi_sender.py checks
    sender_path = SRC_NDI / "ndi_sender.py"
    if sender_path.exists():
        with open(sender_path, encoding="utf-8") as f:
            sender_src = f.read()

        if "class NDISender" not in sender_src:
            errors.append("CRITICAL: Phase 1 NDI: NDISender class missing")
        if "frame_sent" not in sender_src:
            errors.append("CRITICAL: Phase 1 NDI: frame_sent signal missing")
        if "sender_error" not in sender_src:
            errors.append("CRITICAL: Phase 1 NDI: sender_error signal missing")
        if "sender_status_changed" not in sender_src:
            errors.append("CRITICAL: Phase 1 NDI: sender_status_changed signal missing")
        if "NDI_CAPTURE_FPS" not in sender_src:
            errors.append("CRITICAL: Phase 1 NDI: NDI_CAPTURE_FPS constant missing")
        if "_capture_frame" not in sender_src:
            errors.append("CRITICAL: Phase 1 NDI: _capture_frame method missing")
        if ".grabWindow(" in sender_src:
            errors.append("CRITICAL: Phase 1 NDI: ndi_sender.py calls grabWindow() — use QWidget.grab() instead")
        if ".grab(" not in sender_src:
            errors.append("CRITICAL: Phase 1 NDI: ndi_sender.py missing QWidget.grab() — required for GPU capture on Windows")
        # Must use channel.display_window, not channel.controller.display_window
        if ".controller.display_window" in sender_src or ".controller." in sender_src:
            errors.append("CRITICAL: Phase 1 NDI: ndi_sender.py accesses .controller — must use channel.display_window property")

    # ndi_bridge.py checks
    bridge_path = SRC_NDI / "ndi_bridge.py"
    if bridge_path.exists():
        with open(bridge_path, encoding="utf-8") as f:
            bridge_src = f.read()

        if "import ndi" in bridge_src or "import ndi_python" in bridge_src:
            errors.append("CRITICAL: Phase 1 NDI: ndi_bridge.py imports third-party NDI PyPI package")
        if ".grabWindow(" in bridge_src or ".grab(" in bridge_src:
            errors.append("CRITICAL: Phase 1 NDI: ndi_bridge.py calls grab/grabWindow — must only receive QImage from NDISender")
        if "def send_frame" not in bridge_src:
            errors.append("CRITICAL: Phase 1 NDI: ndi_bridge.py missing send_frame()")
        if "def create_sender" not in bridge_src:
            errors.append("CRITICAL: Phase 1 NDI: ndi_bridge.py missing create_sender()")
        if "def destroy_sender" not in bridge_src:
            errors.append("CRITICAL: Phase 1 NDI: ndi_bridge.py missing destroy_sender()")
        # FourCC must be the correct value, not the sequential placeholder '= 1'
        if "0x41524742" not in bridge_src:
            errors.append("CRITICAL: Phase 1 NDI: ndi_bridge.py missing correct BGRA FourCC (0x41524742)")
        # Endianness check must exist (in initialize(), not module-level assert)
        if "sys.byteorder" not in bridge_src:
            errors.append("CRITICAL: Phase 1 NDI: ndi_bridge.py missing endianness check")
        # Init guard must exist
        if "_initialized" not in bridge_src:
            errors.append("CRITICAL: Phase 1 NDI: ndi_bridge.py missing _initialized guard")

    # ndi_manager.py checks
    manager_path = SRC_NDI / "ndi_manager.py"
    if manager_path.exists():
        with open(manager_path, encoding="utf-8") as f:
            manager_src = f.read()

        if "class NDIManager" not in manager_src:
            errors.append("CRITICAL: Phase 1 NDI: NDIManager class missing")
        if "def stop_all" not in manager_src:
            errors.append("CRITICAL: Phase 1 NDI: NDIManager missing stop_all()")
        if "def destroy" not in manager_src:
            errors.append("CRITICAL: Phase 1 NDI: NDIManager missing destroy()")

    # Regression: verify files NOT touched are unchanged
    # channel_display_facade.py — must not have ndi/ndi_sender/ndi_bridge imports
    facade_path = SRC_DISP / "channel_display_facade.py"
    if facade_path.exists():
        with open(facade_path, encoding="utf-8") as f:
            facade_src = f.read()
        for banned in ("ndi_bridge", "ndi_sender", "NDIManager", "NDISender"):
            if banned in facade_src:
                errors.append(f"CRITICAL: Phase 1 NDI: channel_display_facade.py references '{banned}' — must not be modified")

    # channel_manager.py — compatibility shims must not reference NDI
    cm_path = SRC_CORE / "channel_manager.py"
    if cm_path.exists():
        with open(cm_path, encoding="utf-8") as f:
            cm_src = f.read()
        for banned in ("ndi_bridge", "ndi_sender", "NDISender"):
            if banned in cm_src:
                errors.append(f"CRITICAL: Phase 1 NDI: channel_manager.py references '{banned}' — must not be modified")

    # display_channel.py — must have the display_window forwarding property
    disp_ch_path = SRC_DISP / "display_channel.py"
    if disp_ch_path.exists():
        with open(disp_ch_path, encoding="utf-8") as f:
            disp_ch_src = f.read()
        if "def display_window" not in disp_ch_src:
            errors.append("CRITICAL: Phase 1 NDI: display_channel.py missing display_window forwarding property")

    # display_core.py — must not reference NDI
    dc_path = SRC_DISP / "display_core.py"
    if dc_path.exists():
        with open(dc_path, encoding="utf-8") as f:
            dc_src = f.read()
        for banned in ("ndi_bridge", "ndi_sender", "NDISender"):
            if banned in dc_src:
                errors.append(f"CRITICAL: Phase 1 NDI: display_core.py references '{banned}' — must not be modified")

    # home_panel.py — must not reference NDI (no operator UI changes in Phase 1)
    hp_path = SRC_UI / "home_panel.py"
    if hp_path.exists():
        with open(hp_path, encoding="utf-8") as f:
            hp_src = f.read()
        for banned in ("ndi_bridge", "ndi_sender", "NDISender", "NDIManager"):
            if banned in hp_src:
                errors.append(f"CRITICAL: Phase 1 NDI: home_panel.py references '{banned}' — must not be modified")

    return errors

def check_phase2_ndi_alt_channel():
    """Verify v1.2.0 Phase 2 NDI Alt channel registration and no-signal tracker."""
    errors = []

    # main.py — must pass both channels to NDIManager AND enable Alt window.
    # NOTE: '"alt"' already appears many times in main.py (add_channel, alt_display, etc.)
    # so a broad string search for '"alt"' would always pass. We check for the exact
    # NDIManager channels argument instead — the only form that guarantees Alt NDI is active.
    main_path = SRC / "main.py"
    if main_path.exists():
        with open(main_path, encoding="utf-8") as f:
            main_src = f.read()
        if ('channels=["main", "alt"]' not in main_src
                and "channels=['main', 'alt']" not in main_src):
            errors.append(
                "CRITICAL: Phase 2 NDI: main.py does not pass both channels to NDIManager")
        # allow_physical_window must be True for Alt — without it open_display_window()
        # exits at the gate (display_core.py:168) before the headless branch. No window
        # is ever created, NDISender.start() returns False, Alt NDI is silently broken.
        if 'alt_display.allow_physical_window = True' not in main_src:
            errors.append(
                "CRITICAL: Phase 2 NDI: alt_display.allow_physical_window is not True — "
                "Alt DisplayWindow will never be created; Alt NDI silently broken")

    # ndi_sender.py — no-signal miss tracker must exist and must fire exactly once
    sender_path = SRC_NDI / "ndi_sender.py"
    if sender_path.exists():
        with open(sender_path, encoding="utf-8") as f:
            sender_src = f.read()
        if "_NOSIGNAL_MISS_LIMIT" not in sender_src:
            errors.append("CRITICAL: Phase 2 NDI: ndi_sender.py missing _NOSIGNAL_MISS_LIMIT constant")
        if "_consecutive_miss_count" not in sender_src:
            errors.append("CRITICAL: Phase 2 NDI: ndi_sender.py missing _consecutive_miss_count tracker")
        if '{"active": True, "signal": False}' not in sender_src:
            errors.append('CRITICAL: Phase 2 NDI: ndi_sender.py missing no-signal status emit')
        # Guard that the no-signal fires exactly once per transition, not at 30fps.
        # >= would emit the status on every tick after the threshold; == fires once.
        if "== _NOSIGNAL_MISS_LIMIT" not in sender_src:
            errors.append("CRITICAL: Phase 2 NDI: ndi_sender.py no-signal check uses >= instead of == — will spam at 30fps")
        # Guard that stop() resets the miss counter.
        # The string appears in both __init__ (init) and _on_timer (reset-on-success), so
        # checking for count >= 3 confirms stop() also resets it. Checking for count >= 1
        # only confirms the attribute exists, not that stop() resets it.
        if sender_src.count('self._consecutive_miss_count = 0') < 3:
            errors.append(
                "CRITICAL: Phase 2 NDI: ndi_sender.py _consecutive_miss_count not reset in stop() — "
                "stale count may trigger false no-signal on next live session")

    # Regression: channel_display_facade.py and channel_manager.py still not touched
    facade_path = SRC_DISP / "channel_display_facade.py"
    if facade_path.exists():
        with open(facade_path, encoding="utf-8") as f:
            facade_src = f.read()
        for banned in ("ndi_bridge", "ndi_sender", "NDIManager", "NDISender"):
            if banned in facade_src:
                errors.append(
                    f"CRITICAL: Phase 2 NDI: channel_display_facade.py references '{banned}' — must not be modified")

    cm_path = SRC_CORE / "channel_manager.py"
    if cm_path.exists():
        with open(cm_path, encoding="utf-8") as f:
            cm_src = f.read()
        for banned in ("ndi_bridge", "ndi_sender", "NDISender"):
            if banned in cm_src:
                errors.append(
                    f"CRITICAL: Phase 2 NDI: channel_manager.py references '{banned}' — must not be modified")

    # display_core.py — must not reference NDI
    dc_path = SRC_DISP / "display_core.py"
    if dc_path.exists():
        with open(dc_path, encoding="utf-8") as f:
            dc_src = f.read()
        for banned in ("ndi_bridge", "ndi_sender", "NDISender"):
            if banned in dc_src:
                errors.append(
                    f"CRITICAL: Phase 2 NDI: display_core.py references '{banned}' — must not be modified")

    # home_panel.py — no low-level NDI references (NDIManager OK from Phase 4)
    hp_path = SRC_UI / "home_panel.py"
    if hp_path.exists():
        with open(hp_path, encoding="utf-8") as f:
            hp_src = f.read()
        for banned in ("ndi_bridge", "ndi_sender", "NDISender"):
            if banned in hp_src:
                errors.append(
                    f"CRITICAL: Phase 2 NDI: home_panel.py references '{banned}' — low-level NDI must not be in operator UI")

    return errors


def check_output_target_routing():
    """Verify v1.3.0 Output Target Routing integrity.

    Ensures no push/clear path bypasses the target router or uses
    the old linked-mirror pattern.
    """
    errors = []
    hp_path = SRC_UI / "home_panel.py"

    if hp_path.exists():
        with open(hp_path, encoding="utf-8") as f:
            hp = f.read()

        # _route_push and _route_clear must exist
        if "def _route_push" not in hp:
            errors.append("CRITICAL: v1.3.0 Routing: home_panel.py missing _route_push")
        if "def _route_clear" not in hp:
            errors.append("CRITICAL: v1.3.0 Routing: home_panel.py missing _route_clear")
        if "def _on_target_changed" not in hp:
            errors.append("CRITICAL: v1.3.0 Routing: home_panel.py missing _on_target_changed")
        if "def _on_any_channel_changed" not in hp:
            errors.append("CRITICAL: v1.3.0 Routing: home_panel.py missing _on_any_channel_changed")

        # No self.display.push_verse() calls (except overlay rebuild which is Main-only)
        # Simple heuristic: flag if direct push_verse appears outside known exempt paths
        if "self.display.push_verse" in hp:
            # Only _rebuild_display_overlays and _on_translation_changed are exempt
            import re as _re
            for match in _re.finditer(r'^\s+self\.display\.push_verse\(', hp, _re.MULTILINE):
                # Get surrounding context to check if it's in an exempt method
                pos = match.start()
                # Look backwards for the nearest method definition
                method_search = hp[:pos].rfind('\n    def ')
                if method_search >= 0:
                    method_line = hp[method_search:pos]
                    exempt = any(
                        e in method_line
                        for e in ("_rebuild_display_overlays", "_on_translation_changed")
                    )
                    if not exempt:
                        # Get line number
                        line_num = hp[:pos].count('\n') + 1
                        errors.append(
                            f"CRITICAL: v1.3.0 Routing: home_panel.py:{line_num} "
                            f"calls self.display.push_verse() outside exempt methods")

        # No self.channel_manager.linked references
        if "self.channel_manager.linked" in hp:
            errors.append(
                "CRITICAL: v1.3.0 Routing: home_panel.py references "
                "channel_manager.linked — must be removed (router handles fan-out)")

    # navigator.py must have callbacks
    nav_path = SRC_CORE / "navigator.py"
    if nav_path.exists():
        with open(nav_path, encoding="utf-8") as f:
            nav = f.read()
        if "push_callback" not in nav:
            errors.append("CRITICAL: v1.3.0 Routing: navigator.py missing push_callback")
        if "clear_callback" not in nav:
            errors.append("CRITICAL: v1.3.0 Routing: navigator.py missing clear_callback")
        # No linked mirror blocks
        if "self.channel_manager.linked" in nav:
            errors.append(
                "CRITICAL: v1.3.0 Routing: navigator.py references "
                "channel_manager.linked — linked blocks must be removed")

    return errors


def check_phase4_ndi_visibility():
    """Verify v1.2.0 Phase 4 NDI operator visibility."""
    errors = []

    # home_panel.py — NDI indicator in preview status row
    hp_path = SRC_UI / "home_panel.py"
    if hp_path.exists():
        with open(hp_path, encoding="utf-8") as f:
            hp = f.read()
        if "ndi_manager" not in hp:
            errors.append("CRITICAL: Phase 4 NDI: home_panel.py missing ndi_manager parameter")
        if "_ndi(ch_name)" not in hp:
            errors.append("CRITICAL: Phase 4 NDI: home_panel.py missing NDI indicator helper")

    # settings.py — NDI fields in ChannelSettings
    sp_path = SRC_UTILS / "settings.py"
    if sp_path.exists():
        with open(sp_path, encoding="utf-8") as f:
            sp = f.read()
        if "ndi_enabled" not in sp:
            errors.append("CRITICAL: Phase 4 NDI: settings.py missing ndi_enabled in ChannelSettings")
        if "ndi_source_name" not in sp:
            errors.append("CRITICAL: Phase 4 NDI: settings.py missing ndi_source_name in ChannelSettings")

    # settings_panel.py — NDI Output card
    spp_path = SRC_UI / "settings_panel.py"
    if spp_path.exists():
        with open(spp_path, encoding="utf-8") as f:
            spp = f.read()
        if "NDI Output" not in spp:
            errors.append("CRITICAL: Phase 4 NDI: settings_panel.py missing NDI Output card")
        if "_create_ndi_section" not in spp:
            errors.append("CRITICAL: Phase 4 NDI: settings_panel.py missing _create_ndi_section()")

    # ndi_sender.py — set_enabled and is_active
    sender_path = SRC_NDI / "ndi_sender.py"
    if sender_path.exists():
        with open(sender_path, encoding="utf-8") as f:
            sender = f.read()
        if "def is_active" not in sender:
            errors.append("CRITICAL: Phase 4 NDI: ndi_sender.py missing is_active()")
        if "def set_enabled" not in sender:
            errors.append("CRITICAL: Phase 4 NDI: ndi_sender.py missing set_enabled()")
        if "def set_source_name" not in sender:
            errors.append("CRITICAL: Phase 4 NDI: ndi_sender.py missing set_source_name()")

    # ndi_manager.py — set_channel_ndi_enabled and set_channel_source_name
    mgr_path = SRC_NDI / "ndi_manager.py"
    if mgr_path.exists():
        with open(mgr_path, encoding="utf-8") as f:
            mgr = f.read()
        if "def set_channel_ndi_enabled" not in mgr:
            errors.append("CRITICAL: Phase 4 NDI: ndi_manager.py missing set_channel_ndi_enabled()")
        if "def set_channel_source_name" not in mgr:
            errors.append("CRITICAL: Phase 4 NDI: ndi_manager.py missing set_channel_source_name()")

    # main.py — ndi_manager passed to HomePanel and SettingsPanel
    main_path = SRC / "main.py"
    if main_path.exists():
        with open(main_path, encoding="utf-8") as f:
            main = f.read()
        if "ndi_manager=self.ndi_manager" not in main:
            errors.append("CRITICAL: Phase 4 NDI: main.py missing ndi_manager wiring")

    return errors


def check_phase1_theme_engine():
    """Verify v1.3.0 Phase 1 Theme Engine v2 + DisplayWidget Extraction integrity."""
    errors = []

    # DisplayWidget must exist
    dw_path = SRC_DISP / 'display_widget.py'
    if not dw_path.exists():
        errors.append(f"CRITICAL: Phase 1: display_widget.py not found at {dw_path}")
    else:
        with open(dw_path, encoding='utf-8') as f:
            dw = f.read()
        if 'class DisplayWidget' not in dw:
            errors.append("CRITICAL: Phase 1: display_widget.py missing DisplayWidget class")
        if 'def set_theme' not in dw:
            errors.append("CRITICAL: Phase 1: DisplayWidget missing set_theme()")
        if 'def set_logo_path' not in dw:
            errors.append("CRITICAL: Phase 1: DisplayWidget missing set_logo_path()")
        if '_fit_cache.clear' not in dw:
            errors.append("CRITICAL: Phase 1: DisplayWidget.set_theme() missing _fit_cache.clear()")
        if 'self.update()' not in dw[dw.find('def set_theme'):dw.find('def set_theme')+200]:
            pass  # check inside set_theme body only — weak heuristic
        if 'def paintEvent' not in dw:
            errors.append("CRITICAL: Phase 1: DisplayWidget missing paintEvent()")
        if 'setAlphaF' not in dw:
            errors.append("CRITICAL: Phase 1: DisplayWidget.paintEvent() missing setAlphaF() — band renders at full opacity")
        if 'def _build_logo_widget' not in dw:
            errors.append("CRITICAL: Phase 1: DisplayWidget missing _build_logo_widget()")
        if 'QSvgWidget' not in dw:
            errors.append("CRITICAL: Phase 1: _build_logo_widget() missing SVG support")
        if 'isNull' not in dw:
            errors.append("CRITICAL: Phase 1: _build_logo_widget() missing null-pixmap guard")
        if 'def _update_lower_third_geometry' not in dw:
            errors.append("CRITICAL: Phase 1: DisplayWidget missing _update_lower_third_geometry()")

    # Theme schema v2
    th_path = SRC_UTILS / 'theme.py'
    if th_path.exists():
        with open(th_path, encoding='utf-8') as f:
            th = f.read()
        if 'KNOWN_SCHEMA_VERSIONS' not in th:
            errors.append("CRITICAL: Phase 1: theme.py missing KNOWN_SCHEMA_VERSIONS")
        if 'def set_app_theme' not in th:
            errors.append("CRITICAL: Phase 1: ThemeManager missing set_app_theme()")
        if 'def _load_application_fonts' not in th:
            errors.append("CRITICAL: Phase 1: ThemeManager missing _load_application_fonts()")
        if 'application_fonts' not in th:
            errors.append("CRITICAL: Phase 1: ThemeManager missing application_fonts tracker")

    # DisplayChannel must have set_theme
    dc_path = SRC_DISP / 'display_channel.py'
    if dc_path.exists():
        with open(dc_path, encoding='utf-8') as f:
            dc = f.read()
        if 'def set_theme' not in dc:
            errors.append("CRITICAL: Phase 1: DisplayChannel missing set_theme()")

    # DisplayWindow must be thin shell
    dw_win_path = SRC_DISP / 'display_window.py'
    if dw_win_path.exists():
        with open(dw_win_path, encoding='utf-8') as f:
            dw_win = f.read()
        if 'class DisplayWindow' not in dw_win:
            errors.append("CRITICAL: Phase 1: display_window.py missing DisplayWindow")
        # Must not contain rendering methods that should have moved (check def only,
        # not calls — DisplayWindow may call widget._update_lower_third_geometry())
        for moved_method in ('def _calc_single_font_size', 'def _calc_overlay_font_sizes',
                             'def _measure_wrapped_text_height', 'def _render_fullscreen',
                             'def _render_lower_third', 'def _build_lower_third_page',
                             'def _fit_lower_third_fonts', 'def _fit_church_name_font',
                             'def _lower_third_available_area', 'def _update_lower_third_geometry',
                             'def paintEvent', 'def _apply_theme_styling',
                             'def _apply_default_styling'):
            if moved_method in dw_win:
                errors.append(f"CRITICAL: Phase 1: {moved_method} still in display_window.py — should be in DisplayWidget")

    return errors


def check_phase2_theme_designer():
    """Verify v1.3.0 Phase 2 Theme Designer UI integrity."""
    errors = []

    # 1. theme_designer.py exists
    designer_path = SRC_UI / "theme_designer.py"
    if not designer_path.exists():
        errors.append("CRITICAL: Phase 2: theme_designer.py missing")
        return errors
    src = designer_path.read_text(encoding="utf-8")

    # 2. Required classes present
    for cls in ("class ThemeDesignerPanel", "class ThemesListPanel",
                "class PreviewSurface", "class PropertyEditor"):
        if cls not in src:
            errors.append(f"CRITICAL: Phase 2: {cls} missing in theme_designer.py")

    # 3. Required module-level symbols
    for sym in ("THEME_EDITOR_SCHEMA", "SAMPLE_VERSES", "BUILTIN_THEME_IDS",
                "_DummyDisplayController"):
        if sym not in src:
            errors.append(f"CRITICAL: Phase 2: {sym} missing in theme_designer.py")

    # 4. Theme persistence API present in theme.py
    theme_src = (SRC_UTILS / "theme.py").read_text(encoding="utf-8")
    for method in ("def update", "def deep_copy", "def save", "def save_as",
                   "def delete", "def reload_theme", "def create_theme"):
        if method not in theme_src:
            errors.append(f"CRITICAL: Phase 2: theme.py missing {method}")
    if "BUILTIN_THEME_IDS" not in theme_src:
        errors.append("CRITICAL: Phase 2: theme.py missing BUILTIN_THEME_IDS")

    # 5. settings_panel.py wires the new signal
    sp_src = (SRC_UI / "settings_panel.py").read_text(encoding="utf-8")
    if "theme_designer_requested" not in sp_src:
        errors.append("CRITICAL: Phase 2: settings_panel.py missing theme_designer_requested signal")
    if "Open Theme Designer" not in sp_src:
        errors.append("CRITICAL: Phase 2: settings_panel.py missing Open Theme Designer button")

    # 6. main.py wires the designer
    main_src = (SRC / "main.py").read_text(encoding="utf-8")
    for sym in ("from theme_designer import", "ThemeDesignerPanel(",
                "self.stack.addWidget(self.theme_designer)",
                "Ctrl+Shift+T", "Ctrl+3"):
        if sym not in main_src:
            errors.append(f"CRITICAL: Phase 2: main.py missing {sym!r}")

    # 7. THEME_EDITOR_SCHEMA paths must resolve in dark_gold.json after upgrade
    import json, re
    dg_path = SRC_UTILS / "themes" / "dark_gold.json"
    dg = json.loads(dg_path.read_text(encoding="utf-8"))
    # Apply v2 upgrade in memory for path validation
    dg.setdefault("fullscreen", {})
    dg.setdefault("lower_third", {})
    for path_match in re.finditer(r'PropertySpec\("([^"]+)"', src):
        path = path_match.group(1)
        node = dg
        for part in path.split("."):
            if isinstance(node, dict) and part in node:
                node = node[part]
            else:
                # Acceptable: Phase 1 _upgrade_to_v2 fills these at runtime
                if not _is_v2_default_path(path):
                    errors.append(f"CRITICAL: Phase 2: schema path '{path}' not in dark_gold.json")
                break

    return errors


def _is_v2_default_path(path: str) -> bool:
    """Whitelist of paths Phase 1's _upgrade_to_v2 populates from defaults."""
    return path.startswith(("fullscreen.",)) \
           or path in (
               "lower_third.logo_format",
               "lower_third.background_image",
               "lower_third.background_image_fit",
               "lower_third.height_ratio",
               "lower_third.separator_width",
               "lower_third.ref_color",
               "lower_third.verse_color",
               "lower_third.ref_font_family",
               "lower_third.verse_font_family",
               "lower_third.ref_font_weight",
               "lower_third.verse_font_weight",
               "lower_third.church_name_color",
           )


def check_phase3_advanced_properties():
    """Verify v1.3.0 Phase 3 advanced properties (image backgrounds, font import, fade transitions)."""
    errors = []

    # display_widget.py — _BackgroundImageRenderer class
    dw_path = SRC_DISP / "display_widget.py"
    if not dw_path.exists():
        errors.append(f"CRITICAL: display_widget.py not found at {dw_path}")
        return errors

    with open(dw_path, encoding="utf-8") as f:
        dw = f.read()

    if "class _BackgroundImageRenderer" not in dw:
        errors.append("CRITICAL: Phase 3: display_widget.py missing _BackgroundImageRenderer class")
    if "_bg_renderer" not in dw:
        errors.append("CRITICAL: Phase 3: display_widget.py missing _bg_renderer attribute")
    if "clear_cache" not in dw:
        errors.append("CRITICAL: Phase 3: display_widget.py missing clear_cache() on _bg_renderer")
    if "QGraphicsOpacityEffect" not in dw:
        errors.append("CRITICAL: Phase 3: display_widget.py missing QGraphicsOpacityEffect for fade")
    if "QPropertyAnimation" not in dw:
        errors.append("CRITICAL: Phase 3: display_widget.py missing QPropertyAnimation for fade")
    if "_resolve_theme_path" not in dw:
        errors.append("CRITICAL: Phase 3: display_widget.py missing _resolve_theme_path()")

    # theme.py — _fonts_loaded guard removed
    th_path = SRC_UTILS / "theme.py"
    if th_path.exists():
        with open(th_path, encoding="utf-8") as f:
            th = f.read()
        if "_fonts_loaded" in th:
            errors.append("CRITICAL: Phase 3: theme.py still has _fonts_loaded boolean guard — must be removed")
        if "font_path in self._loaded_font_paths" not in th and "font_path not in self._loaded_font_paths" not in th:
            errors.append("CRITICAL: Phase 3: theme.py missing per-file _loaded_font_paths check")

    # theme_designer.py — Import font button
    td_path = SRC_UI / "theme_designer.py"
    if td_path.exists():
        with open(td_path, encoding="utf-8") as f:
            td = f.read()
        if "_import_font" not in td:
            errors.append("CRITICAL: Phase 3: theme_designer.py missing _import_font() method")
        if "Import" not in td:
            errors.append("CRITICAL: Phase 3: theme_designer.py missing Import button for font_family")

    return errors


def check_v131_typography_phase0():
    """Verify Phase 0 typography system foundation is intact."""
    errors = []

    # 1. All built-in themes have a typography section with 4 expected keys
    THEMES_DIR = SRC_UTILS / 'themes'
    EXPECTED_TYPO_KEYS = {"compact", "standard", "body", "hint"}

    for builtin_id in BUILTIN_THEME_IDS:
        path = THEMES_DIR / f"{builtin_id}.json"
        if not path.exists():
            errors.append(f"CRITICAL: Built-in theme {builtin_id}.json missing")
            continue
        with open(path, encoding='utf-8') as f:
            data = json.load(f)
        if "typography" not in data:
            errors.append(f"CRITICAL: {builtin_id}.json missing typography section")
            continue
        typo_keys = set(data["typography"].keys())
        missing = EXPECTED_TYPO_KEYS - typo_keys
        if missing:
            errors.append(f"CRITICAL: {builtin_id}.json typography missing keys: {missing}")

    # 2. theme.py typography infrastructure
    theme_path = SRC_UTILS / 'theme.py'
    with open(theme_path, encoding='utf-8') as f:
        theme_content = f.read()

    if 'TYPOGRAPHY_DEFAULTS' not in theme_content:
        errors.append("CRITICAL: theme.py missing TYPOGRAPHY_DEFAULTS constant")
    if 'TYPO_COLOR_TOKENS' not in theme_content:
        errors.append("CRITICAL: theme.py missing TYPO_COLOR_TOKENS color mapping (F2 fix)")
    if 'typography' not in theme_content:
        errors.append("CRITICAL: theme.py missing typography handling")
    if 'typography_qss' not in theme_content:
        errors.append("CRITICAL: theme.py generate_stylesheet missing typography loop injection")
    # section-header="true" alias removed in Phase 1 settings panel polish (Step 6)

    # 3. B1 blockers: deep_copy and _to_dict must include typography
    if 'copy.deepcopy(self.typography)' not in theme_content:
        errors.append("CRITICAL: Theme.deep_copy missing typography (B1 blocker)")
    if '"typography": self.typography' not in theme_content:
        errors.append("CRITICAL: Theme._to_dict missing typography (B1 blocker)")

    # 4. F9 fix: deprecated alias removed in Phase 1 (Step 6) — no longer needs .get() fallback

    return errors


def check_v131_phase1_settings_panel():
    """Verify Phase 1 settings panel polish closeout."""
    errors = []

    THEMES_DIR = SRC_UTILS / 'themes'
    EXPECTED_TOKEN_COUNT = 47

    # 1. All 10 built-in themes have red_text token
    for builtin_id in BUILTIN_THEME_IDS:
        path = THEMES_DIR / f"{builtin_id}.json"
        if not path.exists():
            errors.append(f"CRITICAL: Built-in theme {builtin_id}.json missing")
            continue
        with open(path, encoding='utf-8') as f:
            data = json.load(f)
        if "red_text" not in data.get("colors", {}):
            errors.append(f"CRITICAL: {builtin_id}.json missing red_text token")
        if len(data.get("colors", {})) != EXPECTED_TOKEN_COUNT:
            errors.append(f"CRITICAL: {builtin_id}.json has {len(data['colors'])} tokens, expected {EXPECTED_TOKEN_COUNT}")

    # 2. theme.py has error selector and no hover rules or deprecated alias
    theme_path = SRC_UTILS / 'theme.py'
    with open(theme_path, encoding='utf-8') as f:
        theme_content = f.read()
    if 'QLabel[error="true"]' not in theme_content:
        errors.append('CRITICAL: theme.py missing QLabel[error="true"] selector')
    if 'QFrame[card="true"]:hover' in theme_content:
        errors.append("CRITICAL: theme.py still has card hover rule (should be removed)")
    if 'QFrame[panel="true"]:hover' in theme_content:
        errors.append("CRITICAL: theme.py still has panel hover rule (should be removed)")
    if 'section-header="true"' in theme_content:
        errors.append("CRITICAL: theme.py still has deprecated section-header=true alias (should be removed)")

    # 3. settings_panel.py has zero inline setStyleSheet() calls
    sp_path = SRC_UI / 'settings_panel.py'
    with open(sp_path, encoding='utf-8') as f:
        sp_content = f.read()
    set_style_count = sp_content.count("setStyleSheet")
    if set_style_count > 0:
        errors.append(f"CRITICAL: settings_panel.py has {set_style_count} inline setStyleSheet() calls, expected 0")

    # 4. _make_section_header uses variant parameter
    if 'variant: str = "compact"' not in sp_content:
        errors.append("CRITICAL: _make_section_header missing variant parameter")
    call_sites = [line for line in sp_content.split('\n') if '_make_section_header(' in line]
    standard_sites = [l for l in call_sites if 'variant="standard"' in l]
    if len(standard_sites) < 5:
        errors.append(f"CRITICAL: Only {len(standard_sites)}/5 _make_section_header call sites use variant='standard'")

    return errors


def check_v131_phase2_icons():
    """Verify Phase 2 iconography system and settings panel icons."""
    errors = []

    # 1. All 5 icon factory functions exist in icons.py
    icons_path = SRC_UTILS / 'icons.py'
    with open(icons_path, encoding='utf-8') as f:
        icons_content = f.read()
    expected_functions = [
        'get_keyboard_icon',
        'get_settings_gear_icon',
        'get_layers_icon',
        'get_broadcast_icon',
        'get_palette_icon',
    ]
    for func in expected_functions:
        if f'def {func}(' not in icons_content:
            errors.append(f"CRITICAL: icons.py missing function '{func}'")

    # 2. All 5 functions accept color and size parameters
    for func in expected_functions:
        sig_pattern = f'def {func}(color: str'
        if sig_pattern not in icons_content:
            errors.append(f"CRITICAL: {func} missing color parameter")

    # 3. settings_panel.py imports all 5 icon functions
    sp_path = SRC_UI / 'settings_panel.py'
    with open(sp_path, encoding='utf-8') as f:
        sp_content = f.read()
    for func in expected_functions:
        if func not in sp_content:
            errors.append(f"CRITICAL: settings_panel.py does not reference '{func}'")

    # 4. _make_section_header accepts icon parameter
    if 'icon: QIcon = None' not in sp_content:
        errors.append("CRITICAL: _make_section_header missing 'icon: QIcon = None' parameter")

    # 5. All call sites pass icon= argument (multi-line safe: search content, not per-line)
    icon_count = sp_content.count("icon=get_")
    if icon_count < 4:
        errors.append(f"CRITICAL: Only {icon_count} occurrences of 'icon=get_' in settings_panel.py, expected at least 4")

    # 6. theme_designer.py imports get_palette_icon
    td_path = SRC_UI / 'theme_designer.py'
    with open(td_path, encoding='utf-8') as f:
        td_content = f.read()
    if 'get_palette_icon' not in td_content:
        errors.append("CRITICAL: theme_designer.py missing get_palette_icon import/usage")

    # 7. settings_panel.py has QIcon import from PyQt6.QtGui
    if 'from PyQt6.QtGui import' not in sp_content or 'QIcon' not in sp_content:
        errors.append("CRITICAL: settings_panel.py missing QIcon import")

    return errors


def check_v131_phase4_theme_designer():
    """Verify v1.3.1 Phase 4 Theme Designer QSS migration and helper removal."""
    errors = []

    td_path = SRC_UI / "theme_designer.py"
    if not td_path.exists():
        errors.append("CRITICAL: theme_designer.py not found")
        return errors
    td_content = td_path.read_text(encoding="utf-8")

    # 1. Helper methods removed
    if 'def _spin_style' in td_content:
        errors.append("CRITICAL: theme_designer.py still has _spin_style() method (should be removed)")
    if 'def _combo_style' in td_content:
        errors.append("CRITICAL: theme_designer.py still has _combo_style() method (should be removed)")
    if 'def _mode_btn_style' in td_content:
        errors.append("CRITICAL: theme_designer.py still has _mode_btn_style() method (should be removed)")

    # 2. Inline setStyleSheet count (remaining category (a) exceptions only)
    ss_count = td_content.count("setStyleSheet")
    if ss_count > 9:
        errors.append(f"CRITICAL: theme_designer.py has {ss_count} setStyleSheet() calls, expected \u2264 9")

    # 3. Key property selectors used for migrated widgets
    expected_properties = [
        "designer-panel",
        "designer-scroll",
        "designer-action-btn",
        "designer-spin",
        "designer-combo",
        "designer-checkbox",
        "designer-header",
        "designer-title",
        "designer-input",
        "designer-browse-btn",
        "thumb-fallback",
        "accent",
    ]
    for prop in expected_properties:
        if prop not in td_content:
            errors.append(f"CRITICAL: theme_designer.py missing property '{prop}'")

    # 3b. Mode buttons use value-encoded property (not boolean)
    if 'setProperty("mode-btn", "active")' not in td_content:
        errors.append("CRITICAL: theme_designer.py missing mode-btn active value-encoded property")
    if 'setProperty("mode-btn", "inactive")' not in td_content:
        errors.append("CRITICAL: theme_designer.py missing mode-btn inactive value-encoded property")

    # 4. Column headers and layout helpers
    if "_make_column_header" not in td_content:
        errors.append("CRITICAL: theme_designer.py missing _make_column_header helper")
    if 'setProperty("gold-dot", True)' not in td_content:
        errors.append("CRITICAL: theme_designer.py missing gold-dot property in _make_column_header")
    if 'setProperty("section-header", "standard")' not in td_content:
        errors.append("CRITICAL: theme_designer.py missing section-header standard variant")

    # 4b. Row labels use compact typography
    if 'setProperty("typography", "compact")' not in td_content:
        errors.append("CRITICAL: theme_designer.py row labels not migrated to compact variant")

    # 4c. Hint labels use hint typography
    if 'setProperty("typography", "hint")' not in td_content:
        errors.append("CRITICAL: theme_designer.py hint labels not migrated to hint variant")

    # 5. QSS selectors in theme.py
    theme_path = SRC_UTILS / "theme.py"
    if not theme_path.exists():
        errors.append("CRITICAL: theme.py not found")
        return errors
    theme_content = theme_path.read_text(encoding="utf-8")
    expected_selectors = [
        'designer-spin="true"',
        'designer-combo="true"',
        'mode-btn="active"',
        'mode-btn="inactive"',
        'designer-panel="true"',
        'designer-scroll="true"',
        'designer-action-btn="true"',
        'designer-header="true"',
        'designer-title="true"',
        'designer-checkbox="true"',
        'designer-input="true"',
        'designer-browse-btn="true"',
        'thumb-fallback="true"',
    ]
    for sel in expected_selectors:
        if sel not in theme_content:
            errors.append(f"CRITICAL: theme.py missing QSS selector for '{sel}'")

    return errors


def check_phase4_preset_library_polish():
    """Verify v1.3.0 Phase 4 preset library and thumbnail grid layout."""
    errors = []

    THEMES_DIR = SRC_UTILS / 'themes'
    for tid in BUILTIN_THEME_IDS:
        json_path = THEMES_DIR / f"{tid}.json"
        if not json_path.exists():
            errors.append(f"CRITICAL: Preset theme file missing: {json_path}")

    td_path = SRC_UI / "theme_designer.py"
    if td_path.exists():
        with open(td_path, encoding='utf-8') as f:
            td_src = f.read()
        if "class ThemeCardWidget" not in td_src:
            errors.append("CRITICAL: theme_designer.py missing ThemeCardWidget class")
        if "_generate_theme_thumbnail" not in td_src:
            errors.append("CRITICAL: theme_designer.py missing _generate_theme_thumbnail() method")
        if "QGridLayout" not in td_src:
            errors.append("CRITICAL: theme_designer.py missing grid layout for themes")

    # Color consistency check — dark themes must not leak midnight_blue chrome
    CHROME_TOKENS = ("bg_sidebar", "bg_sidebar_end", "bg_panel_start",
                     "bg_panel_end", "bg_input", "bg_preview_center",
                     "bg_preview_edge", "bg_statusbar")
    DARK_THEMES = ("warm_amber", "forest_green", "royal_purple",
                   "crimson_red", "slate_gray")
    EXPECTED_COLOR_TOKENS = 47   # Was 46; +1 for red_text (Phase 1)

    midnight_path = THEMES_DIR / "midnight_blue.json"
    if midnight_path.exists():
        with open(midnight_path, encoding='utf-8') as f:
            midnight_colors = json.load(f)["colors"]

        for tid in DARK_THEMES:
            path = THEMES_DIR / f"{tid}.json"
            if not path.exists():
                continue
            with open(path, encoding='utf-8') as f:
                colors = json.load(f)["colors"]
            for token in CHROME_TOKENS:
                if colors.get(token) == midnight_colors.get(token):
                    errors.append(
                        f"COLOR LEAK: {tid}.json {token} = {midnight_colors[token]} (same as midnight_blue)")
            if colors.get("nav_active_text") != colors.get("text_primary"):
                errors.append(
                    f"COLOR MISMATCH: {tid}.json nav_active_text ({colors.get('nav_active_text')}) "
                    f"!= text_primary ({colors.get('text_primary')})")

    # Token count validation
    for tid in BUILTIN_THEME_IDS:
        path = THEMES_DIR / f"{tid}.json"
        if not path.exists():
            continue
        with open(path, encoding='utf-8') as f:
            colors = json.load(f)["colors"]
        if len(colors) != EXPECTED_COLOR_TOKENS:
            errors.append(
                f"{tid}.json: {len(colors)} color tokens, expected {EXPECTED_COLOR_TOKENS}")

    return errors


def check_v131_phase3_home_panel():
    """Verify Phase 3 home panel QSS migration."""
    errors = []

    hp_path = SRC_UI / 'home_panel.py'
    with open(hp_path, encoding='utf-8') as f:
        hp_content = f.read()

    # 1. QIcon imported
    if 'QIcon' not in hp_content:
        errors.append("CRITICAL: home_panel.py missing QIcon import")

    # 2. _make_section_header method exists
    if '_make_section_header' not in hp_content:
        errors.append("CRITICAL: home_panel.py missing _make_section_header method")

    # 3. _make_separator method exists
    if '_make_separator' not in hp_content:
        errors.append("CRITICAL: home_panel.py missing _make_separator method")

    # 4. Inline setStyleSheet count <= 6 (3 logical exceptions: ref_label 3-state,
    #    main_verse_label dynamic padding, overlay label dynamic padding.
    #    Physical counting finds 6 calls because ref_label has 4 separate call sites.)
    ss_count = hp_content.count('.setStyleSheet(')
    if ss_count > 6:
        errors.append(f"CRITICAL: home_panel.py has {ss_count} setStyleSheet calls, expected <= 6")

    # 5. Key property selectors present
    # Properties used as setProperty key (first argument)
    key_properties = [
        'gold-dot', 'separator', 'section-header', 'hint',
        'mode-toggle', 'combo-mode', 'preview-tabs',
        'version-badge', 'gold-dot-green', 'preview-verse',
        'accent', 'result',
    ]
    for prop in key_properties:
        if f'setProperty("{prop}' not in hp_content:
            errors.append(f"CRITICAL: home_panel.py missing setProperty('{prop}') call")
    # Properties used as setProperty value (second argument, e.g. accent="output-target")
    value_properties = ['output-target', 'destructive']
    for prop in value_properties:
        if f'"{prop}"' not in hp_content:
            errors.append(f"CRITICAL: home_panel.py missing '{prop}' property value")

    # 6. theme.py has new selectors
    theme_path = SRC_UTILS / 'theme.py'
    with open(theme_path, encoding='utf-8') as f:
        theme_content = f.read()
    new_selectors = [
        'accent="nav-tab"',
        'accent="nav-tab-active"',
        'accent="destructive"',
        'accent="output-target"',
        'gold-dot-green',
        'version-badge',
        'preview-tabs',
        'combo-mode',
        'mode-toggle',
        'section-header="compact-green"',
        'preview-verse',
    ]
    for sel in new_selectors:
        if sel not in theme_content:
            errors.append(f"CRITICAL: theme.py missing selector '{sel}'")

    # 7. compact-green uses compact_spec (not hardcoded values)
    if 'compact_spec' not in theme_content:
        errors.append("CRITICAL: theme.py missing compact_spec variable for compact-green derivation")

    # 8. No QFrame[panel="true"]:hover in theme.py
    if 'QFrame[panel="true"]:hover' in theme_content:
        errors.append("CRITICAL: QFrame[panel=true]:hover still present in theme.py")

    return errors


if __name__ == "__main__":
    all_errors = []
    print("Running Phase 5 checks...")
    all_errors.extend(check_phase5_tabbed_preview())

    print("Running Phase 6 checks...")
    all_errors.extend(check_phase6_channel_settings())

    print("Running Phase 1 NDI skeleton checks...")
    all_errors.extend(check_phase1_ndi_skeleton())

    print("Running Phase 2 NDI Alt channel checks...")
    all_errors.extend(check_phase2_ndi_alt_channel())

    print("Running v1.3.0 Output Target Routing checks...")
    all_errors.extend(check_output_target_routing())

    print("Running Phase 4 NDI Operator Visibility checks...")
    all_errors.extend(check_phase4_ndi_visibility())

    print("Running Phase 1 Theme Engine checks...")
    all_errors.extend(check_phase1_theme_engine())

    print("Running Phase 2 Theme Designer checks...")
    all_errors.extend(check_phase2_theme_designer())

    print("Running Phase 3 Advanced Properties checks...")
    all_errors.extend(check_phase3_advanced_properties())

    print("Checking v1.3.1 Phase 0 typography system...")
    all_errors.extend(check_v131_typography_phase0())

    print("Checking v1.3.1 Phase 1 settings panel polish...")
    all_errors.extend(check_v131_phase1_settings_panel())

    print("Checking v1.3.1 Phase 2 iconography system...")
    all_errors.extend(check_v131_phase2_icons())

    print("Running Phase 4 Preset Library & Polish checks...")
    all_errors.extend(check_phase4_preset_library_polish())

    print("Checking v1.3.1 Phase 3 home panel QSS migration...")
    all_errors.extend(check_v131_phase3_home_panel())

    print("Checking v1.3.1 Phase 4 theme designer QSS migration...")
    all_errors.extend(check_v131_phase4_theme_designer())

    if all_errors:
        print("\n--- ERRORS FOUND ---")
        for err in all_errors:
            print(f"  {err}")
        sys.exit(1)
    else:
        print("\nSUCCESS: All pre-commit checks passed.")
        sys.exit(0)
