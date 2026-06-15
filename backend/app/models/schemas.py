from pydantic import BaseModel
from typing import Optional
from enum import Enum
from datetime import datetime


class JobStatus(str, Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class SummaryLength(str, Enum):
    short = "short"
    medium = "medium"
    detailed = "detailed"


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
