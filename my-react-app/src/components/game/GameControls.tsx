interface GameControlsProps {
    status: string;
    gameId: string | null;
    difficulty: string;
    onDifficultyChange: (d: string) => void;
    onStart: (difficulty?: string) => void;
    onRestart: () => void;
}

export default function GameControls({
    status,
    gameId,
    difficulty,
    onDifficultyChange,
    onStart,
    onRestart,
}: GameControlsProps) {
    return (
        <div className="flex flex-col items-center gap-3 w-full">
            {/* Difficulty selector */}
            <div className="flex items-center gap-2">
                <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">Difficulty</span>
                <div className="flex rounded-lg border border-gray-200 overflow-hidden">
                    {(["easy", "medium", "hard"] as const).map((d) => (
                        <button
                            key={d}
                            onClick={() => onDifficultyChange(d)}
                            className={`px-3 py-1.5 text-xs font-medium capitalize transition ${difficulty === d
                                    ? "bg-indigo-600 text-white"
                                    : "bg-white text-gray-600 hover:bg-gray-50"
                                }`}
                        >
                            {d}
                        </button>
                    ))}
                </div>
            </div>

            {/* Action buttons */}
            <div className="flex gap-2">
                {(!gameId || status !== "in_progress") && (
                    <button
                        onClick={() => onStart(difficulty)}
                        className="rounded-lg bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-indigo-700 active:scale-95"
                    >
                        {gameId ? "New Game" : "Start Game"}
                    </button>
                )}
                {gameId && status === "in_progress" && (
                    <button
                        onClick={onRestart}
                        className="rounded-lg border border-gray-300 bg-white px-5 py-2.5 text-sm font-medium text-gray-700 shadow-sm transition hover:bg-gray-50 active:scale-95"
                    >
                        Restart
                    </button>
                )}
            </div>
        </div>
    );
}
