import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

from app.api import summaries, webhooks, health, billing
from app.db.firestore_client import init_pocketbase


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_pocketbase()
    yield


app = FastAPI(
    title="ResumidorAI API",
    description="Resume videos de YouTube con IA",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url=None,
)

origins = [o.strip() for o in os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(summaries.router, prefix="/api/summaries", tags=["summaries"])
app.include_router(webhooks.router, prefix="/api/webhooks", tags=["webhooks"])
app.include_router(billing.router, prefix="/api/billing", tags=["billing"])
