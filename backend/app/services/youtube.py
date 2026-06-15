import re
import httpx
from typing import Optional
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound


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

    def get_transcript(self, video_id: str, language: str = "es") -> dict:
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
            }
        except TranscriptsDisabled:
            raise ValueError("Este video no tiene transcripciones habilitadas")
        except NoTranscriptFound:
            raise ValueError("No se encontró transcripción para este video")
        except Exception as e:
            raise ValueError(f"Error al obtener transcripción: {str(e)}")

    def _fmt(self, seconds: float) -> str:
        m, s = divmod(int(seconds), 60)
        h, m = divmod(m, 60)
        return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


youtube_service = YouTubeService()
