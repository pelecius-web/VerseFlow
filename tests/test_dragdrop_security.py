"""Unit tests for safe_json_loads() security validation.

Tests protect against malformed JSON, type errors, null byte injection,
and other potential attack vectors in drag-drop MIME data parsing.
"""

import json
import pytest
import sys
from pathlib import Path

# Add Source Code to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "2. Source Code"))

from models import safe_json_loads


class TestSafeJsonLoads:
    """Test suite for safe_json_loads() function."""

    def test_valid_list_returns_list(self):
        """Valid JSON list should be returned as-is."""
        result = safe_json_loads('[{"id": 1}]')
        assert result == [{"id": 1}]
        assert isinstance(result, list)

    def test_valid_dict_returns_empty_list(self):
        """Non-list JSON should return empty list for safety."""
        result = safe_json_loads('{"id": 1}')
        assert result == []
        assert isinstance(result, list)

    def test_malformed_json_returns_empty_list(self):
        """Malformed JSON should return empty list instead of crashing."""
        assert safe_json_loads('{"id": 1,}') == []
        assert safe_json_loads('not json') == []
        assert safe_json_loads('') == []
        assert safe_json_loads('[') == []
        assert safe_json_loads('{') == []

    def test_null_bytes_returns_empty_list(self):
        """Null byte injection attempt should be handled safely."""
        assert safe_json_loads('[\x00{"id": 1}]') == []
        assert safe_json_loads('\x00') == []

    def test_unicode_escape_handling(self):
        """Valid unicode escapes should work correctly."""
        result = safe_json_loads('[{"text": "\\u0048\\u0069"}]')
        assert result == [{"text": "Hi"}]

    def test_deeply_nested_list_capped(self):
        """Should handle reasonably deep nesting without issues."""
        deep = json.dumps([{"a": {"b": {"c": {"d": "e"}}}}])
        result = safe_json_loads(deep)
        assert result is not None
        assert isinstance(result, list)

    def test_empty_list_returns_empty_list(self):
        """Empty JSON list should return empty list."""
        result = safe_json_loads('[]')
        assert result == []

    def test_default_parameter_respected(self):
        """Custom default parameter should be respected."""
        result = safe_json_loads('not json', default=[{"default": True}])
        assert result == [{"default": True}]

    def test_none_default_returns_empty_list(self):
        """None as default should result in empty list on failure."""
        result = safe_json_loads('not json', default=None)
        assert result == []

    def test_type_error_handling(self):
        """Non-string input should be handled gracefully."""
        assert safe_json_loads(None) == []
        assert safe_json_loads(123) == []
        assert safe_json_loads([]) == []

    def test_large_list_handling(self):
        """Should handle reasonably large lists without crashing."""
        large_list = [{"id": i} for i in range(1000)]
        result = safe_json_loads(json.dumps(large_list))
        assert len(result) == 1000
        assert result == large_list

    def test_boolean_false_not_treated_as_failure(self):
        """JSON boolean false should not be treated as parse failure."""
        result = safe_json_loads('[false]')
        assert result == [False]

    def test_numeric_values_preserved(self):
        """Numeric values in list should be preserved."""
        result = safe_json_loads('[1, 2.5, -10]')
        assert result == [1, 2.5, -10]

    def test_mixed_types_in_list(self):
        """Mixed types in list should be handled correctly."""
        result = safe_json_loads('[{"id": 1}, "string", 123, null]')
        assert len(result) == 4
        assert result[0] == {"id": 1}
        assert result[1] == "string"
        assert result[2] == 123
        assert result[3] is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
