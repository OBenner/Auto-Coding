"""Tests for the JSON recovery module."""

import json

import pytest
from core.json_recovery import parse_json_with_recovery


class TestTier1Direct:
    def test_valid_json_object(self):
        result, tier = parse_json_with_recovery('{"key": "value"}')
        assert result == {"key": "value"}
        assert tier == "tier1_direct"

    def test_valid_json_array(self):
        result, tier = parse_json_with_recovery("[1, 2, 3]")
        assert result == [1, 2, 3]
        assert tier == "tier1_direct"


class TestTier2Repair:
    def test_trailing_comma_object(self):
        result, tier = parse_json_with_recovery('{"a": 1, "b": 2,}')
        assert result == {"a": 1, "b": 2}
        assert tier == "tier2_repair"

    def test_trailing_comma_array(self):
        result, tier = parse_json_with_recovery("[1, 2, 3,]")
        assert result == [1, 2, 3]
        assert tier == "tier2_repair"

    def test_unclosed_brace(self):
        result, tier = parse_json_with_recovery('{"a": 1, "b": 2')
        assert result == {"a": 1, "b": 2}
        assert tier == "tier2_repair"

    def test_unclosed_bracket(self):
        result, tier = parse_json_with_recovery("[1, 2, 3")
        assert result == [1, 2, 3]
        assert tier == "tier2_repair"

    def test_unquoted_status_value(self):
        result, tier = parse_json_with_recovery('{"status": pending}')
        assert result == {"status": "pending"}
        assert tier == "tier2_repair"


class TestTier3Extract:
    def test_json_in_markdown_fence(self):
        text = 'Here is the plan:\n```json\n{"key": "value"}\n```\nDone.'
        result, tier = parse_json_with_recovery(text)
        assert result == {"key": "value"}
        assert tier == "tier3_extract"

    def test_json_in_plain_fence(self):
        text = "Output:\n```\n[1, 2, 3]\n```"
        result, tier = parse_json_with_recovery(text)
        assert result == [1, 2, 3]
        assert tier == "tier3_extract"

    def test_json_embedded_in_prose(self):
        text = 'The response is: {"name": "test", "value": 42} and that is all.'
        result, tier = parse_json_with_recovery(text)
        assert result == {"name": "test", "value": 42}
        assert tier == "tier3_extract"


class TestAllTiersFail:
    def test_completely_invalid_text(self):
        with pytest.raises(json.JSONDecodeError):
            parse_json_with_recovery("this is not json at all")

    def test_empty_string(self):
        with pytest.raises(json.JSONDecodeError):
            parse_json_with_recovery("")
