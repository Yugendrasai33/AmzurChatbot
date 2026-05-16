import { useEffect } from "react";
import { useGame } from "../hooks/useGame";
import TicTacToeBoard from "../components/game/TicTacToeBoard";
import GameControls from "../components/game/GameControls";
import ScoreBoard from "../components/game/ScoreBoard";
import AIMoveIndicator from "../components/game/AIMoveIndicator";
import type { AuthUser } from "../types";

interface GamePageProps {
    user: AuthUser;
    onBack: () => void;
}

export default function GamePage({ user, onBack }: GamePageProps) {
    const {
        game,
        isThinking,
        error,
        difficulty,
        setDifficulty,
        scores,
        startGame,
        makeMove,
        restartGame,
        loadHistory,
    } = useGame();

    useEffect(() => {
        void loadHistory();
    }, [loadHistory]);

    return (
        <div className="flex h-screen flex-col bg-linear-to-br from-slate-50 to-indigo-50">
            {/* Header */}
            <header className="flex shrink-0 items-center justify-between border-b border-gray-200 bg-white/80 backdrop-blur px-4 py-3 sm:px-6">
                <div className="flex items-center gap-3">
                    <button
                        onClick={onBack}
                        className="rounded-lg p-1.5 text-gray-500 transition hover:bg-gray-100 hover:text-gray-700"
                        title="Back to chat"
                    >
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <path d="M19 12H5" /><polyline points="12 19 5 12 12 5" />
                        </svg>
                    </button>
                    <h1 className="text-base font-semibold text-gray-900">Tic Tac Toe</h1>
                    <span className="rounded-full bg-indigo-100 px-2 py-0.5 text-[10px] font-medium text-indigo-700 uppercase tracking-wider">
                        AI Agent
                    </span>
                </div>
                <span className="text-xs text-gray-500">{user.email}</span>
            </header>

            {/* Main content */}
            <div className="flex flex-1 flex-col items-center justify-center gap-6 overflow-y-auto px-4 py-6">
                {/* Score */}
                <ScoreBoard wins={scores.wins} losses={scores.losses} draws={scores.draws} />

                {/* Status message */}
                <div className="text-center">
                    <p className="text-sm font-medium text-gray-700">{game.message}</p>
                    {game.status === "in_progress" && (
                        <p className="mt-1 text-xs text-gray-500">
                            You are <span className="font-bold text-indigo-600">X</span> · AI is <span className="font-bold text-rose-500">O</span>
                        </p>
                    )}
                </div>

                {/* AI indicator */}
                <AIMoveIndicator
                    isThinking={isThinking}
                    aiMove={game.aiMove}
                    status={game.status}
                    winner={game.winner}
                />

                {/* Board */}
                <TicTacToeBoard
                    board={game.board}
                    onCellClick={makeMove}
                    disabled={isThinking || game.status !== "in_progress" || game.currentTurn !== "X"}
                    aiMove={game.aiMove}
                    winner={game.winner}
                    status={game.status}
                />

                {/* Error */}
                {error && (
                    <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-2 text-sm text-red-700">
                        {error}
                    </div>
                )}

                {/* Controls */}
                <GameControls
                    status={game.status}
                    gameId={game.gameId}
                    difficulty={difficulty}
                    onDifficultyChange={setDifficulty}
                    onStart={startGame}
                    onRestart={restartGame}
                />

                {/* Move number */}
                {game.status === "in_progress" && game.moveNumber > 0 && (
                    <p className="text-xs text-gray-400">Move {game.moveNumber}</p>
                )}
            </div>
        </div>
    );
}
