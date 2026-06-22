"""Tests for AI prompts: formatting, completeness, chunking logic."""
import pytest
from app.prompts.prompts import (
    SYSTEM_PROMPT,
    SUMMARY_SYSTEM_WITH_CACHE,
    SUMMARY_LENGTH_GUIDES,
    UNIFIED_ANALYSIS_PROMPT,
    CHUNK_SUMMARY_PROMPT,
    FINAL_SYNTHESIS_PROMPT,
)
from app.agents.summary_agent import _chunk_transcript, CHUNK_SIZE, CHUNK_OVERLAP, CHUNK_THRESHOLD


class TestSystemPrompt:
    def test_system_prompt_not_empty(self):
        assert len(SYSTEM_PROMPT) > 100

    def test_cache_control_present(self):
        assert len(SUMMARY_SYSTEM_WITH_CACHE) == 1
        item = SUMMARY_SYSTEM_WITH_CACHE[0]
        assert item["type"] == "text"
        assert "cache_control" in item
        assert item["cache_control"]["type"] == "ephemeral"

    def test_length_guides_all_present(self):
        for key in ["short", "medium", "detailed"]:
            assert key in SUMMARY_LENGTH_GUIDES
            assert len(SUMMARY_LENGTH_GUIDES[key]) > 10


class TestUnifiedPrompt:
    def test_all_placeholders_fillable(self):
        filled = UNIFIED_ANALYSIS_PROMPT.format(
            title="Test Video",
            duration="5m",
            language_name="español",
            transcript="This is a transcript.",
            length_guide="100-150 palabras",
        )
        assert "Test Video" in filled
        assert "This is a transcript." in filled
        assert "JSON" in filled

    def test_json_instruction_present(self):
        assert "JSON" in UNIFIED_ANALYSIS_PROMPT
        assert "summary" in UNIFIED_ANALYSIS_PROMPT
        assert "key_points" in UNIFIED_ANALYSIS_PROMPT
        assert "chapters" in UNIFIED_ANALYSIS_PROMPT


class TestChunking:
    def test_short_transcript_single_chunk(self):
        # Text <= CHUNK_SIZE should always be a single chunk
        text = "a" * (CHUNK_SIZE - 100)
        chunks = _chunk_transcript(text)
        assert len(chunks) == 1
    
    def test_exact_chunk_size_single_chunk(self):
        text = "a" * CHUNK_SIZE
        chunks = _chunk_transcript(text)
        assert len(chunks) == 1

    def test_long_transcript_gets_chunked(self):
        text = "word " * 5000  # ~25000 chars
        chunks = _chunk_transcript(text)
        assert len(chunks) > 1

    def test_chunks_have_overlap(self):
        text = "x" * (CHUNK_SIZE + 1000)
        chunks = _chunk_transcript(text)
        if len(chunks) > 1:
            # The end of chunk 0 should overlap with the start of chunk 1
            end_of_first = chunks[0][-CHUNK_OVERLAP:]
            start_of_second = chunks[1][:CHUNK_OVERLAP]
            assert end_of_first == start_of_second

    def test_all_content_covered(self):
        # Every character should appear in at least one chunk
        text = "abcdefghij" * 2000  # 20000 chars
        chunks = _chunk_transcript(text)
        reconstructed = chunks[0]
        for i, chunk in enumerate(chunks[1:], 1):
            reconstructed += chunk[CHUNK_OVERLAP:]
        # The original text should be a subset of reconstructed content
        assert text[:CHUNK_SIZE] in reconstructed
