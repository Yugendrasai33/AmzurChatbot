from __future__ import annotations

import re

from app.core.config import settings

_BLOCKED_KEYWORDS: list[str] = [
    "INSERT",
    "UPDATE",
    "DELETE",
    "DROP",
    "TRUNCATE",
    "ALTER",
]

_BLOCKED_PATTERN = re.compile(
    r"\b(?:" + "|".join(_BLOCKED_KEYWORDS) + r")\b",
    re.IGNORECASE,
)


def get_allowed_tables() -> list[str]:
    """Return the list of tables users are permitted to query."""
    return [t.strip() for t in settings.SQL_QUERY_ALLOWED_TABLES.split(",") if t.strip()]


ALLOWED_TABLES: list[str] = get_allowed_tables()


def is_table_allowed(table_name: str) -> bool:
    """Check whether *table_name* is in the allowed-tables list."""
    return table_name.strip().lower() in [t.lower() for t in ALLOWED_TABLES]


def validate_sql(query: str) -> str:
    """Validate that *query* contains no write operations.

    Returns the query unchanged if safe.
    Raises ``ValueError`` if a blocked keyword is detected.
    """
    match = _BLOCKED_PATTERN.search(query)
    if match:
        raise ValueError(
            f"Write operations are not allowed. "
            f"Blocked keyword detected: {match.group().upper()}"
        )
    return query
