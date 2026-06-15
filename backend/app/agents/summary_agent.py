"""
Agentes IA del sistema VideoSummary
Cada agente tiene una responsabilidad específica y se puede encadenar.
"""

import json
import anthropic
from typing import Optional
from app.prompts.prompts import (
    TRANSCRIPT_CLEANER_PROMPT,
    SUMMARY_GENERATOR_PROMPT,
    SUMMARY_LENGTH_GUIDES,
    KEY_POINTS_PROMPT,
    CHAPTER_DETECTOR_PROMPT,
    CONTENT_CLASSIFIER_PROMPT,
)

client = anthropic.Anthropic()
MODEL = "claude-sonnet-4-6"

LANGUAGE_NAMES = {
    "es": "español",
    "en": "English",
    "fr": "français",
    "pt": "português",
    "de": "Deutsch",
    "it": "italiano",
}


# ─────────────────────────────────────────────
# AGENTE 1: LIMPIADOR DE TRANSCRIPCIÓN
# ─────────────────────────────────────────────
class TranscriptCleanerAgent:
    """Limpia y normaliza transcripciones brutas de YouTube/video."""

    async def run(self, raw_transcript: str) -> str:
        if len(raw_transcript) < 100:
            return raw_transcript

        message = client.messages.create(
            model=MODEL,
            max_tokens=4096,
            messages=[
                {
                    "role": "user",
                    "content": TRANSCRIPT_CLEANER_PROMPT.format(
                        raw_transcript=raw_transcript[:12000]  # Limite de tokens
                    ),
                }
            ],
        )
        return message.content[0].text


# ─────────────────────────────────────────────
# AGENTE 2: GENERADOR DE RESUMEN
# ─────────────────────────────────────────────
class SummaryGeneratorAgent:
    """Genera el resumen principal del video."""

    async def run(
        self,
        transcript: str,
        title: str,
        duration_seconds: int,
        language: str = "es",
        length: str = "medium",
    ) -> str:
        duration_str = self._format_duration(duration_seconds)
        language_name = LANGUAGE_NAMES.get(language, language)

        message = client.messages.create(
            model=MODEL,
            max_tokens=2048,
            messages=[
                {
                    "role": "user",
                    "content": SUMMARY_GENERATOR_PROMPT.format(
                        title=title,
                        duration=duration_str,
                        language=language,
                        language_name=language_name,
                        transcript=transcript[:10000],
                        length=length,
                        length_guide=SUMMARY_LENGTH_GUIDES[length],
                    ),
                }
            ],
        )
        return message.content[0].text

    def _format_duration(self, seconds: int) -> str:
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        if h:
            return f"{h}h {m}m"
        return f"{m}m {s}s"


# ─────────────────────────────────────────────
# AGENTE 3: EXTRACTOR DE PUNTOS CLAVE
# ─────────────────────────────────────────────
class KeyPointsAgent:
    """Extrae los puntos más importantes del video."""

    async def run(
        self, transcript: str, title: str, language: str = "es"
    ) -> list[str]:
        language_name = LANGUAGE_NAMES.get(language, language)

        message = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            messages=[
                {
                    "role": "user",
                    "content": KEY_POINTS_PROMPT.format(
                        title=title,
                        transcript=transcript[:8000],
                        language_name=language_name,
                    ),
                }
            ],
        )

        try:
            result = json.loads(message.content[0].text)
            return result.get("key_points", [])
        except (json.JSONDecodeError, IndexError):
            return []


# ─────────────────────────────────────────────
# AGENTE 4: DETECTOR DE CAPÍTULOS
# ─────────────────────────────────────────────
class ChapterDetectorAgent:
    """Detecta y estructura los capítulos temáticos del video."""

    async def run(
        self,
        transcript_with_timestamps: str,
        title: str,
        language: str = "es",
    ) -> list[dict]:
        language_name = LANGUAGE_NAMES.get(language, language)

        message = client.messages.create(
            model=MODEL,
            max_tokens=2048,
            messages=[
                {
                    "role": "user",
                    "content": CHAPTER_DETECTOR_PROMPT.format(
                        title=title,
                        transcript_with_timestamps=transcript_with_timestamps[:10000],
                        language_name=language_name,
                    ),
                }
            ],
        )

        try:
            result = json.loads(message.content[0].text)
            return result.get("chapters", [])
        except (json.JSONDecodeError, IndexError):
            return []


# ─────────────────────────────────────────────
# ORQUESTADOR: PIPELINE COMPLETO
# ─────────────────────────────────────────────
class VideoSummaryOrchestrator:
    """
    Orquesta todos los agentes para procesar un video completo.
    Pipeline: clean → summarize → key_points → chapters (parallel)
    """

    def __init__(self):
        self.cleaner = TranscriptCleanerAgent()
        self.summarizer = SummaryGeneratorAgent()
        self.key_points_agent = KeyPointsAgent()
        self.chapter_agent = ChapterDetectorAgent()

    async def process(
        self,
        raw_transcript: str,
        transcript_with_timestamps: str,
        title: str,
        duration_seconds: int,
        language: str = "es",
        length: str = "medium",
        include_key_points: bool = True,
        include_chapters: bool = True,
    ) -> dict:
        # Paso 1: Limpiar transcript
        clean_transcript = await self.cleaner.run(raw_transcript)

        # Paso 2: Generar resumen (siempre)
        summary = await self.summarizer.run(
            transcript=clean_transcript,
            title=title,
            duration_seconds=duration_seconds,
            language=language,
            length=length,
        )

        result = {
            "summary": summary,
            "key_points": None,
            "chapters": None,
        }

        # Paso 3: Puntos clave (opcional)
        if include_key_points:
            result["key_points"] = await self.key_points_agent.run(
                transcript=clean_transcript,
                title=title,
                language=language,
            )

        # Paso 4: Capítulos (opcional)
        if include_chapters and transcript_with_timestamps:
            result["chapters"] = await self.chapter_agent.run(
                transcript_with_timestamps=transcript_with_timestamps,
                title=title,
                language=language,
            )

        return result
