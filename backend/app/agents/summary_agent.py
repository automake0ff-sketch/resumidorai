import json
import anthropic
from app.prompts.prompts import (
    TRANSCRIPT_CLEANER_PROMPT,
    SUMMARY_GENERATOR_PROMPT,
    SUMMARY_LENGTH_GUIDES,
    KEY_POINTS_PROMPT,
    CHAPTER_DETECTOR_PROMPT,
)

client = None
MODEL = "claude-sonnet-4-6"


def get_client() -> anthropic.Anthropic:
    global client
    if client is None:
        client = anthropic.Anthropic()
    return client

LANGUAGE_NAMES = {
    "es": "español", "en": "English", "fr": "français",
    "pt": "português", "de": "Deutsch", "it": "italiano",
}


class TranscriptCleanerAgent:
    async def run(self, raw_transcript: str) -> str:
        if len(raw_transcript) < 100:
            return raw_transcript
        msg = get_client().messages.create(
            model=MODEL, max_tokens=4096,
            messages=[{"role": "user", "content": TRANSCRIPT_CLEANER_PROMPT.format(
                raw_transcript=raw_transcript[:12000]
            )}],
        )
        return msg.content[0].text


class SummaryGeneratorAgent:
    async def run(self, transcript: str, title: str, duration_seconds: int,
                  language: str = "es", length: str = "medium") -> str:
        m, s = divmod(duration_seconds, 60)
        h, m2 = divmod(m, 60)
        duration_str = f"{h}h {m2}m" if h else f"{m}m {s}s"

        msg = get_client().messages.create(
            model=MODEL, max_tokens=2048,
            messages=[{"role": "user", "content": SUMMARY_GENERATOR_PROMPT.format(
                title=title, duration=duration_str, language=language,
                language_name=LANGUAGE_NAMES.get(language, language),
                transcript=transcript[:10000], length=length,
                length_guide=SUMMARY_LENGTH_GUIDES[length],
            )}],
        )
        return msg.content[0].text


class KeyPointsAgent:
    async def run(self, transcript: str, title: str, language: str = "es") -> list[str]:
        msg = get_client().messages.create(
            model=MODEL, max_tokens=1024,
            messages=[{"role": "user", "content": KEY_POINTS_PROMPT.format(
                title=title, transcript=transcript[:8000],
                language_name=LANGUAGE_NAMES.get(language, language),
            )}],
        )
        try:
            return json.loads(msg.content[0].text).get("key_points", [])
        except Exception:
            return []


class ChapterDetectorAgent:
    async def run(self, transcript_with_timestamps: str, title: str, language: str = "es") -> list[dict]:
        msg = get_client().messages.create(
            model=MODEL, max_tokens=2048,
            messages=[{"role": "user", "content": CHAPTER_DETECTOR_PROMPT.format(
                title=title,
                transcript_with_timestamps=transcript_with_timestamps[:10000],
                language_name=LANGUAGE_NAMES.get(language, language),
            )}],
        )
        try:
            return json.loads(msg.content[0].text).get("chapters", [])
        except Exception:
            return []


class VideoSummaryOrchestrator:
    def __init__(self):
        self.cleaner = TranscriptCleanerAgent()
        self.summarizer = SummaryGeneratorAgent()
        self.key_points_agent = KeyPointsAgent()
        self.chapter_agent = ChapterDetectorAgent()

    async def process(self, raw_transcript: str, transcript_with_timestamps: str,
                      title: str, duration_seconds: int, language: str = "es",
                      length: str = "medium", include_key_points: bool = True,
                      include_chapters: bool = True) -> dict:

        clean = await self.cleaner.run(raw_transcript)
        summary = await self.summarizer.run(clean, title, duration_seconds, language, length)

        result = {"summary": summary, "key_points": None, "chapters": None}

        if include_key_points:
            result["key_points"] = await self.key_points_agent.run(clean, title, language)

        if include_chapters and transcript_with_timestamps:
            result["chapters"] = await self.chapter_agent.run(
                transcript_with_timestamps, title, language
            )

        return result
