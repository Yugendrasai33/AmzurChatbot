import type { AIMoveInfo } from "../../types";

interface TicTacToeBoardProps {
    board: string[][];
    onCellClick: (row: number, col: number) => void;
    disabled: boolean;
    aiMove: AIMoveInfo | null;
    winner: string | null;
    status: string;
}

export default function TicTacToeBoard({
    board,
    onCellClick,
    disabled,
    aiMove,
    winner,
    status,
}: TicTacToeBoardProps) {
    const winningCells = getWinningCells(board, winner);

    return (
        <div className="grid grid-cols-3 gap-2 w-full max-w-xs mx-auto">
            {board.map((row, r) =>
                row.map((cell, c) => {
                    const isWinning = winningCells.some(([wr, wc]) => wr === r && wc === c);
                    const isAiLast = aiMove && aiMove.row === r && aiMove.col === c;
                    const isEmpty = cell === "";
                    const canClick = !disabled && isEmpty && status === "in_progress";

                    return (
                        <button
                            key={`${r}-${c}`}
                            onClick={() => canClick && onCellClick(r, c)}
                            disabled={!canClick}
                            className={`
                                aspect-square rounded-xl text-3xl sm:text-4xl font-bold
                                flex items-center justify-center
                                transition-all duration-200
                                border-2
                                ${isWinning
                                    ? "border-green-400 bg-green-50 scale-105"
                                    : isAiLast
                                        ? "border-blue-300 bg-blue-50"
                                        : "border-gray-200 bg-white hover:border-gray-300"
                                }
                                ${canClick ? "cursor-pointer hover:bg-gray-50 active:scale-95" : "cursor-default"}
                                ${cell === "X" ? "text-indigo-600" : cell === "O" ? "text-rose-500" : "text-transparent"}
                            `}
                        >
                            {cell || "\u00B7"}
                        </button>
                    );
                })
            )}
        </div>
    );
}

function getWinningCells(board: string[][], winner: string | null): [number, number][] {
    if (!winner) return [];
    const lines: [number, number][][] = [];
    for (let i = 0; i < 3; i++) {
        lines.push([[i, 0], [i, 1], [i, 2]]);
        lines.push([[0, i], [1, i], [2, i]]);
    }
    lines.push([[0, 0], [1, 1], [2, 2]]);
    lines.push([[0, 2], [1, 1], [2, 0]]);

    for (const line of lines) {
        if (line.every(([r, c]) => board[r][c] === winner)) {
            return line;
        }
    }
    return [];
}
