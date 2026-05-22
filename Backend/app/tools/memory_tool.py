"""Memory retrieval tool — wraps the existing trim_history function."""
from __future__ import annotations

from typing import Any


def execute_memory_retrieve(
    history: list[dict[str, Any]],
    window_size: int = 5,
) -> dict[str, Any]:
    """Trim conversation history to the configured memory window.

    Args:
        history: List of message dicts with at least a 'role' key
        window_size: Number of exchanges to keep

    Returns:
        dict with keys: success, messages, count
    """
    if not isinstance(history, list):
        return {"success": False, "error": "History must be a list of message dicts"}

    if window_size < 1:
        return {"success": False, "error": "window_size must be at least 1"}

    try:
        from app.ai.memory import trim_history

        trimmed = trim_history(history, window_size=window_size)
        return {
            "success": True,
            "messages": trimmed,
            "count": len(trimmed),
            "original_count": len(history),
            "window_size": window_size,
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Memory retrieval failed: {e}",
        }
