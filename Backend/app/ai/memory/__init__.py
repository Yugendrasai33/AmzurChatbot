from app.core.config import settings


def trim_history(history: list[dict], window_size: int | None = None) -> list[dict]:
    """Return the last *window_size* conversation exchanges from *history*.

    Each exchange is one user message + one assistant response (2 messages).
    The returned list keeps chronological order (oldest first).

    Args:
        history: Full list of message dicts with at least a ``role`` key,
                 ordered oldest-first.
        window_size: Number of exchanges to keep.  Defaults to
                     ``settings.MEMORY_WINDOW_SIZE``.

    Returns:
        A (possibly shorter) list containing at most ``window_size * 2``
        messages from the tail of *history*.
    """
    if not history:
        return []

    if window_size is None:
        window_size = settings.MEMORY_WINDOW_SIZE

    max_messages = window_size * 2
    if len(history) <= max_messages:
        return list(history)

    return list(history[-max_messages:])
