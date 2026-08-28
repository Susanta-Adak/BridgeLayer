"""Logging setup. Redacts token-shaped values so secrets never land

in log output, even if a provider response is logged for debugging.
"""

import logging
import re

from app.core.config import get_settings

_REDACT_KEYS = re.compile(
    r'("(?:access_token|refresh_token|api_key|client_secret|'
    r'authorization|password)"\s*:\s*")([^"]*)(")',
    re.IGNORECASE,
)


class RedactingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = _REDACT_KEYS.sub(r"\1***REDACTED***\3", record.msg)
        return True


def configure_logging() -> None:
    settings = get_settings()
    handler = logging.StreamHandler()
    handler.addFilter(RedactingFilter())
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s %(levelname)s %(name)s: %(message)s"
        )
    )

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(settings.log_level.upper())

    # Quiet down noisy third-party loggers by default.
    logging.getLogger("httpx").setLevel(logging.WARNING)
