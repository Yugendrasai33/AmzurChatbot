import { useRef, useEffect } from "react";
import { type ChatMessage } from "../../types";
import { MessageBubble } from "./MessageBubble";

interface MessageListProps {
    messages: ChatMessage[];
    isLoading: boolean;
}

export function MessageList({ messages, isLoading }: MessageListProps) {
    const bottomRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages]);

    return (
        <div className="flex-1 overflow-y-auto px-4 py-5 sm:px-8 sm:py-6">
            {messages.length === 0 && (
                <div className="flex h-full items-center justify-center">
                    <div className="max-w-md rounded-2xl border border-(--line) bg-white/80 px-6 py-8 text-center shadow-sm">
                        <p className="text-lg font-semibold text-(--text-main)">Start the conversation</p>
                        <p className="mt-2 text-sm leading-relaxed text-(--text-soft)">
                            Ask a question, brainstorm ideas, or draft content in seconds.
                        </p>
                    </div>
                </div>
            )}
            {messages.map((msg) => (
                <MessageBubble key={msg.id} message={msg} />
            ))}
            {isLoading && (
                <div className="mb-4 flex justify-start">
                    <div className="rounded-2xl border border-(--line) bg-white px-4 py-3 shadow-sm">
                        <div className="flex gap-1.5">
                            <span className="h-2.5 w-2.5 rounded-full bg-teal-600/70 animate-bounce" />
                            <span className="h-2.5 w-2.5 rounded-full bg-teal-600/70 animate-bounce [animation-delay:0.18s]" />
                            <span className="h-2.5 w-2.5 rounded-full bg-teal-600/70 animate-bounce [animation-delay:0.34s]" />
                        </div>
                    </div>
                </div>
            )}
            <div ref={bottomRef} />
        </div>
    );
}
