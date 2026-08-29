"""Local mirror of Shopify Orders BridgeLayer has read.

Orders are read-only in this API (Shopify is the only place an
order is created), so the local copy is populated on every list/get
rather than on a create/update - it's still "not just a pass-through
API call": once BridgeLayer has seen an order, it has its own record
of it.
"""

import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utcnow
from app.db.database import Base


class ShopifyOrder(Base):
    __tablename__ = "shopify_orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    external_id: Mapped[str] = mapped_column(
        String(64), unique=True, index=True
    )
    customer_external_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )
    customer_email: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    total_price: Mapped[str] = mapped_column(String(32))
    currency: Mapped[str] = mapped_column(String(8))
    order_status: Mapped[str] = mapped_column(String(50))
    order_created_at: Mapped[str] = mapped_column(String(64))
    synced_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )
