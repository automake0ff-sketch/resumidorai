from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from app.models.schemas import SummaryRequest, SummaryResponse, SummaryResult, UsageStats, JobStatus
from app.services.job_processor import create_job, process_job, get_job, get_user_jobs, get_usage, delete_job
from app.auth.clerk import get_current_user

router = APIRouter()


def _map_job(job: dict) -> SummaryResult:
    return SummaryResult(
        job_id=job["id"],
        status=job["status"],
        url=job["url"],
        title=job.get("title"),
        thumbnail=job.get("thumbnail"),
        duration_seconds=job.get("duration_seconds"),
        summary=job.get("summary"),
        key_points=job.get("key_points"),
        chapters=job.get("chapters"),
        transcript=job.get("transcript"),
        language=job.get("language", "es"),
        error=job.get("error"),
        created=job.get("created"),
        completed_at=job.get("completed_at"),
    )


@router.post("", response_model=SummaryResponse, status_code=202)
async def submit_summary(
    request: SummaryRequest,
    background_tasks: BackgroundTasks,
    user: dict = Depends(get_current_user),
):
    usage = await get_usage(user["user_id"])
    if usage["summaries_this_month"] >= usage["summaries_limit"]:
        raise HTTPException(
            status_code=429,
            detail=f"Límite mensual alcanzado ({usage['summaries_limit']}). Actualiza tu plan.",
        )
    job_id = await create_job(clerk_user_id=user["user_id"], request=request)
    background_tasks.add_task(process_job, job_id)
    return SummaryResponse(job_id=job_id, status=JobStatus.pending)


@router.get("/usage/me", response_model=UsageStats)
async def get_my_usage(user: dict = Depends(get_current_user)):
    return await get_usage(user["user_id"])


@router.get("/{job_id}", response_model=SummaryResult)
async def get_summary(job_id: str, user: dict = Depends(get_current_user)):
    job = await get_job(job_id=job_id, clerk_user_id=user["user_id"])
    if not job:
        raise HTTPException(status_code=404, detail="No encontrado")
    return _map_job(job)


@router.get("", response_model=list[SummaryResult])
async def list_summaries(
    page: int = Query(default=1),
    per_page: int = Query(default=20, le=100),
    user: dict = Depends(get_current_user),
):
    jobs = await get_user_jobs(clerk_user_id=user["user_id"], page=page, per_page=per_page)
    return [_map_job(j) for j in jobs]


@router.delete("/{job_id}", status_code=204)
async def delete_summary(job_id: str, user: dict = Depends(get_current_user)):
    deleted = await delete_job(job_id=job_id, clerk_user_id=user["user_id"])
    if not deleted:
        raise HTTPException(status_code=404, detail="No encontrado")
