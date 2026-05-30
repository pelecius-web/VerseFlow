import sys
sys.path.insert(0, "src/utils")
from theme import generate_stylesheet, ThemeManager, Theme, TYPOGRAPHY_DEFAULTS, TYPO_COLOR_TOKENS, BUILTIN_THEME_IDS
import json

mgr = ThemeManager()
print("=== Phase 0 Full Verification ===")

# 1. All 3 built-in theme JSONs have typography with 4 keys
EXPECTED_TYPO_KEYS = {"compact", "standard", "body", "hint"}
for builtin_id in BUILTIN_THEME_IDS:
    t = mgr.get_theme(builtin_id)
    assert t is not None, f"Built-in theme {builtin_id} not found"
    typo_keys = set(t.typography.keys())
    missing = EXPECTED_TYPO_KEYS - typo_keys
    assert not missing, f"{builtin_id} typography missing keys: {missing}"
    print(f"  [OK] {builtin_id} has all 4 typography keys")

# 2. Theme.__init__ provides fallback for themes lacking typography
sample_no_typo = {"id": "no_typo", "name": "No Typo", "schema_version": "2.0",
                  "colors": {"gold": "#c8a03c"}, "fonts": {"family": "Segoe UI"},
                  "lower_third": {}, "fullscreen": {}, "spacing": {}, "animation": {}}
t_no_typo = Theme(sample_no_typo)
assert t_no_typo.typography is not TYPOGRAPHY_DEFAULTS, "Shared reference mutation risk"
assert set(t_no_typo.typography.keys()) == EXPECTED_TYPO_KEYS, "Fallback missing expected keys"
print("  [OK] Themes without typography get independent TYPOGRAPHY_DEFAULTS fallback")

# 3. deep_copy preserves and isolates typography (B1)
sample_custom = {"id": "custom", "name": "Custom", "schema_version": "2.0",
                 "colors": {"gold": "#c8a03c"}, "fonts": {"family": "Segoe UI"},
                 "lower_third": {}, "fullscreen": {}, "spacing": {}, "animation": {},
                 "typography": {"compact": {"size": 11, "weight": "Bold", "uppercase": True, "letter_spacing": 3}}}
t_custom = Theme(sample_custom)
assert t_custom.typography["compact"]["size"] == 11, "Custom typography not preserved on init"
copy_t = t_custom.deep_copy()
assert copy_t.typography["compact"]["size"] == 11, "deep_copy lost custom typography (B1)"
copy_t.typography["compact"]["size"] = 99
assert t_custom.typography["compact"]["size"] == 11, "deep_copy mutation contaminated original"
print("  [OK] Theme.deep_copy preserves and isolates typography (B1)")

# 4. _to_dict includes typography (B1)
d = t_custom._to_dict()
assert "typography" in d, "_to_dict missing typography (B1)"
assert d["typography"]["compact"]["size"] == 11, "_to_dict lost custom typography value"
print("  [OK] Theme._to_dict includes typography (B1)")

# 5. Schema v1.0 themes get typography defaults via _upgrade_to_v2
v1_sample = {"id": "v1theme", "name": "V1 Theme", "schema_version": "1.0",
             "colors": {"gold": "#c8a03c"}, "fonts": {"family": "Segoe UI"},
             "lower_third": {}, "spacing": {}, "animation": {}}
t_v1 = Theme(v1_sample)
assert t_v1.schema_version == "2.0", "Schema version not upgraded"
assert set(t_v1.typography.keys()) == EXPECTED_TYPO_KEYS, "v1.0 theme missing typography after upgrade"
print("  [OK] Schema v1.0 themes get typography defaults via _upgrade_to_v2")

# 6. generate_stylesheet emits typography and section-header selectors
qss = generate_stylesheet(mgr.get_theme('dark_gold'))
assert 'QLabel[typography=' in qss, "Typography selectors missing"
assert 'QLabel[section-header=' in qss, "Section-header selectors missing"
print("  [OK] generate_stylesheet emits QLabel[typography=X] and QLabel[section-header=X] selectors")

# 7. Deprecated alias preserved
lines = qss.split('\n')
alias_lines = [l for l in lines if 'QLabel[section-header="true"]' in l]
assert len(alias_lines) > 0, "Deprecated alias missing"
alias_block = '\n'.join(lines[lines.index(alias_lines[0]):lines.index(alias_lines[0])+8])
assert 'font-size: 9px' in alias_block, "Deprecated alias wrong font-size (F7)"
assert 'letter-spacing: 2px' in alias_block, "Deprecated alias wrong letter-spacing (F7)"
print("  [OK] Deprecated alias QLabel[section-header=true] renders as compact (font-size:9px, letter-spacing:2px)")

# 8. Typography hint uses nav_inactive_text, not gold (F2)
hint_lines = [l for l in lines if 'QLabel[typography="hint"]' in l]
assert len(hint_lines) > 0, "Typography hint selector missing"
hint_block = '\n'.join(lines[lines.index(hint_lines[0]):lines.index(hint_lines[0])+8])
# dark_gold's nav_inactive_text color value is "rgba(200,160,60,0.4)"
assert 'rgba(200,160,60,0.4)' in hint_block, "Hint typography should use nav_inactive_text, not gold (F2)"
print("  [OK] QLabel[typography=hint] uses nav_inactive_text color (not gold) (F2)")

# 9. Existing panels render without regression — generate_stylesheet still produces all original selectors
original_selectors = ['QMainWindow', 'QFrame[sidebar', 'QFrame[panel', 'QFrame[preview',
                       'QFrame[crossref', 'QFrame[draft', 'QLineEdit', 'QComboBox',
                       'QScrollArea', 'QScrollBar', 'QStatusBar', 'QPushButton',
                       'QFrame[card', 'QLabel[hint', 'QCheckBox', 'QDialog', 'QTextEdit']
for sel in original_selectors:
    assert sel in qss, f"Original selector {sel} missing from stylesheet — regression!"
print("  [OK] All original stylesheet selectors still present — zero regression")

# 10. Round-trip test: deep_copy -> _to_dict -> Theme -> verify typography preserved
round_trip_data = t_custom._to_dict()
round_trip_theme = Theme(round_trip_data)
assert round_trip_theme.typography["compact"]["size"] == 11, "Round-trip lost typography"
print("  [OK] Round-trip: _to_dict -> Theme preserves typography")

print("\n=== ALL PHASE 0 VERIFICATION PASSED ===")
