"""
Servicio de procesamiento de trabajos de resumen.
Maneja el ciclo completo: crear job → procesar → guardar resultado.
"""

import uuid
from datetime import datetime, timezone
from app.db.supabase import get_db
from app.services.youtube import youtube_service
from app.agents.summary_agent import VideoSummaryOrchestrator
from app.models.schemas import JobStatus, SummaryRequest


orchestrator = VideoSummaryOrchestrator()


async def create_job(user_id: str, request: SummaryRequest) -> str:
    """Crea un job en Supabase y devuelve el job_id."""
    db = get_db()
    job_id = str(uuid.uuid4())

    db.table("summary_jobs").insert({
        "id": job_id,
        "user_id": user_id,
        "url": request.url,
        "language": request.language,
        "length": request.length,
        "include_chapters": request.include_chapters,
        "include_key_points": request.include_key_points,
        "include_transcript": request.include_transcript,
        "status": JobStatus.pending,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }).execute()

    return job_id


async def process_job(job_id: str):
    """
    Procesamiento completo de un job (ejecutar en background).
    1. Marca como processing
    2. Extrae datos del video
    3. Corre agentes IA
    4. Guarda resultados
    """
    db = get_db()

    try:
        # Marcar como procesando
        db.table("summary_jobs").update({
            "status": JobStatus.processing,
            "started_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", job_id).execute()

        # Obtener datos del job
        result = db.table("summary_jobs").select("*").eq("id", job_id).single().execute()
        job = result.data

        # Extraer datos del video
        video_id = youtube_service.extract_video_id(job["url"])
        if not video_id:
            raise ValueError(f"URL no válida: {job['url']}")

        metadata = await youtube_service.get_metadata(video_id)
        transcript_data = youtube_service.get_transcript(video_id, job["language"])

        # Procesar con agentes IA
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

        # Guardar resultado exitoso
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

        db.table("summary_jobs").update(update_data).eq("id", job_id).execute()

        # Incrementar uso del usuario
        _increment_usage(user_id=job["user_id"])

    except Exception as e:
        db.table("summary_jobs").update({
            "status": JobStatus.failed,
            "error": str(e),
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", job_id).execute()
        raise


def _increment_usage(user_id: str):
    db = get_db()
    now = datetime.now(timezone.utc)
    month_key = f"{now.year}-{now.month:02d}"

    # Upsert en tabla de uso
    db.table("user_usage").upsert({
        "user_id": user_id,
        "month": month_key,
        "count": 1,
    }, on_conflict="user_id,month", count="exact").execute()

    # También podría usarse una función RPC de Supabase para incremento atómico
    db.rpc("increment_usage", {"p_user_id": user_id, "p_month": month_key}).execute()


async def get_job(job_id: str, user_id: str) -> dict | None:
    db = get_db()
    result = (
        db.table("summary_jobs")
        .select("*")
        .eq("id", job_id)
        .eq("user_id", user_id)
        .single()
        .execute()
    )
    return result.data


async def get_user_jobs(user_id: str, limit: int = 20, offset: int = 0) -> list[dict]:
    db = get_db()
    result = (
        db.table("summary_jobs")
        .select("id, status, url, title, thumbnail, duration_seconds, created_at, completed_at, length, language")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .range(offset, offset + limit - 1)
        .execute()
    )
    return result.data


async def get_usage(user_id: str) -> dict:
    db = get_db()
    now = datetime.now(timezone.utc)
    month_key = f"{now.year}-{now.month:02d}"

    # Obtener plan del usuario
    profile = db.table("user_profiles").select("plan").eq("user_id", user_id).single().execute()
    plan = profile.data.get("plan", "free") if profile.data else "free"

    limits = {"free": 5, "starter": 50, "pro": 200, "unlimited": 99999}

    usage = db.table("user_usage").select("count").eq("user_id", user_id).eq("month", month_key).single().execute()
    count = usage.data.get("count", 0) if usage.data else 0

    return {
        "user_id": user_id,
        "summaries_this_month": count,
        "summaries_limit": limits.get(plan, 5),
        "plan": plan,
    }
