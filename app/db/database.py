from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import get_settings

settings = get_settings()

_connect_args = (
    {"check_same_thread": False}
    if settings.database_url.startswith("sqlite")
    else {}
)

engine = create_engine(settings.database_url, connect_args=_connect_args)
SessionLocal = sessionmaker(
    bind=engine, autoflush=False, autocommit=False, expire_on_commit=False
)


class Base(DeclarativeBase):
    pass


def init_db() -> None:
    # Import each provider's token model so it's registered on
    # Base.metadata before create_all. The local DB only stores
    # OAuth tokens - Zoho/Shopify are the source of truth for
    # business data, so there are no other tables to import here.
    import app.modules.shopify.auth.models  # noqa: F401
    import app.modules.zoho.auth.models  # noqa: F401

    Base.metadata.create_all(bind=engine)
