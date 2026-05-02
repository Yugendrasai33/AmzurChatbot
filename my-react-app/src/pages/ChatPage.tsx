import { useEffect, useState } from "react";
import { useChat } from "../hooks/useChat";
import { MessageList } from "../components/chat/MessageList";
import { InputBar } from "../components/chat/InputBar";
import { type AuthUser } from "../types";

interface ChatPageProps {
    user: AuthUser;
    onLogout: () => void;
}

export default function ChatPage({ user, onLogout }: ChatPageProps) {
    const {
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
    } = useChat();

    const [renameModalThreadId, setRenameModalThreadId] = useState<string | null>(null);
    const [renameInput, setRenameInput] = useState("");
    const [deleteModalThreadId, setDeleteModalThreadId] = useState<string | null>(null);

    useEffect(() => {
        void loadThreads();
    }, [loadThreads]);

    useEffect(() => {
        if (selectedThreadId) {
            void loadMessages(selectedThreadId);
        }
    }, [selectedThreadId, loadMessages]);

    return (
        <main className="relative min-h-screen overflow-hidden p-4 sm:p-8">
            <div className="pointer-events-none absolute -left-10 top-8 h-40 w-40 rounded-full bg-teal-300/35 blur-3xl sm:h-56 sm:w-56" />
            <div className="pointer-events-none absolute -right-12 bottom-10 h-44 w-44 rounded-full bg-amber-300/35 blur-3xl sm:h-60 sm:w-60" />

            <div className="relative mx-auto grid h-[calc(100vh-2rem)] max-w-6xl grid-cols-1 overflow-hidden rounded-3xl border border-(--line) bg-(--surface)/85 shadow-[0_22px_70px_rgba(32,21,10,0.14)] backdrop-blur sm:h-[calc(100vh-4rem)] md:grid-cols-[280px_1fr]">
                <aside className="border-b border-(--line) bg-(--surface-strong)/90 p-4 md:border-b-0 md:border-r">
                    <div className="flex items-start justify-between gap-2">
                        <div>
                            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-(--text-soft)">Stackyon</p>
                            <p className="text-sm font-medium text-(--text-main)">{user.email}</p>
                        </div>
                        <button
                            onClick={onLogout}
                            className="rounded-lg border border-(--line) bg-white px-2 py-1 text-xs text-(--text-main)"
                        >
                            Logout
                        </button>
                    </div>

                    <button
                        onClick={startNewThread}
                        className="mt-4 w-full rounded-xl bg-(--accent) px-3 py-2 text-sm font-semibold text-white transition hover:bg-(--accent-strong)"
                    >
                        + New Chat
                    </button>

                    <div className="mt-4 space-y-2 overflow-y-auto pr-1 md:h-[calc(100vh-15rem)]">
                        {threads.map((thread) => (
                            <div
                                key={thread.id}
                                className={`w-full rounded-xl border px-3 py-2 text-left text-sm transition ${selectedThreadId === thread.id
                                    ? "border-teal-600 bg-teal-50 text-teal-900"
                                    : "border-(--line) bg-white text-(--text-main) hover:border-amber-300"
                                    }`}
                            >
                                <button
                                    onClick={() => void loadMessages(thread.id)}
                                    className="w-full text-left"
                                >
                                    <p className="truncate font-medium">{thread.title}</p>
                                    <p className="mt-1 text-xs text-(--text-soft)">
                                        {new Date(thread.updated_at).toLocaleString()}
                                    </p>
                                </button>
                                <div className="mt-2 flex gap-2">
                                    <button
                                        onClick={() => {
                                            setRenameModalThreadId(thread.id);
                                            setRenameInput(thread.title);
                                        }}
                                        className="rounded-md border border-(--line) bg-white px-2 py-1 text-xs"
                                    >
                                        Rename
                                    </button>
                                    <button
                                        onClick={() => setDeleteModalThreadId(thread.id)}
                                        className="rounded-md border border-red-200 bg-red-50 px-2 py-1 text-xs text-red-700"
                                    >
                                        Delete
                                    </button>
                                </div>
                            </div>
                        ))}
                    </div>
                </aside>

                <section className="flex min-h-0 flex-col">
                    <header className="flex items-center justify-between border-b border-(--line) bg-(--surface-strong)/85 px-5 py-4 sm:px-7 sm:py-5">
                        <div>
                            <p className="text-xs font-semibold uppercase tracking-[0.28em] text-(--text-soft)">
                                Conversational AI
                            </p>
                            <h1 className="mt-1 text-xl font-semibold text-(--text-main) sm:text-2xl">
                                Chat Studio
                            </h1>
                        </div>
                        <button
                            onClick={clearMessages}
                            className="rounded-xl border border-(--line) bg-white/90 px-4 py-2 text-sm font-medium text-(--text-main) transition hover:-translate-y-0.5 hover:border-amber-300 hover:bg-amber-50"
                        >
                            Clear View
                        </button>
                    </header>

                    <MessageList messages={messages} isLoading={isLoading || isHistoryLoading} />
                    <InputBar onSend={sendMessage} isLoading={isLoading} />
                </section>
            </div>

            {renameModalThreadId && (
                <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/35 p-4">
                    <div className="w-full max-w-md rounded-2xl border border-(--line) bg-white p-5 shadow-xl">
                        <h2 className="text-lg font-semibold text-(--text-main)">Rename thread</h2>
                        <input
                            value={renameInput}
                            onChange={(e) => setRenameInput(e.target.value)}
                            className="mt-3 w-full rounded-xl border border-(--line) px-3 py-2 text-sm"
                            placeholder="Thread title"
                        />
                        <div className="mt-4 flex justify-end gap-2">
                            <button
                                onClick={() => {
                                    setRenameModalThreadId(null);
                                    setRenameInput("");
                                }}
                                className="rounded-lg border border-(--line) px-3 py-2 text-sm"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={() => {
                                    if (renameModalThreadId) {
                                        void renameThread(renameModalThreadId, renameInput);
                                    }
                                    setRenameModalThreadId(null);
                                    setRenameInput("");
                                }}
                                className="rounded-lg bg-(--accent) px-3 py-2 text-sm font-semibold text-white"
                            >
                                Save
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {deleteModalThreadId && (
                <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/35 p-4">
                    <div className="w-full max-w-md rounded-2xl border border-(--line) bg-white p-5 shadow-xl">
                        <h2 className="text-lg font-semibold text-(--text-main)">Delete thread</h2>
                        <p className="mt-2 text-sm text-(--text-soft)">This will permanently remove the thread and its messages.</p>
                        <div className="mt-4 flex justify-end gap-2">
                            <button
                                onClick={() => setDeleteModalThreadId(null)}
                                className="rounded-lg border border-(--line) px-3 py-2 text-sm"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={() => {
                                    if (deleteModalThreadId) {
                                        void deleteThread(deleteModalThreadId);
                                    }
                                    setDeleteModalThreadId(null);
                                }}
                                className="rounded-lg bg-red-600 px-3 py-2 text-sm font-semibold text-white"
                            >
                                Delete
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </main>
    );
}
