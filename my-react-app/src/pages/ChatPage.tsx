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
        errorMessage,
        ragMode,
        sqlMode,
        sheetsMode,
        researchMode,
        sendMessage,
        sendRagMessage,
        sendSqlMessage,
        sendSheetsMessage,
        sendResearchMessage,
        generateImage,
        editImage,
        loadThreads,
        loadMessages,
        startNewThread,
        renameThread,
        deleteThread,
        toggleRagMode,
        toggleSqlMode,
        toggleSheetsMode,
        toggleResearchMode,
    } = useChat();

    const [renameModalThreadId, setRenameModalThreadId] = useState<string | null>(null);
    const [renameInput, setRenameInput] = useState("");
    const [deleteModalThreadId, setDeleteModalThreadId] = useState<string | null>(null);
    const [selectedImageId, setSelectedImageId] = useState<string | null>(null);

    useEffect(() => {
        void loadThreads();
    }, [loadThreads]);

    useEffect(() => {
        if (selectedThreadId) {
            void loadMessages(selectedThreadId);
            setSelectedImageId(null);
        }
    }, [selectedThreadId, loadMessages]);

    const handleSelectImage = (attachmentId: string) => {
        setSelectedImageId((prev) => (prev === attachmentId ? null : attachmentId));
    };

    return (
        <main className="flex h-screen bg-white">
            {/* Sidebar */}
            <aside className="hidden w-64 flex-col border-r border-(--line) bg-(--sidebar-bg) lg:flex">
                <div className="flex items-center justify-between px-4 py-4">
                    <span className="text-sm font-semibold text-(--text-main)">Amzur AI</span>
                    <button
                        onClick={onLogout}
                        className="rounded-md px-2.5 py-1 text-xs font-medium text-(--text-soft) transition hover:bg-(--surface-soft) hover:text-(--text-main)"
                    >
                        Log out
                    </button>
                </div>

                <div className="px-3">
                    <button
                        onClick={startNewThread}
                        className="flex w-full items-center gap-2 rounded-lg border border-(--line) px-3 py-2.5 text-sm font-medium text-(--text-main) transition hover:bg-(--surface-soft)"
                    >
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" /></svg>
                        New chat
                    </button>
                </div>

                <div className="mt-4 flex-1 overflow-y-auto px-3">
                    <p className="mb-2 px-1 text-xs font-medium text-(--text-muted)">Recent</p>
                    <div className="space-y-0.5">
                        {threads.length === 0 && (
                            <p className="px-3 py-4 text-sm text-(--text-muted)">No conversations yet</p>
                        )}
                        {threads.map((thread) => {
                            const isActive = selectedThreadId === thread.id;

                            return (
                                <div
                                    key={thread.id}
                                    className={`group flex items-center rounded-lg px-3 py-2 text-sm transition ${isActive
                                        ? "bg-(--surface-soft) font-medium text-(--text-main)"
                                        : "text-(--text-soft) hover:bg-(--surface-soft)/60"
                                        }`}
                                >
                                    <button
                                        onClick={() => void loadMessages(thread.id)}
                                        className="min-w-0 flex-1 truncate text-left"
                                    >
                                        {thread.title}
                                    </button>
                                    <div className="ml-2 flex shrink-0 gap-1 opacity-0 transition group-hover:opacity-100">
                                        <button
                                            onClick={() => {
                                                setRenameModalThreadId(thread.id);
                                                setRenameInput(thread.title);
                                            }}
                                            className="rounded p-1 text-(--text-muted) hover:text-(--text-main)"
                                            title="Rename"
                                        >
                                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" /><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" /></svg>
                                        </button>
                                        <button
                                            onClick={() => setDeleteModalThreadId(thread.id)}
                                            className="rounded p-1 text-(--text-muted) hover:text-red-600"
                                            title="Delete"
                                        >
                                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="3 6 5 6 21 6" /><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" /></svg>
                                        </button>
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                </div>

                <div className="border-t border-(--line) px-4 py-3">
                    <p className="truncate text-xs text-(--text-muted)">{user.email}</p>
                </div>
            </aside>

            {/* Main chat area */}
            <section className="flex min-w-0 flex-1 flex-col">
                {/* Top bar */}
                <header className="flex shrink-0 items-center justify-between border-b border-(--line) px-4 py-3 sm:px-6">
                    <h1 className="truncate text-sm font-medium text-(--text-main)">
                        {threads.find(t => t.id === selectedThreadId)?.title ?? "New conversation"}
                    </h1>
                    <div className="flex items-center gap-2">
                        {ragMode && (
                            <span className="flex items-center gap-1.5 rounded-md bg-blue-50 px-2.5 py-1 text-xs font-medium text-blue-700">
                                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><polyline points="14 2 14 8 20 8" /></svg>
                                Document mode
                                <button onClick={toggleRagMode} className="ml-1 text-blue-400 hover:text-blue-700">×</button>
                            </span>
                        )}
                        {sqlMode && (
                            <span className="flex items-center gap-1.5 rounded-md bg-indigo-50 px-2.5 py-1 text-xs font-medium text-indigo-700">
                                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><ellipse cx="12" cy="5" rx="9" ry="3" /><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3" /><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5" /></svg>
                                Database mode
                                <button onClick={toggleSqlMode} className="ml-1 text-indigo-400 hover:text-indigo-700">×</button>
                            </span>
                        )}
                        {sheetsMode && (
                            <span className="flex items-center gap-1.5 rounded-md bg-green-50 px-2.5 py-1 text-xs font-medium text-green-700">
                                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2" /><line x1="3" y1="9" x2="21" y2="9" /><line x1="9" y1="3" x2="9" y2="21" /></svg>
                                Spreadsheet mode
                                <button onClick={toggleSheetsMode} className="ml-1 text-green-400 hover:text-green-700">×</button>
                            </span>
                        )}
                        {researchMode && (
                            <span className="flex items-center gap-1.5 rounded-md bg-amber-50 px-2.5 py-1 text-xs font-medium text-amber-700">
                                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" /><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" /></svg>
                                Research mode
                                <button onClick={toggleResearchMode} className="ml-1 text-amber-400 hover:text-amber-700">×</button>
                            </span>
                        )}
                    </div>
                </header>

                {errorMessage && (
                    <div className="border-b border-amber-200 bg-amber-50 px-5 py-2.5 text-sm text-amber-800">
                        {errorMessage}
                    </div>
                )}

                <MessageList
                    messages={messages}
                    isLoading={isLoading || isHistoryLoading}
                    onSelectImage={handleSelectImage}
                    selectedImageId={selectedImageId}
                    onEditImage={editImage}
                />
                <InputBar
                    onSend={
                        researchMode
                            ? sendResearchMessage
                            : sheetsMode
                                ? (msg: string) => sendSheetsMessage(msg, "google_sheet")
                                : (sqlMode ? sendSqlMessage : (ragMode ? sendRagMessage : sendMessage))
                    }
                    onGenerateImage={generateImage}
                    onEditImage={editImage}
                    selectedImageId={selectedImageId}
                    onDeselectImage={() => setSelectedImageId(null)}
                    isLoading={isLoading}
                    ragMode={ragMode}
                    onToggleRag={toggleRagMode}
                    sqlMode={sqlMode}
                    onToggleSql={toggleSqlMode}
                    sheetsMode={sheetsMode}
                    onToggleSheets={toggleSheetsMode}
                    onSendSheets={(msg, sourceType, sheetUrl) => sendSheetsMessage(msg, sourceType, sheetUrl)}
                    researchMode={researchMode}
                    onToggleResearch={toggleResearchMode}
                />
            </section>

            {renameModalThreadId && (
                <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/40 p-4">
                    <div className="w-full max-w-sm rounded-xl border border-(--line) bg-white p-6 shadow-lg">
                        <h2 className="text-base font-semibold text-(--text-main)">Rename thread</h2>
                        <input
                            value={renameInput}
                            onChange={(e) => setRenameInput(e.target.value)}
                            className="mt-4 w-full rounded-lg border border-(--line) bg-white px-3 py-2.5 text-sm outline-none transition focus:border-(--text-main) focus:ring-1 focus:ring-(--text-main)"
                            placeholder="Thread title"
                        />
                        <div className="mt-4 flex justify-end gap-2">
                            <button
                                onClick={() => {
                                    setRenameModalThreadId(null);
                                    setRenameInput("");
                                }}
                                className="rounded-lg border border-(--line) px-4 py-2 text-sm font-medium text-(--text-soft) hover:bg-(--surface-soft)"
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
                                className="rounded-lg bg-(--text-main) px-4 py-2 text-sm font-medium text-white hover:bg-black"
                            >
                                Save
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {deleteModalThreadId && (
                <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/40 p-4">
                    <div className="w-full max-w-sm rounded-xl border border-(--line) bg-white p-6 shadow-lg">
                        <h2 className="text-base font-semibold text-(--text-main)">Delete thread</h2>
                        <p className="mt-2 text-sm text-(--text-soft)">This will permanently remove the thread and its messages.</p>
                        <div className="mt-4 flex justify-end gap-2">
                            <button
                                onClick={() => setDeleteModalThreadId(null)}
                                className="rounded-lg border border-(--line) px-4 py-2 text-sm font-medium text-(--text-soft) hover:bg-(--surface-soft)"
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
                                className="rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700"
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
