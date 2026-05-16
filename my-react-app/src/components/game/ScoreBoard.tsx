interface ScoreBoardProps {
    wins: number;
    losses: number;
    draws: number;
}

export default function ScoreBoard({ wins, losses, draws }: ScoreBoardProps) {
    return (
        <div className="flex gap-4 justify-center">
            <div className="flex flex-col items-center rounded-lg bg-green-50 border border-green-200 px-4 py-2 min-w-[60px]">
                <span className="text-lg font-bold text-green-700">{wins}</span>
                <span className="text-[10px] font-medium text-green-600 uppercase tracking-wider">Wins</span>
            </div>
            <div className="flex flex-col items-center rounded-lg bg-red-50 border border-red-200 px-4 py-2 min-w-[60px]">
                <span className="text-lg font-bold text-red-700">{losses}</span>
                <span className="text-[10px] font-medium text-red-600 uppercase tracking-wider">Losses</span>
            </div>
            <div className="flex flex-col items-center rounded-lg bg-gray-50 border border-gray-200 px-4 py-2 min-w-[60px]">
                <span className="text-lg font-bold text-gray-700">{draws}</span>
                <span className="text-[10px] font-medium text-gray-500 uppercase tracking-wider">Draws</span>
            </div>
        </div>
    );
}
