# inventory/utils/safe_db.py
from __future__ import annotations

import logging
from typing import Any, Iterable, Optional

from django.db import DatabaseError, OperationalError, ProgrammingError

logger = logging.getLogger(__name__)


DB_SAFE_EXCEPTIONS = (
    OperationalError,
    DatabaseError,
    ProgrammingError,
    AttributeError,
)


def safe_get_profile(user: Any) -> Any | None:
    """
    Safely get user.profile without crashing the whole request when
    migrations/schema are incomplete.
    """
    if not user:
        return None

    try:
        if not getattr(user, "is_authenticated", False):
            return None
    except Exception:
        return None

    try:
        return getattr(user, "profile", None)
    except DB_SAFE_EXCEPTIONS as exc:
        logger.warning("safe_get_profile fallback due to DB/profile error: %s", exc)
        return None
    except Exception as exc:
        logger.exception("Unexpected safe_get_profile error: %s", exc)
        return None


def safe_count(qs, default: int = 0) -> int:
    try:
        return qs.count()
    except DB_SAFE_EXCEPTIONS as exc:
        logger.warning("safe_count fallback: %s", exc)
        return default
    except Exception as exc:
        logger.exception("Unexpected safe_count error: %s", exc)
        return default


def safe_exists(qs, default: bool = False) -> bool:
    try:
        return qs.exists()
    except DB_SAFE_EXCEPTIONS as exc:
        logger.warning("safe_exists fallback: %s", exc)
        return default
    except Exception as exc:
        logger.exception("Unexpected safe_exists error: %s", exc)
        return default


def safe_first(qs, default=None):
    try:
        return qs.first()
    except DB_SAFE_EXCEPTIONS as exc:
        logger.warning("safe_first fallback: %s", exc)
        return default
    except Exception as exc:
        logger.exception("Unexpected safe_first error: %s", exc)
        return default


def safe_list(qs_or_iterable: Any, limit: Optional[int] = None, default: Optional[list] = None) -> list:
    """
    Convert queryset or iterable to list safely.
    """
    if default is None:
        default = []

    try:
        if hasattr(qs_or_iterable, "__getitem__") and limit is not None:
            return list(qs_or_iterable[:limit])
        if limit is not None:
            out = []
            for idx, item in enumerate(qs_or_iterable):
                if idx >= limit:
                    break
                out.append(item)
            return out
        return list(qs_or_iterable)
    except DB_SAFE_EXCEPTIONS as exc:
        logger.warning("safe_list fallback: %s", exc)
        return default
    except Exception as exc:
        logger.exception("Unexpected safe_list error: %s", exc)
        return default


def safe_attr(obj: Any, attr: str, default: Any = None) -> Any:
    try:
        return getattr(obj, attr, default)
    except Exception:
        return default