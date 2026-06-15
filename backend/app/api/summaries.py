from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from app.models.schemas import SummaryRequest, SummaryResponse, SummaryResult, UsageStats, JobStatus
from app.services.job_processor import create_job, process_job, get_job, get_user_jobs, get_usage
from app.auth.clerk import get_current_user
from datetime import datetime, timezone

router = APIRouter()


@router.post("", response_model=SummaryResponse, status_code=202)
async def submit_summary(
    request: SummaryRequest,
    background_tasks: BackgroundTasks,
    user: dict = Depends(get_current_user),
):
    """Envía un video para resumir. Procesamiento async en background."""
    user_id = user["user_id"]

    # Verificar límite de uso
    usage = await get_usage(user_id)
    if usage["summaries_this_month"] >= usage["summaries_limit"]:
        raise HTTPException(
            status_code=429,
            detail=f"Límite mensual alcanzado ({usage['summaries_limit']} resúmenes). Actualiza tu plan.",
        )

    # Crear job
    job_id = await create_job(user_id=user_id, request=request)

    # Procesar en background
    background_tasks.add_task(process_job, job_id)

    return SummaryResponse(
        job_id=job_id,
        status=JobStatus.pending,
        created_at=datetime.now(timezone.utc),
    )


@router.get("/{job_id}", response_model=SummaryResult)
async def get_summary(
    job_id: str,
    user: dict = Depends(get_current_user),
):
    """Obtiene el resultado de un resumen por job_id."""
    job = await get_job(job_id=job_id, user_id=user["user_id"])

    if not job:
        raise HTTPException(status_code=404, detail="Resumen no encontrado")

    return SummaryResult(**job)


@router.get("", response_model=list[SummaryResult])
async def list_summaries(
    limit: int = Query(default=20, le=100),
    offset: int = Query(default=0),
    user: dict = Depends(get_current_user),
):
    """Lista todos los resúmenes del usuario."""
    jobs = await get_user_jobs(
        user_id=user["user_id"],
        limit=limit,
        offset=offset,
    )
    return [SummaryResult(**j) for j in jobs]


@router.get("/usage/me", response_model=UsageStats)
async def get_my_usage(user: dict = Depends(get_current_user)):
    """Devuelve el uso actual del usuario este mes."""
    return await get_usage(user["user_id"])


@router.delete("/{job_id}", status_code=204)
async def delete_summary(
    job_id: str,
    user: dict = Depends(get_current_user),
):
    """Elimina un resumen del historial."""
    from app.db.supabase import get_db
    db = get_db()
    result = db.table("summary_jobs").delete().eq("id", job_id).eq("user_id", user["user_id"]).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="No encontrado")
