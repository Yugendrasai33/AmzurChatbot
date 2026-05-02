import { useState, useCallback, useRef } from "react";
import { chatApi } from "../lib/api";
import { type ChatMessage, type Thread } from "../types";

export function useChat() {
    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const [threads, setThreads] = useState<Thread[]>([]);
    const [selectedThreadId, setSelectedThreadId] = useState<string | null>(null);
    const [isLoading, setIsLoading] = useState(false);
    const [isHistoryLoading, setIsHistoryLoading] = useState(false);
    const hasAutoSelectedInitialThread = useRef(false);

    const loadThreads = useCallback(async () => {
        const data = await chatApi.listThreads();
        setThreads(data);
        // Auto-select a thread only once on initial load. Do not re-select after "New Chat".
        if (!hasAutoSelectedInitialThread.current && data.length > 0) {
            const firstThread = data[0];
            if (firstThread) {
                setSelectedThreadId((prev) => prev ?? firstThread.id);
                hasAutoSelectedInitialThread.current = true;
            }
        }
    }, []);

    const loadMessages = useCallback(async (threadId: string) => {
        setIsHistoryLoading(true);
        try {
            const data = await chatApi.getThreadMessages(threadId);
            setMessages(data);
            setSelectedThreadId(threadId);
        } finally {
            setIsHistoryLoading(false);
        }
    }, []);

    const startNewThread = useCallback(() => {
        setSelectedThreadId(null);
        setMessages([]);
    }, []);

    const renameThread = useCallback(async (threadId: string, title: string) => {
        const trimmed = title.trim();
        if (!trimmed) return;

        await chatApi.renameThread(threadId, trimmed);
        const latest = await chatApi.listThreads();
        setThreads(latest);
    }, []);

    const deleteThread = useCallback(async (threadId: string) => {
        await chatApi.deleteThread(threadId);
        const latest = await chatApi.listThreads();
        setThreads(latest);

        if (selectedThreadId === threadId) {
            const nextThread = latest[0];
            if (nextThread) {
                setSelectedThreadId(nextThread.id);
                const threadMessages = await chatApi.getThreadMessages(nextThread.id);
                setMessages(threadMessages);
            } else {
                setSelectedThreadId(null);
                setMessages([]);
            }
        }
    }, [selectedThreadId]);

    const sendMessage = useCallback(async (content: string) => {
        // Show the user's message immediately (optimistic update).
        const optimisticId = crypto.randomUUID();
        const optimisticMessage: ChatMessage = {
            id: optimisticId,
            role: "user",
            content,
        };
        setMessages((prev) => [...prev, optimisticMessage]);
        setIsLoading(true);

        try {
            const data = await chatApi.sendMessage({
                message: content,
                thread_id: selectedThreadId,
            });

            setSelectedThreadId(data.thread.id);
            // Replace the optimistic message with the real messages from the server.
            setMessages((prev) => {
                const withoutOptimistic = prev.filter((m) => m.id !== optimisticId);
                return [...withoutOptimistic, data.user_message, data.assistant_message];
            });

            const latestThreads = await chatApi.listThreads();
            setThreads(latestThreads);
        } catch {
            // Replace the optimistic message with an error indicator.
            setMessages((prev) => {
                const withoutOptimistic = prev.filter((m) => m.id !== optimisticId);
                return [
                    ...withoutOptimistic,
                    optimisticMessage,
                    {
                        id: crypto.randomUUID(),
                        role: "assistant" as const,
                        content: "Sorry, something went wrong. Please try again.",
                    },
                ];
            });
        } finally {
            setIsLoading(false);
        }
    }, [selectedThreadId]);

    const clearMessages = useCallback(() => {
        setMessages([]);
    }, []);

    return {
        messages,
        threads,
        selectedThreadId,
        isLoading,
        isHistoryLoading,
        sendMessage,
        clearMessages,
        loadThreads,
        loadMessages,
        startNewThread,
        renameThread,
        deleteThread,
    };
}
