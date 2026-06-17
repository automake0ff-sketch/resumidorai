"""
Pipeline de procesamiento de jobs usando PocketBase.
"""
import logging
from datetime import datetime, timezone
from app.db.pocketbase import pb_create, pb_update, pb_get, pb_get_first, pb_list, pb_delete, pb_upsert
from app.services.youtube import youtube_service
from app.agents.summary_agent import VideoSummaryOrchestrator
from app.models.schemas import JobStatus, SummaryRequest

logger = logging.getLogger(__name__)
orchestrator = VideoSummaryOrchestrator()

from app.services.stripe_service import PLAN_LIMITS


def _esc(value: str) -> str:
    """Escapa comillas para uso seguro en filtros de PocketBase."""
    return value.replace('"', '\\"')


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


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
    logger.info(f"Processing job {job_id}")
    try:
        await pb_update("summary_jobs", job_id, {
            "status": JobStatus.processing,
            "started_at": _now(),
        })

        job = await pb_get("summary_jobs", job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")

        video_id = youtube_service.extract_video_id(job["url"])
        if not video_id:
            raise ValueError(f"URL no válida: {job['url']}")

        metadata = await youtube_service.get_metadata(video_id)
        transcript_data = youtube_service.get_transcript(video_id, job["language"])

        # La YouTube Data API da la duración real del video (más fiable que
        # calcularla desde el último timestamp de la transcripción, que puede
        # quedarse corto si el video tiene silencio o créditos al final).
        duration_seconds = metadata.get("duration_seconds_hint") or transcript_data["duration_seconds"]

        ai_result = await orchestrator.process(
            raw_transcript=transcript_data["raw"],
            transcript_with_timestamps=transcript_data["with_timestamps"],
            title=metadata["title"],
            duration_seconds=duration_seconds,
            language=job["language"],
            length=job["length"],
            include_key_points=job.get("include_key_points", True),
            include_chapters=job.get("include_chapters", True),
        )

        update_data: dict = {
            "status": JobStatus.completed,
            "title": metadata["title"],
            "thumbnail": metadata["thumbnail"],
            "duration_seconds": duration_seconds,
            "summary": ai_result["summary"],
            "key_points": ai_result["key_points"],
            "chapters": ai_result["chapters"],
            "completed_at": _now(),
        }

        if job.get("include_transcript"):
            update_data["transcript"] = transcript_data["raw"]

        await pb_update("summary_jobs", job_id, update_data)
        await _increment_usage(job["clerk_user_id"])
        logger.info(f"Job {job_id} completed successfully")

    except Exception as e:
        logger.error(f"Job {job_id} failed: {e}", exc_info=True)
        try:
            await pb_update("summary_jobs", job_id, {
                "status": JobStatus.failed,
                "error": str(e)[:500],
                "completed_at": _now(),
            })
        except Exception as update_err:
            logger.error(f"Failed to update job status: {update_err}")


async def _increment_usage(clerk_user_id: str):
    now = datetime.now(timezone.utc)
    month_key = f"{now.year}-{now.month:02d}"
    existing = await pb_get_first(
        "user_usage",
        f'clerk_user_id="{_esc(clerk_user_id)}"&&month="{month_key}"',
    )
    if existing:
        await pb_update("user_usage", existing["id"], {"count": existing.get("count", 0) + 1})
    else:
        await pb_create("user_usage", {"clerk_user_id": clerk_user_id, "month": month_key, "count": 1})


async def get_job(job_id: str, clerk_user_id: str) -> dict | None:
    job = await pb_get("summary_jobs", job_id)
    if not job or job.get("clerk_user_id") != clerk_user_id:
        return None
    return job


async def get_user_jobs(clerk_user_id: str, page: int = 1, per_page: int = 20) -> list[dict]:
    result = await pb_list(
        "summary_jobs",
        filter=f'clerk_user_id="{_esc(clerk_user_id)}"',
        sort="-created",
        page=page,
        per_page=per_page,
    )
    return result.get("items", [])


async def get_usage(clerk_user_id: str) -> dict:
    profile = await pb_get_first("user_profiles", f'clerk_user_id="{_esc(clerk_user_id)}"')
    plan = profile.get("plan", "trial") if profile else "trial"

    now = datetime.now(timezone.utc)
    month_key = f"{now.year}-{now.month:02d}"
    usage_record = await pb_get_first(
        "user_usage",
        f'clerk_user_id="{_esc(clerk_user_id)}"&&month="{month_key}"',
    )
    count = usage_record.get("count", 0) if usage_record else 0

    return {
        "summaries_this_month": count,
        "summaries_limit": PLAN_LIMITS.get(plan, 0),
        "plan": plan,
    }


async def delete_job(job_id: str, clerk_user_id: str) -> bool:
    job = await pb_get("summary_jobs", job_id)
    if not job or job.get("clerk_user_id") != clerk_user_id:
        return False
    await pb_delete("summary_jobs", job_id)
    return True


async def ensure_user_profile(clerk_user_id: str, email: str = "", name: str = ""):
    """Create user profile if it doesn't exist (fallback for webhook failures)."""
    existing = await pb_get_first("user_profiles", f'clerk_user_id="{_esc(clerk_user_id)}"')
    if not existing:
        await pb_create("user_profiles", {
            "clerk_user_id": clerk_user_id,
            "email": email,
            "name": name,
            "plan": "trial",
        })
