"""Tests for input validation (URL, language, SSRF protection)."""
import pytest
from pydantic import ValidationError
from app.models.schemas import SummaryRequest, validate_youtube_host


class TestYouTubeHostValidation:
    def test_allowed_hosts(self):
        assert validate_youtube_host("https://www.youtube.com/watch?v=abc123") is True
        assert validate_youtube_host("https://youtu.be/abc123") is True
        assert validate_youtube_host("https://m.youtube.com/watch?v=abc123") is True
        assert validate_youtube_host("https://youtube.com/shorts/abc123") is True

    def test_ssrf_blocked_hosts(self):
        assert validate_youtube_host("https://evil.com/watch?v=abc123") is False
        assert validate_youtube_host("https://youtube.com.evil.com/watch?v=abc123") is False
        assert validate_youtube_host("http://localhost/watch?v=abc123") is False
        assert validate_youtube_host("http://169.254.169.254/watch?v=abc123") is False
        assert validate_youtube_host("https://fakeyoutube.com/watch?v=abc123") is False


class TestSummaryRequestValidation:
    def test_valid_url(self):
        r = SummaryRequest(url="https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        assert r.url == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

    def test_valid_short_url(self):
        r = SummaryRequest(url="https://youtu.be/dQw4w9WgXcQ")
        assert "youtu.be" in r.url

    def test_valid_shorts_url(self):
        r = SummaryRequest(url="https://youtube.com/shorts/dQw4w9WgXcQ")
        assert r.url is not None

    def test_invalid_url_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            SummaryRequest(url="https://evil.com/watch?v=dQw4w9WgXcQ")
        assert "YouTube" in str(exc_info.value)

    def test_non_url_rejected(self):
        with pytest.raises(ValidationError):
            SummaryRequest(url="not a url at all")

    def test_invalid_language_rejected(self):
        with pytest.raises(ValidationError):
            SummaryRequest(url="https://youtu.be/dQw4w9WgXcQ", language="xx")

    def test_valid_languages(self):
        for lang in ["es", "en", "fr", "pt", "de", "it"]:
            r = SummaryRequest(url="https://youtu.be/dQw4w9WgXcQ", language=lang)
            assert r.language == lang

    def test_default_values(self):
        r = SummaryRequest(url="https://youtu.be/dQw4w9WgXcQ")
        assert r.language == "es"
        assert r.length == "medium"
        assert r.include_chapters is True
        assert r.include_key_points is True
        assert r.include_transcript is False

    def test_url_whitespace_stripped(self):
        r = SummaryRequest(url="  https://youtu.be/dQw4w9WgXcQ  ")
        assert not r.url.startswith(" ")
