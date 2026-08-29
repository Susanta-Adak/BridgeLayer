from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api_v1 import router as api_v1_router
from app.core.exceptions import register_exception_handlers
from app.core.http_client import close_http_client
from app.core.logging import configure_logging
from app.db.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    init_db()
    yield
    await close_http_client()


app = FastAPI(
    title="BridgeLayer",
    description=(
        "Unified integration layer connecting Zoho CRM and Shopify "
        "through a single API."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

register_exception_handlers(app)

app.include_router(api_v1_router)


@app.get("/health", tags=["health"])
async def health():
    return {"success": True, "data": {"status": "ok"}, "error": None}
