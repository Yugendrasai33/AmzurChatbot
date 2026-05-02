import { useState, type FormEvent } from "react";

interface InputBarProps {
    onSend: (message: string) => void;
    isLoading: boolean;
}

export function InputBar({ onSend, isLoading }: InputBarProps) {
    const [input, setInput] = useState("");

    const handleSubmit = (e: FormEvent) => {
        e.preventDefault();
        const trimmed = input.trim();
        if (!trimmed || isLoading) return;
        onSend(trimmed);
        setInput("");
    };

    return (
        <form onSubmit={handleSubmit} className="border-t border-(--line) bg-(--surface-strong)/85 p-4 sm:p-5">
            <div className="flex items-center gap-2 rounded-2xl border border-(--line) bg-white px-2 py-2 shadow-sm sm:gap-3 sm:px-3">
                <input
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    placeholder="Type your message..."
                    className="h-11 flex-1 rounded-xl border-none bg-transparent px-2 text-sm text-(--text-main) placeholder:text-(--text-soft) focus:outline-none focus:ring-0 sm:text-base"
                    disabled={isLoading}
                />
                <button
                    type="submit"
                    disabled={isLoading || !input.trim()}
                    className="h-11 rounded-xl bg-(--accent) px-5 text-sm font-semibold text-white transition hover:bg-(--accent-strong) disabled:cursor-not-allowed disabled:opacity-45 sm:px-6"
                >
                    {isLoading ? "Sending..." : "Send"}
                </button>
            </div>
            <p className="mt-2 px-1 text-xs text-(--text-soft)">
                Your chat may include generated content. Verify important details.
            </p>
        </form>
    );
}
