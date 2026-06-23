import os
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

from app.api import summaries, webhooks, health, billing
from app.db.firestore_client import init_firestore

# Rate limiter — uses IP by default, can be extended to use user_id
limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_firestore()
    yield


# ENVIRONMENT is canonical; NODE_ENV and ENV accepted for legacy compatibility
is_production = (
    os.environ.get("ENVIRONMENT") == "production"
    or os.environ.get("NODE_ENV") == "production"
    or os.environ.get("ENV") == "production"
)

app = FastAPI(
    title="ResumidorAI API",
    description="Resume videos de YouTube con IA",
    version="1.1.0",
    lifespan=lifespan,
    docs_url=None if is_production else "/docs",
    redoc_url=None,
)

# Rate limiting middleware
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

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
