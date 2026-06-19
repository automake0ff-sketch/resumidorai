import re
from urllib.parse import urlparse
from pydantic import BaseModel, field_validator
from typing import Optional
from enum import Enum

YOUTUBE_URL_PATTERN = re.compile(
    r"(?:youtube\.com/(?:watch\?v=|embed/|shorts/)|youtu\.be/)[\w-]{11}"
)

# Allowed YouTube hosts for SSRF protection
ALLOWED_YOUTUBE_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be"}


def validate_youtube_host(url: str) -> bool:
    """Validate URL uses only allowed YouTube hosts to prevent SSRF."""
    try:
        parsed = urlparse(url)
        return parsed.hostname in ALLOWED_YOUTUBE_HOSTS
    except Exception:
        return False


class JobStatus(str, Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class SummaryLength(str, Enum):
    short = "short"
    medium = "medium"
    detailed = "detailed"


SUPPORTED_LANGUAGES = {"es", "en", "fr", "pt", "de", "it"}


class SummaryRequest(BaseModel):
    url: str
    language: str = "es"
    length: SummaryLength = SummaryLength.medium
    include_chapters: bool = True
    include_key_points: bool = True
    include_transcript: bool = False

    @field_validator("url")
    @classmethod
    def validate_youtube_url(cls, v: str) -> str:
        v = v.strip()
        if not YOUTUBE_URL_PATTERN.search(v):
            raise ValueError("Debe ser una URL válida de YouTube (youtube.com o youtu.be)")
        if not validate_youtube_host(v):
            raise ValueError("Solo se permiten URLs de youtube.com, www.youtube.com, m.youtube.com y youtu.be")
        return v

    @field_validator("language")
    @classmethod
    def validate_language(cls, v: str) -> str:
        v = v.lower().strip()
        if v not in SUPPORTED_LANGUAGES:
            raise ValueError(f"Idioma no soportado. Usa uno de: {', '.join(sorted(SUPPORTED_LANGUAGES))}")
        return v


class SummaryResponse(BaseModel):
    job_id: str
    status: JobStatus


class SummaryResult(BaseModel):
    job_id: str
    status: JobStatus
    url: str
    title: Optional[str] = None
    thumbnail: Optional[str] = None
    duration_seconds: Optional[int] = None
    summary: Optional[str] = None
    key_points: Optional[list[str]] = None
    chapters: Optional[list[dict]] = None
    transcript: Optional[str] = None
    language: str = "es"
    error: Optional[str] = None
    created: Optional[str] = None
    completed_at: Optional[str] = None


class UsageStats(BaseModel):
    summaries_this_month: int
    summaries_limit: int
    plan: str
