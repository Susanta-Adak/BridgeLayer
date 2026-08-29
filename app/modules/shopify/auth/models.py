"""Local table for Shopify's OAuth token.

Shopify's offline access token never expires. The row simply
doesn't exist until OAuth completes; until then the module falls
back to a static env-configured token.
"""

import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utcnow
from app.db.database import Base


class ShopifyToken(Base):
    __tablename__ = "shopify_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    access_token: Mapped[str] = mapped_column(String(2048))
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )
