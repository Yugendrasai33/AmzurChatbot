import pytest

from app.ai.memory import trim_history


def _make_exchange(index: int) -> list[dict]:
    """Return a user+assistant pair for a given index."""
    return [
        {"role": "user", "content": f"user message {index}"},
        {"role": "assistant", "content": f"assistant message {index}"},
    ]


def _make_history(n_exchanges: int) -> list[dict]:
    """Build a chronological history of *n_exchanges* pairs."""
    history: list[dict] = []
    for i in range(1, n_exchanges + 1):
        history.extend(_make_exchange(i))
    return history


# ── empty history ────────────────────────────────────────────────────
def test_empty_history():
    assert trim_history([], window_size=5) == []


# ── fewer than window_size exchanges ─────────────────────────────────
@pytest.mark.parametrize("n", [1, 2, 3, 4])
def test_fewer_than_window(n: int):
    history = _make_history(n)
    result = trim_history(history, window_size=5)
    assert result == history


# ── exactly window_size exchanges ────────────────────────────────────
def test_exactly_window_size():
    history = _make_history(5)
    result = trim_history(history, window_size=5)
    assert result == history
    assert len(result) == 10


# ── more than window_size exchanges ──────────────────────────────────
def test_more_than_window():
    history = _make_history(8)
    result = trim_history(history, window_size=5)
    assert len(result) == 10
    # Should contain exchanges 4-8 (last 5)
    assert result[0] == {"role": "user", "content": "user message 4"}
    assert result[-1] == {"role": "assistant", "content": "assistant message 8"}


# ── odd number of messages (incomplete pair) ─────────────────────────
def test_odd_messages():
    history = _make_history(6)
    # Remove last assistant message → 11 messages total
    history = history[:-1]
    assert len(history) == 11
    result = trim_history(history, window_size=5)
    assert len(result) == 10
    assert result[-1] == {"role": "user", "content": "user message 6"}


# ── window_size=1 returns only the last pair ─────────────────────────
def test_window_size_one():
    history = _make_history(5)
    result = trim_history(history, window_size=1)
    assert len(result) == 2
    assert result[0] == {"role": "user", "content": "user message 5"}
    assert result[1] == {"role": "assistant", "content": "assistant message 5"}


# ── chronological order preserved ────────────────────────────────────
def test_chronological_order():
    history = _make_history(10)
    result = trim_history(history, window_size=5)
    for i in range(len(result) - 1):
        # user messages come before their paired assistant messages
        if result[i]["role"] == "user":
            assert result[i + 1]["role"] == "assistant"


# ── original list not mutated ────────────────────────────────────────
def test_original_not_mutated():
    history = _make_history(8)
    original_len = len(history)
    trim_history(history, window_size=5)
    assert len(history) == original_len
