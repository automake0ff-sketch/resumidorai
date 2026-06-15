from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.api import summaries, webhooks, health
from app.db.supabase import init_supabase


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_supabase()
    yield


app = FastAPI(
    title="VideoSummary AI API",
    description="SaaS para resumir videos con IA",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En prod: tu dominio Vercel
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(summaries.router, prefix="/api/summaries", tags=["summaries"])
app.include_router(webhooks.router, prefix="/api/webhooks", tags=["webhooks"])
