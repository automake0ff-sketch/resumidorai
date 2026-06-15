"""
Pipeline de procesamiento de jobs usando PocketBase.
"""
import uuid
from datetime import datetime, timezone
from app.db.pocketbase import pb_create, pb_update, pb_get, pb_get_first, pb_list, pb_delete
from app.services.youtube import youtube_service
from app.agents.summary_agent import VideoSummaryOrchestrator
from app.models.schemas import JobStatus, SummaryRequest

orchestrator = VideoSummaryOrchestrator()

PLAN_LIMITS = {"free": 5, "starter": 50, "pro": 200, "unlimited": 99999}


async def create_job(clerk_user_id: str, request: SummaryRequest) -> str:
    record = await pb_create("summary_jobs", {
        "clerk_user_id": clerk_user_id,
        "url": request.url,
        "language": request.language,
        "length": request.length,
        "include_chapters": request.include_chapters,
        "include_key_points": request.include_key_points,
        "include_transcript": request.include_transcript,
        "status": JobStatus.pending,
    })
    return record["id"]


async def process_job(job_id: str):
    try:
        await pb_update("summary_jobs", job_id, {
            "status": JobStatus.processing,
            "started_at": datetime.now(timezone.utc).isoformat(),
        })

        job = await pb_get("summary_jobs", job_id)

        video_id = youtube_service.extract_video_id(job["url"])
        if not video_id:
            raise ValueError(f"URL no válida: {job['url']}")

        metadata = await youtube_service.get_metadata(video_id)
        transcript_data = youtube_service.get_transcript(video_id, job["language"])

        ai_result = await orchestrator.process(
            raw_transcript=transcript_data["raw"],
            transcript_with_timestamps=transcript_data["with_timestamps"],
            title=metadata["title"],
            duration_seconds=transcript_data["duration_seconds"],
            language=job["language"],
            length=job["length"],
            include_key_points=job["include_key_points"],
            include_chapters=job["include_chapters"],
        )

        update_data = {
            "status": JobStatus.completed,
            "title": metadata["title"],
            "thumbnail": metadata["thumbnail"],
            "duration_seconds": transcript_data["duration_seconds"],
            "summary": ai_result["summary"],
            "key_points": ai_result["key_points"],
            "chapters": ai_result["chapters"],
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }

        if job["include_transcript"]:
            update_data["transcript"] = transcript_data["raw"]

        await pb_update("summary_jobs", job_id, update_data)
        await _increment_usage(job["clerk_user_id"])

    except Exception as e:
        await pb_update("summary_jobs", job_id, {
            "status": JobStatus.failed,
            "error": str(e),
            "completed_at": datetime.now(timezone.utc).isoformat(),
        })
        raise


async def _increment_usage(clerk_user_id: str):
    now = datetime.now(timezone.utc)
    month_key = f"{now.year}-{now.month:02d}"

    existing = await pb_get_first(
        "user_usage",
        f'clerk_user_id="{clerk_user_id}" && month="{month_key}"',
    )

    if existing:
        await pb_update("user_usage", existing["id"], {
            "count": existing["count"] + 1,
        })
    else:
        await pb_create("user_usage", {
            "clerk_user_id": clerk_user_id,
            "month": month_key,
            "count": 1,
        })


async def get_job(job_id: str, clerk_user_id: str) -> dict | None:
    job = await pb_get("summary_jobs", job_id)
    if not job or job["clerk_user_id"] != clerk_user_id:
        return None
    return job


async def get_user_jobs(clerk_user_id: str, page: int = 1, per_page: int = 20) -> list[dict]:
    result = await pb_list(
        "summary_jobs",
        filter=f'clerk_user_id="{clerk_user_id}"',
        sort="-created",
        page=page,
        per_page=per_page,
    )
    return result.get("items", [])


async def get_usage(clerk_user_id: str) -> dict:
    profile = await pb_get_first("user_profiles", f'clerk_user_id="{clerk_user_id}"')
    plan = profile["plan"] if profile else "free"

    now = datetime.now(timezone.utc)
    month_key = f"{now.year}-{now.month:02d}"

    usage_record = await pb_get_first(
        "user_usage",
        f'clerk_user_id="{clerk_user_id}" && month="{month_key}"',
    )
    count = usage_record["count"] if usage_record else 0

    return {
        "clerk_user_id": clerk_user_id,
        "summaries_this_month": count,
        "summaries_limit": PLAN_LIMITS.get(plan, 5),
        "plan": plan,
    }


async def delete_job(job_id: str, clerk_user_id: str) -> bool:
    job = await pb_get("summary_jobs", job_id)
    if not job or job["clerk_user_id"] != clerk_user_id:
        return False
    await pb_delete("summary_jobs", job_id)
    return True
