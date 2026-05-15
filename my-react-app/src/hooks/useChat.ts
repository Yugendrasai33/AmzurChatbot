import { useState, useCallback, useRef } from "react";
import axios from "axios";
import { chatApi, ragApi, sqlApi } from "../lib/api";
import { type AttachmentMeta, type ChatMessage, type Thread } from "../types";

export function useChat() {
    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const [threads, setThreads] = useState<Thread[]>([]);
    const [selectedThreadId, setSelectedThreadId] = useState<string | null>(null);
    const [isLoading, setIsLoading] = useState(false);
    const [isHistoryLoading, setIsHistoryLoading] = useState(false);
    const [errorMessage, setErrorMessage] = useState<string | null>(null);
    const [ragMode, setRagMode] = useState(false);
    const [sqlMode, setSqlMode] = useState(false);
    const hasAutoSelectedInitialThread = useRef(false);
    const skipNextLoadRef = useRef(false);

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
        // Skip if a send function just created this thread (messages are already in state)
        if (skipNextLoadRef.current) {
            skipNextLoadRef.current = false;
            return;
        }
        setIsHistoryLoading(true);
        setErrorMessage(null);
        try {
            const data = await chatApi.getThreadMessages(threadId);
            setMessages(data);
            setSelectedThreadId(threadId);
        } catch {
            setErrorMessage("Couldn't load this conversation right now.");
        } finally {
            setIsHistoryLoading(false);
        }
    }, []);

    const startNewThread = useCallback(() => {
        setSelectedThreadId(null);
        setMessages([]);
        setErrorMessage(null);
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

    const sendMessage = useCallback(async (content: string, files?: File[]) => {
        // Show the user's message immediately (optimistic update).
        const optimisticId = crypto.randomUUID();
        const optimisticMessage: ChatMessage = {
            id: optimisticId,
            role: "user",
            content,
        };
        setMessages((prev) => [...prev, optimisticMessage]);
        setIsLoading(true);
        setErrorMessage(null);

        try {
            // Upload files first if any
            let attachmentIds: string[] | undefined;
            if (files && files.length > 0) {
                const uploaded = await Promise.all(files.map((f) => chatApi.uploadFile(f)));
                attachmentIds = uploaded.map((u) => u.id);

                // Auto-ingest uploaded files into RAG pipeline
                await Promise.allSettled(
                    uploaded.map((u) => ragApi.ingestAttachment(u.id))
                );
            }

            const data = await chatApi.sendMessage({
                message: content,
                thread_id: selectedThreadId,
                attachment_ids: attachmentIds,
            });

            skipNextLoadRef.current = true;
            setSelectedThreadId(data.thread.id);
            // Replace the optimistic message with the real messages from the server.
            setMessages((prev) => {
                const withoutOptimistic = prev.filter((m) => m.id !== optimisticId);
                return [...withoutOptimistic, data.user_message, data.assistant_message];
            });

            const latestThreads = await chatApi.listThreads();
            setThreads(latestThreads);
        } catch (error) {
            const fallbackMessage = "Something went wrong while sending your message.";
            let nextError = fallbackMessage;

            if (axios.isAxiosError(error)) {
                const detail = error.response?.data?.detail;
                if (typeof detail === "string") {
                    nextError = detail;
                } else if (detail && typeof detail === "object") {
                    nextError = detail.message ?? detail.error ?? fallbackMessage;
                }
            }

            setErrorMessage(nextError);
            // Replace the optimistic message with an error indicator.
            setMessages((prev) => {
                const withoutOptimistic = prev.filter((m) => m.id !== optimisticId);
                return [
                    ...withoutOptimistic,
                    optimisticMessage,
                    {
                        id: crypto.randomUUID(),
                        role: "assistant" as const,
                        content: nextError,
                    },
                ];
            });
        } finally {
            setIsLoading(false);
        }
    }, [selectedThreadId]);

    const toggleRagMode = useCallback(() => {
        setRagMode((prev) => {
            if (!prev) setSqlMode(false);
            return !prev;
        });
    }, []);

    const toggleSqlMode = useCallback(() => {
        setSqlMode((prev) => {
            if (!prev) setRagMode(false);
            return !prev;
        });
    }, []);

    const sendRagMessage = useCallback(async (content: string, files?: File[]) => {
        let threadId = selectedThreadId;

        // Auto-create a thread if none selected
        if (!threadId) {
            try {
                const newThread = await chatApi.createThread({ title: content.slice(0, 50) });
                threadId = newThread.id;
                skipNextLoadRef.current = true;
                setSelectedThreadId(threadId);
                setThreads((prev) => [newThread, ...prev]);
            } catch {
                setErrorMessage("Failed to create a new thread.");
                return;
            }
        }

        const optimisticId = crypto.randomUUID();
        const optimisticMessage: ChatMessage = {
            id: optimisticId,
            role: "user",
            content,
        };
        setMessages((prev) => [...prev, optimisticMessage]);
        setIsLoading(true);
        setErrorMessage(null);

        try {
            // Upload and ingest files if any — collect IDs to scope retrieval
            let uploadedAttachmentIds: string[] | undefined;
            if (files && files.length > 0) {
                const uploaded = await Promise.all(files.map((f) => chatApi.uploadFile(f)));
                uploadedAttachmentIds = uploaded.map((u) => u.id);
                await Promise.allSettled(
                    uploaded.map((u) => ragApi.ingestAttachment(u.id))
                );
            }

            // Create a streaming assistant message placeholder
            const assistantId = crypto.randomUUID();
            const assistantMessage: ChatMessage = {
                id: assistantId,
                role: "assistant",
                content: "",
            };
            setMessages((prev) => [...prev, assistantMessage]);

            await ragApi.streamRag(threadId, content, (token) => {
                setMessages((prev) =>
                    prev.map((m) =>
                        m.id === assistantId
                            ? { ...m, content: m.content + token }
                            : m
                    )
                );
            }, (sources) => {
                setMessages((prev) =>
                    prev.map((m) =>
                        m.id === assistantId
                            ? { ...m, sources }
                            : m
                    )
                );
            }, uploadedAttachmentIds);

            const latestThreads = await chatApi.listThreads();
            setThreads(latestThreads);
        } catch (error) {
            const fallbackMessage = "Document search failed. Please try again.";
            let nextError = fallbackMessage;

            if (error instanceof Error) {
                nextError = error.message || fallbackMessage;
            } else if (axios.isAxiosError(error)) {
                const detail = error.response?.data?.detail;
                if (typeof detail === "string") {
                    nextError = detail;
                } else if (detail && typeof detail === "object") {
                    nextError = detail.message ?? detail.error ?? fallbackMessage;
                }
            }

            setErrorMessage(nextError);
            setMessages((prev) => [
                ...prev.filter((m) => m.content !== ""),
                {
                    id: crypto.randomUUID(),
                    role: "assistant" as const,
                    content: nextError,
                },
            ]);
        } finally {
            setIsLoading(false);
        }
    }, [selectedThreadId]);

    const sendSqlMessage = useCallback(async (content: string) => {
        let threadId = selectedThreadId;

        // Auto-create a thread if none selected
        if (!threadId) {
            try {
                const newThread = await chatApi.createThread({ title: content.slice(0, 50) });
                threadId = newThread.id;
                skipNextLoadRef.current = true;
                setSelectedThreadId(threadId);
                setThreads((prev) => [newThread, ...prev]);
            } catch {
                setErrorMessage("Failed to create a new thread.");
                return;
            }
        }

        const optimisticId = crypto.randomUUID();
        const optimisticMessage: ChatMessage = {
            id: optimisticId,
            role: "user",
            content,
        };
        setMessages((prev) => [...prev, optimisticMessage]);
        setIsLoading(true);
        setErrorMessage(null);

        try {
            const assistantId = crypto.randomUUID();
            const assistantMessage: ChatMessage = {
                id: assistantId,
                role: "assistant",
                content: "",
            };
            setMessages((prev) => [...prev, assistantMessage]);

            await sqlApi.streamQuery(threadId, content, (token) => {
                setMessages((prev) =>
                    prev.map((m) =>
                        m.id === assistantId
                            ? { ...m, content: m.content + token }
                            : m
                    )
                );
            }, (sqlQuery) => {
                setMessages((prev) =>
                    prev.map((m) =>
                        m.id === assistantId
                            ? { ...m, sql_query: sqlQuery }
                            : m
                    )
                );
            }, (sqlResult) => {
                setMessages((prev) =>
                    prev.map((m) =>
                        m.id === assistantId
                            ? { ...m, sql_result: sqlResult }
                            : m
                    )
                );
            });

            const latestThreads = await chatApi.listThreads();
            setThreads(latestThreads);
        } catch (error) {
            const fallbackMessage = "Database query failed. Please try again.";
            let nextError = fallbackMessage;

            if (error instanceof Error) {
                nextError = error.message || fallbackMessage;
            } else if (axios.isAxiosError(error)) {
                const detail = error.response?.data?.detail;
                if (typeof detail === "string") {
                    nextError = detail;
                } else if (detail && typeof detail === "object") {
                    nextError = detail.message ?? detail.error ?? fallbackMessage;
                }
            }

            setErrorMessage(nextError);
            setMessages((prev) => [
                ...prev.filter((m) => m.content !== ""),
                {
                    id: crypto.randomUUID(),
                    role: "assistant" as const,
                    content: nextError,
                },
            ]);
        } finally {
            setIsLoading(false);
        }
    }, [selectedThreadId]);

    const generateImage = useCallback(async (prompt: string) => {
        const cleaned = prompt.trim();
        if (!cleaned) return;

        const optimisticId = crypto.randomUUID();
        const optimisticUserMessage: ChatMessage = {
            id: optimisticId,
            role: "user",
            content: `/image ${cleaned}`,
        };

        setMessages((prev) => [...prev, optimisticUserMessage]);
        setIsLoading(true);
        setErrorMessage(null);

        try {
            const attachment: AttachmentMeta = await chatApi.generateImage(cleaned, selectedThreadId);

            const assistantMessage: ChatMessage = {
                id: crypto.randomUUID(),
                role: "assistant",
                content: `Generated image for: ${cleaned}`,
                attachments: [attachment],
            };

            setMessages((prev) => {
                const withoutOptimistic = prev.filter((m) => m.id !== optimisticId);
                return [...withoutOptimistic, optimisticUserMessage, assistantMessage];
            });

            const latestThreads = await chatApi.listThreads();
            setThreads(latestThreads);
            if (!selectedThreadId && latestThreads.length > 0) {
                const firstThread = latestThreads[0];
                if (firstThread) {
                    setSelectedThreadId(firstThread.id);
                }
            }
        } catch (error) {
            const fallbackMessage = "Image generation failed. Please try again.";
            let nextError = fallbackMessage;

            if (axios.isAxiosError(error)) {
                const detail = error.response?.data?.detail;
                if (typeof detail === "string") {
                    nextError = detail;
                } else if (detail && typeof detail === "object") {
                    nextError = detail.message ?? detail.error ?? fallbackMessage;
                }
            }

            setErrorMessage(nextError);
            setMessages((prev) => [
                ...prev,
                {
                    id: crypto.randomUUID(),
                    role: "assistant",
                    content: nextError,
                },
            ]);
        } finally {
            setIsLoading(false);
        }
    }, [selectedThreadId]);

    const clearMessages = useCallback(() => {
        setMessages([]);
    }, []);

    const editImage = useCallback(async (attachmentId: string, editPrompt: string) => {
        const trimmed = editPrompt.trim();
        if (!trimmed) return;

        setIsLoading(true);
        setErrorMessage(null);

        try {
            const attachment: AttachmentMeta = await chatApi.editImage(attachmentId, trimmed, selectedThreadId);

            const assistantMessage: ChatMessage = {
                id: crypto.randomUUID(),
                role: "assistant",
                content: `Edited image: ${trimmed}`,
                attachments: [attachment],
            };

            setMessages((prev) => [...prev, assistantMessage]);

            const latestThreads = await chatApi.listThreads();
            setThreads(latestThreads);
            if (!selectedThreadId && latestThreads.length > 0 && latestThreads[0]) {
                setSelectedThreadId(latestThreads[0].id);
            }
        } catch (error) {
            const fallbackMessage = "Image editing failed. Please try again.";
            let nextError = fallbackMessage;

            if (axios.isAxiosError(error)) {
                const detail = error.response?.data?.detail;
                if (typeof detail === "string") {
                    nextError = detail;
                } else if (detail && typeof detail === "object") {
                    nextError = detail.message ?? detail.error ?? fallbackMessage;
                }
            }

            setErrorMessage(nextError);
            setMessages((prev) => [
                ...prev,
                { id: crypto.randomUUID(), role: "assistant" as const, content: nextError },
            ]);
        } finally {
            setIsLoading(false);
        }
    }, [selectedThreadId]);

    return {
        messages,
        threads,
        selectedThreadId,
        isLoading,
        isHistoryLoading,
        errorMessage,
        ragMode,
        sqlMode,
        sendMessage,
        sendRagMessage,
        sendSqlMessage,
        generateImage,
        editImage,
        clearMessages,
        loadThreads,
        loadMessages,
        startNewThread,
        renameThread,
        deleteThread,
        toggleRagMode,
        toggleSqlMode,
    };
}
