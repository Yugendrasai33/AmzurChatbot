import { useCallback, useState } from "react";
import { gameApi } from "../lib/api";
import type { AIMoveInfo, GameHistoryEntry } from "../types";

export interface GameState {
    gameId: string | null;
    board: string[][];
    currentTurn: string;
    status: string;
    winner: string | null;
    moveNumber: number;
    message: string;
    aiMove: AIMoveInfo | null;
}

const EMPTY_BOARD: string[][] = [
    ["", "", ""],
    ["", "", ""],
    ["", "", ""],
];

export function useGame() {
    const [game, setGame] = useState<GameState>({
        gameId: null,
        board: EMPTY_BOARD,
        currentTurn: "X",
        status: "not_started",
        winner: null,
        moveNumber: 0,
        message: "Start a new game!",
        aiMove: null,
    });

    const [isThinking, setIsThinking] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [difficulty, setDifficulty] = useState<string>("hard");

    const [scores, setScores] = useState({ wins: 0, losses: 0, draws: 0 });
    const [history, setHistory] = useState<GameHistoryEntry[]>([]);

    const startGame = useCallback(async (diff?: string) => {
        const d = diff ?? difficulty;
        setError(null);
        try {
            const res = await gameApi.startGame(d);
            setGame({
                gameId: res.game_id,
                board: res.board,
                currentTurn: res.current_turn,
                status: res.status,
                winner: null,
                moveNumber: 0,
                message: res.message,
                aiMove: null,
            });
        } catch (err: unknown) {
            const msg = err instanceof Error ? err.message : "Failed to start game";
            setError(msg);
        }
    }, [difficulty]);

    const makeMove = useCallback(async (row: number, col: number) => {
        if (!game.gameId || game.status !== "in_progress" || game.currentTurn !== "X") return;
        if (game.board[row][col] !== "") return;

        setError(null);
        setIsThinking(true);

        // Optimistic: show user's move immediately
        const optimisticBoard = game.board.map((r) => [...r]);
        optimisticBoard[row][col] = "X";
        setGame((prev) => ({
            ...prev,
            board: optimisticBoard,
            currentTurn: "O",
            message: "AI is thinking...",
            aiMove: null,
        }));

        try {
            const res = await gameApi.makeMove(game.gameId, row, col);
            setGame({
                gameId: res.game_id,
                board: res.board,
                currentTurn: res.current_turn,
                status: res.status,
                winner: res.winner,
                moveNumber: res.move_number,
                message: res.message,
                aiMove: res.ai_move,
            });

            // Update scores on game end
            if (res.status !== "in_progress") {
                void loadHistory();
            }
        } catch (err: unknown) {
            // Revert optimistic update
            setGame((prev) => ({
                ...prev,
                board: game.board,
                currentTurn: "X",
                message: "Your turn (X)",
            }));
            const msg = err instanceof Error ? err.message : "Move failed";
            setError(msg);
        } finally {
            setIsThinking(false);
        }
    }, [game.gameId, game.status, game.currentTurn, game.board]);

    const restartGame = useCallback(async () => {
        if (!game.gameId) return;
        setError(null);
        try {
            const res = await gameApi.restartGame(game.gameId);
            setGame({
                gameId: res.game_id,
                board: res.board,
                currentTurn: res.current_turn,
                status: res.status,
                winner: null,
                moveNumber: 0,
                message: res.message,
                aiMove: null,
            });
        } catch (err: unknown) {
            const msg = err instanceof Error ? err.message : "Restart failed";
            setError(msg);
        }
    }, [game.gameId]);

    const loadHistory = useCallback(async () => {
        try {
            const res = await gameApi.getHistory();
            setScores({ wins: res.wins, losses: res.losses, draws: res.draws });
            setHistory(res.history);
        } catch {
            // silently ignore
        }
    }, []);

    return {
        game,
        isThinking,
        error,
        difficulty,
        setDifficulty,
        scores,
        history,
        startGame,
        makeMove,
        restartGame,
        loadHistory,
    };
}
