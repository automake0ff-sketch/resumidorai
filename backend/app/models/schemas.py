from pydantic import BaseModel, HttpUrl
from typing import Optional
from enum import Enum
from datetime import datetime


class JobStatus(str, Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class SummaryLength(str, Enum):
    short = "short"        # ~150 palabras
    medium = "medium"      # ~300 palabras
    detailed = "detailed"  # ~600 palabras


class SummaryRequest(BaseModel):
    url: str
    language: str = "es"
    length: SummaryLength = SummaryLength.medium
    include_chapters: bool = True
    include_key_points: bool = True
    include_transcript: bool = False


class SummaryResponse(BaseModel):
    job_id: str
    status: JobStatus
    created_at: datetime


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
    created_at: datetime
    completed_at: Optional[datetime] = None


class UsageStats(BaseModel):
    user_id: str
    summaries_this_month: int
    summaries_limit: int
    plan: str
