"""
Servicio de extracción de datos de YouTube.
Obtiene transcript, metadatos y thumbnails.
"""

import re
import httpx
from typing import Optional
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound


class YouTubeService:

    def extract_video_id(self, url: str) -> Optional[str]:
        """Extrae el video_id de cualquier formato de URL de YouTube."""
        patterns = [
            r"(?:v=|\/)([0-9A-Za-z_-]{11}).*",
            r"(?:embed\/)([0-9A-Za-z_-]{11})",
            r"(?:youtu\.be\/)([0-9A-Za-z_-]{11})",
            r"(?:shorts\/)([0-9A-Za-z_-]{11})",
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None

    async def get_metadata(self, video_id: str) -> dict:
        """Obtiene metadatos del video usando la API pública de YouTube."""
        # Usamos el endpoint oEmbed que no requiere API key
        url = f"https://www.youtube.com/oembed?url=https://youtube.com/watch?v={video_id}&format=json"
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "title": data.get("title", "Video sin título"),
                    "thumbnail": data.get("thumbnail_url", f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"),
                    "author": data.get("author_name", ""),
                }
        return {
            "title": "Video de YouTube",
            "thumbnail": f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg",
            "author": "",
        }

    def get_transcript(self, video_id: str, language: str = "es") -> dict:
        """
        Obtiene la transcripción del video.
        Returns:
            raw: texto plano sin timestamps
            with_timestamps: lista de segmentos con tiempo
            duration_seconds: duración total estimada
        """
        try:
            # Intentar en el idioma solicitado, luego fallback
            languages_to_try = [language, "en", "es"]

            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

            transcript = None
            for lang in languages_to_try:
                try:
                    transcript = transcript_list.find_transcript([lang])
                    break
                except Exception:
                    continue

            if transcript is None:
                # Último recurso: cualquier transcript disponible
                transcript = transcript_list.find_generated_transcript(
                    [t.language_code for t in transcript_list]
                )

            segments = transcript.fetch()

            # Texto plano
            raw_text = " ".join([s["text"] for s in segments])

            # Con timestamps para detección de capítulos
            with_timestamps = "\n".join(
                [f"[{self._format_time(s['start'])}] {s['text']}" for s in segments]
            )

            # Duración del último segmento
            duration = 0
            if segments:
                last = segments[-1]
                duration = int(last["start"] + last.get("duration", 0))

            return {
                "raw": raw_text,
                "with_timestamps": with_timestamps,
                "duration_seconds": duration,
                "language_detected": transcript.language_code,
            }

        except TranscriptsDisabled:
            raise ValueError("Este video no tiene transcripciones habilitadas")
        except NoTranscriptFound:
            raise ValueError("No se encontró transcripción para este video")
        except Exception as e:
            raise ValueError(f"Error al obtener transcripción: {str(e)}")

    def _format_time(self, seconds: float) -> str:
        m, s = divmod(int(seconds), 60)
        h, m = divmod(m, 60)
        if h:
            return f"{h:02d}:{m:02d}:{s:02d}"
        return f"{m:02d}:{s:02d}"


youtube_service = YouTubeService()
