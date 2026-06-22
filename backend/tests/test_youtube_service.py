"""Tests for YouTube service: video ID extraction, URL parsing."""
import pytest
from app.services.youtube import YouTubeService

svc = YouTubeService()


class TestVideoIdExtraction:
    def test_standard_watch_url(self):
        assert svc.extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_short_url(self):
        assert svc.extract_video_id("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_embed_url(self):
        assert svc.extract_video_id("https://www.youtube.com/embed/dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_shorts_url(self):
        assert svc.extract_video_id("https://youtube.com/shorts/dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_url_with_timestamp(self):
        assert svc.extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=42s") == "dQw4w9WgXcQ"

    def test_mobile_url(self):
        assert svc.extract_video_id("https://m.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_invalid_url_returns_none(self):
        assert svc.extract_video_id("https://evil.com/watch?v=abc") is None

    def test_non_youtube_returns_none(self):
        assert svc.extract_video_id("https://vimeo.com/123456") is None

    def test_empty_string_returns_none(self):
        assert svc.extract_video_id("") is None


class TestDurationParsing:
    def test_minutes_only(self):
        assert svc._parse_iso8601_duration("PT5M") == 300

    def test_hours_and_minutes(self):
        assert svc._parse_iso8601_duration("PT1H30M") == 5400

    def test_full_duration(self):
        assert svc._parse_iso8601_duration("PT2H15M30S") == 8130

    def test_seconds_only(self):
        assert svc._parse_iso8601_duration("PT45S") == 45

    def test_invalid_returns_zero(self):
        assert svc._parse_iso8601_duration("invalid") == 0

    def test_empty_returns_zero(self):
        assert svc._parse_iso8601_duration("") == 0


class TestTimestampFormat:
    def test_minutes_and_seconds(self):
        assert svc._fmt(90) == "01:30"

    def test_hours_minutes_seconds(self):
        assert svc._fmt(3661) == "01:01:01"

    def test_zero(self):
        assert svc._fmt(0) == "00:00"
