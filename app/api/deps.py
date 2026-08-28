"""Small shared helpers for building the response envelope."""

from typing import Any


def envelope(data: Any) -> dict:
    return {"success": True, "data": data, "error": None}
