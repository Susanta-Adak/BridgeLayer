"""Local table for Zoho's OAuth token.

Single-tenant, so this is always a one-row table.
"""

import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utcnow
from app.db.database import Base


class ZohoToken(Base):
    __tablename__ = "zoho_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    access_token: Mapped[str] = mapped_column(String(2048))
    refresh_token: Mapped[str | None] = mapped_column(
        String(2048), nullable=True
    )
    expires_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )
