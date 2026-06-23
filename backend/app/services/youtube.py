"""
Servicio de extracción de datos de YouTube.

Niveles de fallback:
1. Metadata: YouTube Data API v3 → oEmbed
2. Transcripción: youtube-transcript-api → faster-whisper (si ENABLE_WHISPER_FALLBACK=true)

Todas las operaciones de I/O bloqueante se ejecutan en run_in_executor
para no bloquear el event loop de FastAPI.
"""
import asyncio
import os
import re
import logging
import tempfile
import functools
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

import httpx
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound

logger = logging.getLogger(__name__)

YOUTUBE_DATA_API_KEY = os.environ.get("YOUTUBE_DATA_API_KEY", "")
WHISPER_MODEL_SIZE = os.environ.get("WHISPER_MODEL_SIZE", "base")
ENABLE_WHISPER_FALLBACK = os.environ.get("ENABLE_WHISPER_FALLBACK", "true").lower() == "true"

_whisper_model = None
_yt_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="youtube")


def _get_whisper_model():
    global _whisper_model
    if _whisper_model is None:
        from faster_whisper import WhisperModel
        logger.info(f"Cargando modelo Whisper '{WHISPER_MODEL_SIZE}'...")
        _whisper_model = WhisperModel(WHISPER_MODEL_SIZE, device="cpu", compute_type="int8")
    return _whisper_model


async def _run_blocking(fn, *args, **kwargs):
    loop = asyncio.get_event_loop()
    if kwargs:
        fn = functools.partial(fn, *args, **kwargs)
        return await loop.run_in_executor(_yt_executor, fn)
    return await loop.run_in_executor(_yt_executor, fn, *args)


class YouTubeService:

    def extract_video_id(self, url: str) -> Optional[str]:
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
        if YOUTUBE_DATA_API_KEY:
            data = await self._get_metadata_via_data_api(video_id)
            if data:
                return data
        return await self._get_metadata_via_oembed(video_id)

    async def _get_metadata_via_data_api(self, video_id: str) -> Optional[dict]:
        url = "https://www.googleapis.com/youtube/v3/videos"
        params = {"part": "snippet,contentDetails", "id": video_id, "key": YOUTUBE_DATA_API_KEY}
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(url, params=params)
                if resp.status_code != 200:
                    return None
                items = resp.json().get("items", [])
                if not items:
                    return None
                snippet = items[0]["snippet"]
                duration_iso = items[0]["contentDetails"]["duration"]
                thumbnails = snippet.get("thumbnails", {})
                thumb = (
                    thumbnails.get("maxres") or thumbnails.get("high")
                    or thumbnails.get("medium") or thumbnails.get("default") or {}
                )
                return {
                    "title": snippet.get("title", "Video sin título"),
                    "thumbnail": thumb.get("url", f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"),
                    "author": snippet.get("channelTitle", ""),
                    "duration_seconds_hint": self._parse_iso8601_duration(duration_iso),
                }
        except Exception as e:
            logger.warning(f"YouTube Data API falló: {e}")
            return None

    async def _get_metadata_via_oembed(self, video_id: str) -> dict:
        url = f"https://www.youtube.com/oembed?url=https://youtube.com/watch?v={video_id}&format=json"
        async with httpx.AsyncClient(timeout=10) as client:
            try:
                resp = await client.get(url)
                if resp.status_code == 200:
                    data = resp.json()
                    return {
                        "title": data.get("title", "Video sin título"),
                        "thumbnail": data.get("thumbnail_url", f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"),
                        "author": data.get("author_name", ""),
                    }
            except Exception:
                pass
        return {
            "title": "Video de YouTube",
            "thumbnail": f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg",
            "author": "",
        }

    @staticmethod
    def _parse_iso8601_duration(duration: str) -> int:
        match = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", duration)
        if not match:
            return 0
        h, m, s = (int(x) if x else 0 for x in match.groups())
        return h * 3600 + m * 60 + s

    async def get_transcript(self, video_id: str, language: str = "es") -> dict:
        """Async wrapper — runs blocking transcript fetch in thread pool."""
        try:
            return await _run_blocking(self._get_transcript_via_api, video_id, language)
        except Exception as e:
            logger.warning(f"youtube-transcript-api falló para {video_id}: {e}")
            if ENABLE_WHISPER_FALLBACK:
                logger.info(f"Probando fallback Whisper para {video_id}...")
                return await _run_blocking(self._get_transcript_via_whisper, video_id, language)
            raise ValueError(str(e))

    def _get_transcript_via_api(self, video_id: str, language: str) -> dict:
        try:
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            transcript = None
            for lang in [language, "en", "es"]:
                try:
                    transcript = transcript_list.find_transcript([lang])
                    break
                except Exception:
                    continue

            if transcript is None:
                codes = [t.language_code for t in transcript_list]
                transcript = transcript_list.find_generated_transcript(codes)

            segments = transcript.fetch()
            raw_text = " ".join([s["text"] for s in segments])
            with_timestamps = "\n".join(
                [f"[{self._fmt(s['start'])}] {s['text']}" for s in segments]
            )
            duration = 0
            if segments:
                last = segments[-1]
                duration = int(last["start"] + last.get("duration", 0))

            return {
                "raw": raw_text,
                "with_timestamps": with_timestamps,
                "duration_seconds": duration,
                "language_detected": transcript.language_code,
                "source": "youtube_captions",
            }
        except TranscriptsDisabled:
            raise ValueError("Este video no tiene transcripciones habilitadas")
        except NoTranscriptFound:
            raise ValueError("No se encontró transcripción para este video")

    def _get_transcript_via_whisper(self, video_id: str, language: str) -> dict:
        import yt_dlp

        with tempfile.TemporaryDirectory() as tmpdir:
            audio_path = os.path.join(tmpdir, f"{video_id}.mp3")
            ydl_opts = {
                "format": "bestaudio/best",
                "outtmpl": os.path.join(tmpdir, video_id),
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "64",
                }],
                "quiet": True,
                "no_warnings": True,
                "extractor_args": {"youtube": {"player_client": ["android"]}},
                "http_headers": {"User-Agent": "com.google.android.youtube/19.09.37 (Linux; U; Android 14)"},
            }
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([f"https://www.youtube.com/watch?v={video_id}"])
            except Exception as e:
                error_text = str(e)
                if "Sign in to confirm" in error_text or "not a bot" in error_text:
                    raise ValueError(
                        "YouTube está bloqueando temporalmente la descarga de audio "
                        "desde este servidor (detección anti-bot). Prueba con un video "
                        "que tenga subtítulos/CC activados."
                    )
                raise ValueError(f"No se pudo descargar el audio del video: {error_text}")

            if not os.path.exists(audio_path):
                raise ValueError("No se pudo extraer el audio del video")

            model = _get_whisper_model()
            segments_iter, info = model.transcribe(
                audio_path,
                language=language if language != "auto" else None,
                vad_filter=True,
            )

            segments = []
            raw_parts = []
            ts_parts = []
            for seg in segments_iter:
                text = seg.text.strip()
                raw_parts.append(text)
                ts_parts.append(f"[{self._fmt(seg.start)}] {text}")
                segments.append({"start": seg.start, "duration": seg.end - seg.start})

            if not raw_parts:
                raise ValueError("Whisper no pudo extraer ningún texto del audio")

            duration = int(segments[-1]["start"] + segments[-1]["duration"]) if segments else 0

            return {
                "raw": " ".join(raw_parts),
                "with_timestamps": "\n".join(ts_parts),
                "duration_seconds": duration,
                "language_detected": info.language,
                "source": "whisper_fallback",
            }

    def _fmt(self, seconds: float) -> str:
        m, s = divmod(int(seconds), 60)
        h, m = divmod(m, 60)
        return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


youtube_service = YouTubeService()
