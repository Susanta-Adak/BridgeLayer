"""Local mirror of Demo Contacts, same shape as every other module's

models.py - proof that a new provider's local-persistence story
replicates with zero changes to anything outside its own folder.
"""

import datetime

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.time import utcnow
from app.db.database import Base


class DemoContact(Base):
    __tablename__ = "demo_contacts"

    id: Mapped[int] = mapped_column(primary_key=True)
    external_id: Mapped[str] = mapped_column(
        String(64), unique=True, index=True
    )
    first_name: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    last_name: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    company: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )
