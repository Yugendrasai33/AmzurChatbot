"""Pydantic schemas for the Tic Tac Toe game API."""

from pydantic import BaseModel, Field


class GameStartRequest(BaseModel):
    difficulty: str = Field(default="hard", pattern=r"^(easy|medium|hard)$")


class GameMoveRequest(BaseModel):
    game_id: str
    row: int = Field(ge=0, le=2)
    col: int = Field(ge=0, le=2)


class AIMoveResponse(BaseModel):
    row: int
    col: int
    reason: str


class GameState(BaseModel):
    game_id: str
    board: list[list[str]]
    current_turn: str  # "X" or "O"
    status: str  # "in_progress", "X_wins", "O_wins", "draw"
    winner: str | None = None
    ai_move: AIMoveResponse | None = None
    move_number: int = 0


class GameStartResponse(BaseModel):
    game_id: str
    board: list[list[str]]
    current_turn: str
    status: str
    message: str


class GameMoveResponse(BaseModel):
    game_id: str
    board: list[list[str]]
    current_turn: str
    status: str
    winner: str | None = None
    ai_move: AIMoveResponse | None = None
    message: str
    move_number: int


class GameHistoryEntry(BaseModel):
    game_id: str
    result: str  # "win", "loss", "draw"
    moves: int
    difficulty: str
    started_at: str
    finished_at: str | None = None


class GameScoreResponse(BaseModel):
    wins: int
    losses: int
    draws: int
    total_games: int
    history: list[GameHistoryEntry]
