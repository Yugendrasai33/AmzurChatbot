import type { AIMoveInfo } from "../../types";

interface AIMoveIndicatorProps {
    isThinking: boolean;
    aiMove: AIMoveInfo | null;
    status: string;
    winner: string | null;
}

export default function AIMoveIndicator({ isThinking, aiMove, status, winner }: AIMoveIndicatorProps) {
    if (isThinking) {
        return (
            <div className="flex items-center gap-2 rounded-lg bg-blue-50 border border-blue-200 px-4 py-2.5 text-sm text-blue-700">
                <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                AI is thinking...
            </div>
        );
    }

    if (status !== "in_progress" && status !== "not_started") {
        const isWin = winner === "X";
        const isDraw = status === "draw";
        return (
            <div
                className={`rounded-lg border px-4 py-2.5 text-sm font-medium text-center ${isWin
                        ? "bg-green-50 border-green-200 text-green-700"
                        : isDraw
                            ? "bg-amber-50 border-amber-200 text-amber-700"
                            : "bg-red-50 border-red-200 text-red-700"
                    }`}
            >
                {isWin ? "You win! 🎉" : isDraw ? "It's a draw!" : "AI wins!"}
            </div>
        );
    }

    if (aiMove) {
        return (
            <div className="rounded-lg bg-gray-50 border border-gray-200 px-4 py-2.5 text-sm text-gray-600">
                <span className="font-medium text-gray-800">AI played ({aiMove.row}, {aiMove.col})</span>
                {aiMove.reason && (
                    <span className="ml-1.5 text-gray-500">— {aiMove.reason}</span>
                )}
            </div>
        );
    }

    return null;
}
