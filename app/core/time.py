import datetime


def utcnow() -> datetime.datetime:
    """Naive UTC now.

    Naive on purpose: SQLite has no native tz support, and mixing
    naive/aware datetimes on comparison raises TypeError. Every
    timestamp in this codebase is UTC by convention instead.
    """
    return datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
