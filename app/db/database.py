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
    # Import every module's models so they're registered on
    # Base.metadata before create_all. Each provider module owns its
    # own tables (auth token + one per resource) - add the import
    # here whenever a new module gains a models.py.
    import app.modules.demo.contacts.models  # noqa: F401
    import app.modules.demo.leads.models  # noqa: F401
    import app.modules.shopify.auth.models  # noqa: F401
    import app.modules.shopify.customers.models  # noqa: F401
    import app.modules.shopify.orders.models  # noqa: F401
    import app.modules.zoho.auth.models  # noqa: F401
    import app.modules.zoho.contacts.models  # noqa: F401
    import app.modules.zoho.leads.models  # noqa: F401

    Base.metadata.create_all(bind=engine)
