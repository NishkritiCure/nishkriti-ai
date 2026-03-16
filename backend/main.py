import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from dotenv import load_dotenv

load_dotenv()  # loads backend/.env before any module imports env vars

from routers.webhooks import router as webhooks_router
from utils.logging import get_logger

logger = get_logger(__name__)

REQUIRED_ENV_VARS = ["SUPABASE_URL", "SUPABASE_KEY", "EXOTEL_WEBHOOK_SECRET"]


@asynccontextmanager
async def lifespan(app: FastAPI):
    missing = [v for v in REQUIRED_ENV_VARS if not os.getenv(v)]
    if missing:
        raise RuntimeError(f"Missing required environment variables: {missing}")
    logger.info("startup_complete")
    yield
    logger.info("shutdown")


app = FastAPI(title="Nishkriti AI", version="0.1.0", lifespan=lifespan)
app.include_router(webhooks_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
