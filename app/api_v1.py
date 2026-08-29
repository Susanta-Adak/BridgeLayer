"""API v1 composition root.

Mounts every module's router under a single `/api/v1` prefix. Each
module's own router.py keeps its relative prefix (e.g.
`/zoho/contacts`) unchanged and stays independently testable/
importable - this file only adds the version prefix on top, so
introducing a v2 later means adding a sibling `api_v2.py` that
composes a different set of routers, not touching any module.

`/health` is intentionally NOT versioned (see main.py) - it's an
infra-level liveness check, not a business-data endpoint, and load
balancers/orchestrators expect a stable, unversioned path for it.
"""

from fastapi import APIRouter

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

router = APIRouter(prefix="/api/v1")

router.include_router(zoho_auth_router)
router.include_router(zoho_contacts_router)
router.include_router(zoho_leads_router)
router.include_router(shopify_auth_router)
router.include_router(shopify_customers_router)
router.include_router(shopify_orders_router)
router.include_router(shopify_webhooks_router)
