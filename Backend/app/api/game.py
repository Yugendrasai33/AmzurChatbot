"""API routes for Tic Tac Toe game."""

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.security import get_current_user
from app.services.auth_service import AuthenticatedUser
from app.schemas.game import (
    GameMoveRequest,
    GameMoveResponse,
    GameScoreResponse,
    GameStartRequest,
    GameStartResponse,
)
from app.services.game_service import game_service

router = APIRouter(prefix="/api/game", tags=["game"])


@router.post("/start", response_model=GameStartResponse)
async def start_game(
    body: GameStartRequest | None = None,
    user: AuthenticatedUser = Depends(get_current_user),
):
    difficulty = body.difficulty if body else "hard"
    game = game_service.start_game(user.id, difficulty)
    return GameStartResponse(
        game_id=game["game_id"],
        board=game["board"],
        current_turn=game["current_turn"],
        status=game["status"],
        message=f"Game started! You are X. Difficulty: {difficulty}",
    )


@router.post("/move", response_model=GameMoveResponse)
async def make_move(
    body: GameMoveRequest,
    user: AuthenticatedUser = Depends(get_current_user),
):
    result = await game_service.make_user_move(
        user.id, body.game_id, body.row, body.col
    )
    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=result["error"]
        )
    return GameMoveResponse(**result)


@router.post("/restart/{game_id}")
async def restart_game(
    game_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
):
    game = game_service.restart_game(user.id, game_id)
    if game is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Game not found"
        )
    return GameStartResponse(
        game_id=game["game_id"],
        board=game["board"],
        current_turn=game["current_turn"],
        status=game["status"],
        message="Game restarted! Your move.",
    )


@router.get("/history")
async def get_history(
    user: AuthenticatedUser = Depends(get_current_user),
):
    scores = game_service.get_scores(user.id)
    history = game_service.get_history(user.id)
    return GameScoreResponse(
        wins=scores["wins"],
        losses=scores["losses"],
        draws=scores["draws"],
        total_games=scores["total_games"],
        history=history,
    )
