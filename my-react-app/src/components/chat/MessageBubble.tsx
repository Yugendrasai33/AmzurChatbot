import { type ChatMessage } from "../../types";

interface MessageBubbleProps {
    message: ChatMessage;
}

export function MessageBubble({ message }: MessageBubbleProps) {
    const isUser = message.role === "user";

    return (
        <div className={`mb-4 flex ${isUser ? "justify-end" : "justify-start"}`}>
            <div
                className={`max-w-[88%] rounded-2xl px-4 py-3 text-sm leading-relaxed shadow-sm sm:max-w-[72%] sm:text-base ${isUser
                    ? "border border-teal-700/40 bg-gradient-to-br from-teal-700 to-teal-600 text-white"
                    : "border border-(--line) bg-white text-(--text-main)"
                    }`}
            >
                <p className="whitespace-pre-wrap">{message.content}</p>
            </div>
        </div>
    );
}
