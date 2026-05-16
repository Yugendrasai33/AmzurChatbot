"""Game service — manages Tic Tac Toe state and orchestrates AI moves."""

import uuid
from datetime import datetime, timezone
from typing import Any

from app.agents.tic_tac_toe_agent import get_ai_move


def _empty_board() -> list[list[str]]:
    return [["", "", ""], ["", "", ""], ["", "", ""]]


def _check_winner(board: list[list[str]]) -> str | None:
    lines = []
    for i in range(3):
        lines.append([board[i][0], board[i][1], board[i][2]])
        lines.append([board[0][i], board[1][i], board[2][i]])
    lines.append([board[0][0], board[1][1], board[2][2]])
    lines.append([board[0][2], board[1][1], board[2][0]])
    for line in lines:
        if line[0] != "" and line[0] == line[1] == line[2]:
            return line[0]
    return None


def _is_draw(board: list[list[str]]) -> bool:
    return all(board[r][c] != "" for r in range(3) for c in range(3))


def _game_status(board: list[list[str]]) -> tuple[str, str | None]:
    """Returns (status_string, winner_or_none)."""
    winner = _check_winner(board)
    if winner == "X":
        return "X_wins", "X"
    if winner == "O":
        return "O_wins", "O"
    if _is_draw(board):
        return "draw", None
    return "in_progress", None


class GameService:
    """In-memory game state manager keyed by (user_id, game_id)."""

    def __init__(self) -> None:
        # {user_id: {game_id: game_dict}}
        self._games: dict[str, dict[str, dict[str, Any]]] = {}

    def _user_games(self, user_id: str) -> dict[str, dict[str, Any]]:
        if user_id not in self._games:
            self._games[user_id] = {}
        return self._games[user_id]

    def start_game(self, user_id: str, difficulty: str = "hard") -> dict[str, Any]:
        game_id = str(uuid.uuid4())
        board = _empty_board()
        game = {
            "game_id": game_id,
            "board": board,
            "current_turn": "X",
            "status": "in_progress",
            "winner": None,
            "move_number": 0,
            "difficulty": difficulty,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "finished_at": None,
            "move_history": [],
        }
        self._user_games(user_id)[game_id] = game
        return game

    def get_game(self, user_id: str, game_id: str) -> dict[str, Any] | None:
        return self._user_games(user_id).get(game_id)

    def _apply_move(
        self, game: dict[str, Any], row: int, col: int, player: str
    ) -> str | None:
        """Apply a move. Returns error string or None on success."""
        if game["status"] != "in_progress":
            return "Game is already finished"
        if game["current_turn"] != player:
            return f"Not {player}'s turn"
        if not (0 <= row <= 2 and 0 <= col <= 2):
            return "Move out of bounds"
        if game["board"][row][col] != "":
            return "Cell already occupied"

        game["board"][row][col] = player
        game["move_number"] += 1
        game["move_history"].append({"player": player, "row": row, "col": col})

        status, winner = _game_status(game["board"])
        game["status"] = status
        game["winner"] = winner
        if status != "in_progress":
            game["finished_at"] = datetime.now(timezone.utc).isoformat()
        else:
            game["current_turn"] = "O" if player == "X" else "X"
        return None

    async def make_user_move(
        self, user_id: str, game_id: str, row: int, col: int
    ) -> dict[str, Any]:
        """
        Process user move (X), then let AI respond (O) if game continues.
        Returns updated game state + ai_move info.
        """
        game = self.get_game(user_id, game_id)
        if game is None:
            return {"error": "Game not found"}

        # Apply user move
        err = self._apply_move(game, row, col, "X")
        if err:
            return {"error": err}

        ai_move_info = None

        # If game still in progress, get AI move
        if game["status"] == "in_progress":
            ai_result = await get_ai_move(
                game["board"], difficulty=game["difficulty"]
            )
            ai_row, ai_col = ai_result["row"], ai_result["col"]
            reason = ai_result.get("reason", "")

            err = self._apply_move(game, ai_row, ai_col, "O")
            if err:
                # Should not happen with fallback, but handle gracefully
                return {"error": f"AI made invalid move: {err}"}

            ai_move_info = {"row": ai_row, "col": ai_col, "reason": reason}

        result = {
            "game_id": game["game_id"],
            "board": game["board"],
            "current_turn": game["current_turn"],
            "status": game["status"],
            "winner": game["winner"],
            "ai_move": ai_move_info,
            "move_number": game["move_number"],
        }

        # Build message
        if game["status"] == "X_wins":
            result["message"] = "You win! Congratulations!"
        elif game["status"] == "O_wins":
            result["message"] = f"AI wins! {ai_move_info['reason'] if ai_move_info else ''}"
        elif game["status"] == "draw":
            result["message"] = "It's a draw!"
        else:
            result["message"] = f"AI played at ({ai_row}, {ai_col}): {reason}"

        return result

    def restart_game(self, user_id: str, game_id: str) -> dict[str, Any] | None:
        game = self.get_game(user_id, game_id)
        if game is None:
            return None
        # Reset board but keep game_id
        game["board"] = _empty_board()
        game["current_turn"] = "X"
        game["status"] = "in_progress"
        game["winner"] = None
        game["move_number"] = 0
        game["move_history"] = []
        game["started_at"] = datetime.now(timezone.utc).isoformat()
        game["finished_at"] = None
        return game

    def get_history(self, user_id: str) -> list[dict[str, Any]]:
        games = self._user_games(user_id)
        history = []
        for g in games.values():
            if g["status"] == "in_progress":
                continue
            result = "draw"
            if g["winner"] == "X":
                result = "win"
            elif g["winner"] == "O":
                result = "loss"
            history.append({
                "game_id": g["game_id"],
                "result": result,
                "moves": g["move_number"],
                "difficulty": g["difficulty"],
                "started_at": g["started_at"],
                "finished_at": g["finished_at"],
            })
        return sorted(history, key=lambda x: x["started_at"], reverse=True)

    def get_scores(self, user_id: str) -> dict[str, int]:
        history = self.get_history(user_id)
        wins = sum(1 for h in history if h["result"] == "win")
        losses = sum(1 for h in history if h["result"] == "loss")
        draws = sum(1 for h in history if h["result"] == "draw")
        return {
            "wins": wins,
            "losses": losses,
            "draws": draws,
            "total_games": len(history),
        }


# Singleton instance
game_service = GameService()
