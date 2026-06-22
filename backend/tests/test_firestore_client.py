"""Tests for Firestore client utilities."""
import pytest
from app.db.firestore_client import _parse_filter, _escape_newlines_inside_json_strings, _serialize_timestamp
from datetime import datetime, timezone


class TestParseFilter:
    def test_single_filter(self):
        result = _parse_filter('clerk_user_id="user_abc"')
        assert result == [("clerk_user_id", "user_abc")]

    def test_double_filter(self):
        result = _parse_filter('clerk_user_id="user_abc"&&month="2026-06"')
        assert result == [("clerk_user_id", "user_abc"), ("month", "2026-06")]

    def test_empty_filter(self):
        assert _parse_filter("") == []

    def test_filter_with_spaces(self):
        result = _parse_filter('field="value"')
        assert result[0] == ("field", "value")


class TestEscapeNewlines:
    def test_clean_json_unchanged(self):
        json_str = '{"key": "value"}'
        assert _escape_newlines_inside_json_strings(json_str) == json_str

    def test_newline_in_string_value_escaped(self):
        # A PEM key with literal newlines inside a JSON string
        broken = '{"private_key": "-----BEGIN RSA PRIVATE KEY-----\nMIIEpAIB\n-----END RSA PRIVATE KEY-----"}'
        fixed = _escape_newlines_inside_json_strings(broken)
        assert "\\n" in fixed
        # The outer JSON should be parseable now
        import json
        parsed = json.loads(fixed)
        assert "private_key" in parsed

    def test_newline_outside_string_preserved(self):
        json_str = '{\n"key": "value"\n}'
        result = _escape_newlines_inside_json_strings(json_str)
        # Newlines outside strings stay as-is (they're part of JSON formatting)
        import json
        parsed = json.loads(result)
        assert parsed["key"] == "value"


class TestSerializeTimestamp:
    def test_none_returns_none(self):
        assert _serialize_timestamp(None) is None

    def test_datetime_returns_isoformat(self):
        dt = datetime(2026, 6, 22, 12, 0, 0, tzinfo=timezone.utc)
        result = _serialize_timestamp(dt)
        assert "2026-06-22" in result

    def test_string_returns_string(self):
        assert _serialize_timestamp("2026-01-01T00:00:00Z") == "2026-01-01T00:00:00Z"
