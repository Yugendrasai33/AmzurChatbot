"""AI Agent for Tic Tac Toe using LiteLLM for move reasoning."""

import json
import re
from typing import Any

from app.ai.llm import llm

SYSTEM_PROMPT = """\
You are an intelligent Tic Tac Toe AI agent playing as "O" against a human who plays "X".

RULES:
- The board is a 3x3 grid. Rows and columns are 0-indexed (0, 1, 2).
- A cell is empty if its value is "" (empty string).
- You can ONLY place your mark in an empty cell.
- You must NEVER choose a cell that already has "X" or "O".

STRATEGY (in order of priority):
1. WIN: If you can win this turn, take the winning move.
2. BLOCK: If the opponent can win next turn, block them.
3. CENTER: If the center (1,1) is open, take it.
4. CORNERS: Prefer open corners (0,0), (0,2), (2,0), (2,2).
5. EDGES: Take any remaining open edge.

RESPONSE FORMAT:
You MUST respond with ONLY a JSON object, no extra text:
{"row": <0-2>, "col": <0-2>, "reason": "<brief explanation>"}
"""


def _board_to_text(board: list[list[str]]) -> str:
    """Convert board matrix to readable text for the LLM."""
    lines = []
    for r, row in enumerate(board):
        cells = []
        for c, cell in enumerate(row):
            if cell == "":
                cells.append(f"({r},{c}):empty")
            else:
                cells.append(f"({r},{c}):{cell}")
        lines.append(" | ".join(cells))
    return "\n".join(lines)


def _get_empty_cells(board: list[list[str]]) -> list[tuple[int, int]]:
    """Return list of (row, col) for empty cells."""
    empty = []
    for r in range(3):
        for c in range(3):
            if board[r][c] == "":
                empty.append((r, c))
    return empty


def _parse_ai_response(text: str) -> dict[str, Any] | None:
    """Parse the LLM JSON response, tolerant of markdown fences."""
    text = text.strip()
    # Strip markdown code fences if present
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    # Try direct JSON parse
    try:
        data = json.loads(text)
        if "row" in data and "col" in data:
            return data
    except json.JSONDecodeError:
        pass
    # Try to find JSON object in text
    match = re.search(r'\{[^{}]*"row"\s*:\s*\d[^{}]*"col"\s*:\s*\d[^{}]*\}', text)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return None


def _fallback_move(board: list[list[str]]) -> dict[str, Any]:
    """Deterministic fallback: pick first valid cell with basic strategy."""
    empty = _get_empty_cells(board)
    if not empty:
        return {"row": -1, "col": -1, "reason": "No moves available"}

    # Check for winning move for O
    for r, c in empty:
        board[r][c] = "O"
        if _check_winner(board) == "O":
            board[r][c] = ""
            return {"row": r, "col": c, "reason": "Winning move (fallback)"}
        board[r][c] = ""

    # Block X from winning
    for r, c in empty:
        board[r][c] = "X"
        if _check_winner(board) == "X":
            board[r][c] = ""
            return {"row": r, "col": c, "reason": "Blocking opponent (fallback)"}
        board[r][c] = ""

    # Center, corners, edges
    priority = [(1, 1), (0, 0), (0, 2), (2, 0), (2, 2), (0, 1), (1, 0), (1, 2), (2, 1)]
    for r, c in priority:
        if (r, c) in empty:
            return {"row": r, "col": c, "reason": "Strategic position (fallback)"}

    r, c = empty[0]
    return {"row": r, "col": c, "reason": "First available (fallback)"}


def _check_winner(board: list[list[str]]) -> str | None:
    """Check if there is a winner. Returns 'X', 'O', or None."""
    lines = []
    for i in range(3):
        lines.append([board[i][0], board[i][1], board[i][2]])  # rows
        lines.append([board[0][i], board[1][i], board[2][i]])  # cols
    lines.append([board[0][0], board[1][1], board[2][2]])  # diag
    lines.append([board[0][2], board[1][1], board[2][0]])  # anti-diag
    for line in lines:
        if line[0] != "" and line[0] == line[1] == line[2]:
            return line[0]
    return None


async def get_ai_move(
    board: list[list[str]],
    difficulty: str = "hard",
    max_retries: int = 3,
) -> dict[str, Any]:
    """
    Ask the LLM agent to decide the next move for 'O'.

    Returns dict with keys: row, col, reason
    """
    empty_cells = _get_empty_cells(board)
    if not empty_cells:
        return {"row": -1, "col": -1, "reason": "No moves available"}

    board_text = _board_to_text(board)
    empty_text = ", ".join(f"({r},{c})" for r, c in empty_cells)

    user_msg = (
        f"Current board state:\n{board_text}\n\n"
        f"Empty cells available: {empty_text}\n\n"
        f"It's your turn (O). Pick the best move. "
        f"Respond with ONLY the JSON object."
    )

    if difficulty == "easy":
        user_msg += "\nPlay at a beginner level — make occasional suboptimal moves."
    elif difficulty == "medium":
        user_msg += "\nPlay at an intermediate level — generally good but not always perfect."

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_msg},
    ]

    for attempt in range(max_retries):
        try:
            response = await llm.ainvoke(messages)
            content = response.content if hasattr(response, "content") else str(response)
            parsed = _parse_ai_response(content)

            if parsed is not None:
                row = int(parsed["row"])
                col = int(parsed["col"])
                reason = parsed.get("reason", "AI move")

                # Validate the move
                if 0 <= row <= 2 and 0 <= col <= 2 and board[row][col] == "":
                    return {"row": row, "col": col, "reason": str(reason)}

            # If invalid, add correction message and retry
            messages.append({"role": "assistant", "content": content})
            messages.append({
                "role": "user",
                "content": (
                    f"Invalid move. The cell must be empty. "
                    f"Available empty cells: {empty_text}. "
                    f"Respond with ONLY the JSON object."
                ),
            })
        except Exception:
            continue

    # All retries exhausted — use deterministic fallback
    return _fallback_move(board)
