import datetime

from sqlalchemy import JSON, Boolean, DateTime, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utcnow
from app.db.database import Base


class Token(Base):
    """OAuth / API credentials for a single provider.

    One row per provider name (e.g. "zoho", "shopify"). Shopify's
    offline access token never expires, so `expires_at` and
    `refresh_token` stay null for that row; Shopify falls back to a
    static env-configured token if no row exists yet.
    """

    __tablename__ = "tokens"
    __table_args__ = (UniqueConstraint("provider", name="uq_tokens_provider"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    provider: Mapped[str] = mapped_column(String(50), index=True)
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


class IntegrationRecord(Base):
    """Local mirror of every record BridgeLayer pushes to a provider.

    Every create/update/delete a service sends to Zoho or Shopify is
    also upserted here, keyed by (provider, resource_type,
    external_id), so this app keeps its own durable copy instead of
    only trusting the third party's. Deletes are soft (`is_deleted`)
    rather than removing the row, so the local copy still shows what
    used to exist there. Generic across providers/resource types on
    purpose: a new provider's service needs zero schema changes to
    get the same mirroring.
    """

    __tablename__ = "integration_records"
    __table_args__ = (
        UniqueConstraint(
            "provider",
            "resource_type",
            "external_id",
            name="uq_integration_records_identity",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    provider: Mapped[str] = mapped_column(String(50), index=True)
    resource_type: Mapped[str] = mapped_column(String(50), index=True)
    external_id: Mapped[str] = mapped_column(String(255), index=True)
    data: Mapped[dict] = mapped_column(JSON)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )
