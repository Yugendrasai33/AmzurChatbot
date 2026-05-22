"""Tic Tac Toe game tool — wraps the existing get_ai_move function."""
from __future__ import annotations

from typing import Any


async def execute_game_move(
    board: list[list[str]],
    difficulty: str = "hard",
) -> dict[str, Any]:
    """Get AI move for Tic Tac Toe.

    Args:
        board: 3x3 board state (list of lists with "", "X", or "O")
        difficulty: "easy", "medium", or "hard"

    Returns:
        dict with keys: success, row, col, reason
    """
    # Validate board structure
    if not board or len(board) != 3:
        return {"success": False, "error": "Board must be a 3x3 grid"}

    for row in board:
        if not isinstance(row, list) or len(row) != 3:
            return {"success": False, "error": "Board must be a 3x3 grid"}
        for cell in row:
            if cell not in ("", "X", "O"):
                return {"success": False, "error": f"Invalid cell value: '{cell}'. Must be '', 'X', or 'O'"}

    if difficulty not in ("easy", "medium", "hard"):
        return {"success": False, "error": f"Invalid difficulty: '{difficulty}'. Must be 'easy', 'medium', or 'hard'"}

    try:
        from app.agents.tic_tac_toe_agent import get_ai_move

        result = await get_ai_move(board=board, difficulty=difficulty)
        return {
            "success": True,
            "row": result["row"],
            "col": result["col"],
            "reason": result.get("reason", "AI move"),
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Game move failed: {e}",
        }
