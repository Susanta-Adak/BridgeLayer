from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.exceptions import register_exception_handlers
from app.core.http_client import close_http_client
from app.core.logging import configure_logging
from app.db.database import init_db
from app.modules.shopify.auth.router import router as shopify_auth_router
from app.modules.shopify.customers.router import (
    router as shopify_customers_router,
)
from app.modules.shopify.orders.router import (
    router as shopify_orders_router,
)
from app.modules.shopify.webhooks import router as shopify_webhooks_router
from app.modules.zoho.auth.router import router as zoho_auth_router
from app.modules.zoho.contacts.router import router as zoho_contacts_router
from app.modules.zoho.leads.router import router as zoho_leads_router


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

app.include_router(zoho_auth_router)
app.include_router(zoho_contacts_router)
app.include_router(zoho_leads_router)
app.include_router(shopify_auth_router)
app.include_router(shopify_customers_router)
app.include_router(shopify_orders_router)
app.include_router(shopify_webhooks_router)


@app.get("/health", tags=["health"])
async def health():
    return {"success": True, "data": {"status": "ok"}, "error": None}
