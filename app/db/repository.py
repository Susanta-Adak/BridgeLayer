"""Generic local-mirror persistence for provider records.

Every service module (zoho_service, shopify_service, ...) calls
these functions after a successful create/update/delete against the
third party, so BridgeLayer keeps its own durable copy instead of
only trusting the provider's copy. Kept generic across (provider,
resource_type) so a new provider's Facade needs zero changes here -
it just calls the same three functions.
"""

from app.db.models import IntegrationRecord
from app.db.session import SessionLocal


def _query(db, provider: str, resource_type: str, external_id: str):
    return db.query(IntegrationRecord).filter(
        IntegrationRecord.provider == provider,
        IntegrationRecord.resource_type == resource_type,
        IntegrationRecord.external_id == external_id,
    )


def upsert_record(
    provider: str, resource_type: str, external_id: str, data: dict
) -> IntegrationRecord:
    with SessionLocal() as db:
        record = _query(db, provider, resource_type, external_id).first()
        if record is None:
            record = IntegrationRecord(
                provider=provider,
                resource_type=resource_type,
                external_id=external_id,
            )
            db.add(record)

        record.data = data
        record.is_deleted = False

        db.commit()
        db.refresh(record)
        return record


def mark_deleted(provider: str, resource_type: str, external_id: str) -> None:
    with SessionLocal() as db:
        record = _query(db, provider, resource_type, external_id).first()
        if record is not None:
            record.is_deleted = True
            db.commit()


def get_record(
    provider: str, resource_type: str, external_id: str
) -> IntegrationRecord | None:
    with SessionLocal() as db:
        return _query(db, provider, resource_type, external_id).first()
