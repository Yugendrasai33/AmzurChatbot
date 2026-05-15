import { useRef, useEffect } from "react";
import { type ChatMessage } from "../../types";
import { MessageBubble } from "./MessageBubble";

interface MessageListProps {
    messages: ChatMessage[];
    isLoading: boolean;
    onSelectImage?: (attachmentId: string) => void;
    selectedImageId?: string | null;
    onEditImage?: (attachmentId: string, editPrompt: string) => void;
}

export function MessageList({ messages, isLoading, onSelectImage, selectedImageId, onEditImage }: MessageListProps) {
    const bottomRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages]);

    return (
        <div className="flex-1 overflow-y-auto">
            {messages.length === 0 && (
                <div className="flex h-full items-center justify-center px-4">
                    <div className="max-w-lg text-center">
                        <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-(--surface-soft)">
                            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="text-(--text-muted)">
                                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
                            </svg>
                        </div>
                        <h2 className="mt-4 text-lg font-semibold text-(--text-main)">How can I help you today?</h2>
                        <p className="mt-2 text-sm leading-6 text-(--text-soft)">
                            Ask a question, upload a file, or start a conversation.
                        </p>
                        <div className="mt-6 grid gap-2 sm:grid-cols-3">
                            <div className="rounded-lg border border-(--line) p-3 text-left">
                                <p className="text-sm font-medium text-(--text-main)">Upload & ask</p>
                                <p className="mt-1 text-xs text-(--text-muted)">Attach PDFs, code, or tables</p>
                            </div>
                            <div className="rounded-lg border border-(--line) p-3 text-left">
                                <p className="text-sm font-medium text-(--text-main)">Organize threads</p>
                                <p className="mt-1 text-xs text-(--text-muted)">Keep topics separate</p>
                            </div>
                            <div className="rounded-lg border border-(--line) p-3 text-left">
                                <p className="text-sm font-medium text-(--text-main)">Generate images</p>
                                <p className="mt-1 text-xs text-(--text-muted)">Create visuals from text</p>
                            </div>
                        </div>
                    </div>
                </div>
            )}
            <div className="flex w-full flex-col">
                {messages.map((msg) => (
                    <MessageBubble key={msg.id} message={msg} onSelectImage={onSelectImage} selectedImageId={selectedImageId} onEditImage={onEditImage} />
                ))}
            </div>
            {isLoading && (messages.length === 0 || messages[messages.length - 1]?.role !== "assistant") && (
                <div className="flex justify-start px-4 py-4 sm:px-6">
                    <div className="flex max-w-[75%] flex-row gap-3">
                        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-emerald-600 text-xs font-semibold text-white">AI</div>
                        <div className="rounded-2xl rounded-tl-sm bg-(--surface-soft) px-4 py-3">
                            <div className="flex items-center gap-1.5">
                                <span className="h-2 w-2 rounded-full bg-(--text-muted) animate-bounce" />
                                <span className="h-2 w-2 rounded-full bg-(--text-muted) animate-bounce [animation-delay:0.15s]" />
                                <span className="h-2 w-2 rounded-full bg-(--text-muted) animate-bounce [animation-delay:0.3s]" />
                            </div>
                        </div>
                    </div>
                </div>
            )}
            <div ref={bottomRef} />
        </div>
    );
}
