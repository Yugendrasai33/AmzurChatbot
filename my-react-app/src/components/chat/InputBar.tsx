import { useState, useRef, useCallback, type FormEvent, type ChangeEvent } from "react";
import { FilePreview } from "../attachments/FilePreview";
import { InputActionPopover } from "./InputActionPopover";

const MAX_UPLOAD_MB = 20;

interface InputBarProps {
    onSend: (message: string, files?: File[]) => void;
    onGenerateImage?: (prompt: string) => void;
    onEditImage?: (attachmentId: string, editPrompt: string) => void;
    selectedImageId?: string | null;
    onDeselectImage?: () => void;
    isLoading: boolean;
    ragMode?: boolean;
    onToggleRag?: () => void;
    sqlMode?: boolean;
    onToggleSql?: () => void;
    sheetsMode?: boolean;
    onToggleSheets?: () => void;
    onSendSheets?: (message: string, sourceType: string, sheetUrl?: string) => void;
    researchMode?: boolean;
    onToggleResearch?: () => void;
    onOpenGame?: () => void;
    onOpenTickets?: () => void;
}

export function InputBar({
    onSend,
    onGenerateImage,
    onEditImage,
    selectedImageId,
    onDeselectImage,
    isLoading,
    ragMode,
    onToggleRag,
    sqlMode,
    onToggleSql,
    sheetsMode,
    onToggleSheets,
    onSendSheets,
    researchMode,
    onToggleResearch,
    onOpenGame,
    onOpenTickets,
}: InputBarProps) {
    const [input, setInput] = useState("");
    const [files, setFiles] = useState<File[]>([]);
    const [popoverOpen, setPopoverOpen] = useState(false);
    const [generateMode, setGenerateMode] = useState(false);
    const [sheetUrl, setSheetUrl] = useState("");
    const fileInputRef = useRef<HTMLInputElement>(null);
    const plusButtonRef = useRef<HTMLButtonElement>(null);
    const textInputRef = useRef<HTMLInputElement>(null);

    const handleSubmit = (e: FormEvent) => {
        e.preventDefault();
        const trimmed = input.trim();
        if ((!trimmed && files.length === 0) || isLoading) return;

        // When an image is selected, ALL text goes as an edit prompt.
        if (trimmed && selectedImageId && onEditImage && files.length === 0) {
            onEditImage(selectedImageId, trimmed);
            setInput("");
            return;
        }

        // When in generate-image mode, treat text as image generation prompt.
        if (trimmed && generateMode && onGenerateImage) {
            onGenerateImage(trimmed);
            setInput("");
            setGenerateMode(false);
            return;
        }

        // Also keep slash-command compatibility.
        if (trimmed.startsWith("/image ")) {
            const prompt = trimmed.substring(7).trim();
            if (prompt && onGenerateImage) {
                onGenerateImage(prompt);
                setInput("");
                return;
            }
        }

        onSend(trimmed || "(attachment)", files.length > 0 ? files : undefined);
        setInput("");
        setFiles([]);
    };

    const handleSheetsSubmit = (e: FormEvent) => {
        e.preventDefault();
        const trimmed = input.trim();
        if (!trimmed || isLoading || !onSendSheets) return;
        onSendSheets(trimmed, "google_sheet", sheetUrl.trim() || undefined);
        setInput("");
    };

    const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
        if (!e.target.files) return;
        const selected = Array.from(e.target.files);
        const valid = selected.filter((f) => {
            if (f.size > MAX_UPLOAD_MB * 1024 * 1024) {
                alert(`"${f.name}" exceeds ${MAX_UPLOAD_MB}MB limit`);
                return false;
            }
            return true;
        });
        setFiles((prev) => [...prev, ...valid]);
        e.target.value = "";
    };

    const removeFile = (index: number) => {
        setFiles((prev) => prev.filter((_, i) => i !== index));
    };

    const handleAttachFiles = useCallback(() => {
        fileInputRef.current?.click();
    }, []);

    const handleGenerateImageAction = useCallback(() => {
        setGenerateMode(true);
        setInput("");
        setTimeout(() => textInputRef.current?.focus(), 0);
    }, []);

    return (
        <form onSubmit={sheetsMode ? handleSheetsSubmit : handleSubmit} className="border-t border-(--line) bg-white px-4 py-4 sm:px-6">
            <div className="mx-auto w-full max-w-3xl">
                {/* Sheet URL input */}
                {sheetsMode && (
                    <div className="mb-2">
                        <input
                            type="url"
                            value={sheetUrl}
                            onChange={(e) => setSheetUrl(e.target.value)}
                            placeholder="Paste Google Sheet URL (must be shared with the service account)…"
                            className="w-full rounded-lg border border-green-200 bg-green-50/50 px-3 py-2 text-sm text-(--text-main) placeholder:text-green-400 focus:border-green-400 focus:outline-none"
                        />
                    </div>
                )}

                {/* Selected image indicator */}
                {selectedImageId && (
                    <div className="mb-2 flex items-center gap-2 rounded-lg bg-(--surface-soft) px-3 py-2 text-xs text-(--text-soft)">
                        <span>Image selected — type your edit prompt below</span>
                        <button
                            type="button"
                            onClick={onDeselectImage}
                            className="ml-auto text-(--text-muted) hover:text-(--text-main)"
                        >
                            ×
                        </button>
                    </div>
                )}

                <FilePreview files={files} onRemove={removeFile} />
                <div className="flex items-end gap-2 rounded-xl border border-(--line) bg-white p-2 shadow-sm transition focus-within:border-(--text-muted) focus-within:shadow-md">
                    {/* Plus button with popover */}
                    <div className="relative shrink-0">
                        <button
                            ref={plusButtonRef}
                            type="button"
                            onClick={() => setPopoverOpen((prev) => !prev)}
                            aria-haspopup="menu"
                            aria-expanded={popoverOpen}
                            aria-label="Attach or generate"
                            className="flex h-9 w-9 items-center justify-center rounded-lg text-(--text-muted) transition hover:bg-(--surface-soft) hover:text-(--text-main) disabled:opacity-40"
                            disabled={isLoading}
                        >
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" /></svg>
                        </button>
                        {popoverOpen && (
                            <InputActionPopover
                                anchorRef={plusButtonRef}
                                onAttachFiles={handleAttachFiles}
                                onGenerateImage={handleGenerateImageAction}
                                onDocSearch={onToggleRag ?? (() => { })}
                                onDbQuery={onToggleSql ?? (() => { })}
                                onSheetAnalyze={onToggleSheets ?? (() => { })}
                                onResearch={onToggleResearch ?? (() => { })}
                                onOpenGame={onOpenGame}
                                onOpenTickets={onOpenTickets}
                                onClose={() => setPopoverOpen(false)}
                                ragMode={ragMode}
                                sqlMode={sqlMode}
                                sheetsMode={sheetsMode}
                                researchMode={researchMode}
                            />
                        )}
                    </div>

                    <input
                        ref={fileInputRef}
                        type="file"
                        multiple
                        className="hidden"
                        onChange={handleFileChange}
                        accept="image/*,video/mp4,video/webm,video/quicktime,.mov,.pdf,.txt,.py,.js,.ts,.html,.css,.md,.json,.csv,.xlsx,.xls,.doc,.docx"
                    />

                    {/* RAG mode tag */}
                    {ragMode && !selectedImageId && !generateMode && (
                        <div className="flex shrink-0 items-center gap-1.5 rounded-full bg-blue-50 border border-blue-200 px-2.5 py-1">
                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-blue-500">
                                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                                <polyline points="14 2 14 8 20 8" />
                            </svg>
                            <span className="text-xs font-medium text-blue-700">Search documents</span>
                            <button
                                type="button"
                                onClick={onToggleRag}
                                className="ml-0.5 text-blue-400 hover:text-blue-700"
                                aria-label="Exit document mode"
                            >
                                ×
                            </button>
                        </div>
                    )}

                    {/* SQL mode tag */}
                    {sqlMode && !selectedImageId && !generateMode && (
                        <div className="flex shrink-0 items-center gap-1.5 rounded-full bg-indigo-50 border border-indigo-200 px-2.5 py-1">
                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-indigo-500">
                                <ellipse cx="12" cy="5" rx="9" ry="3" />
                                <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3" />
                                <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5" />
                            </svg>
                            <span className="text-xs font-medium text-indigo-700">Query database</span>
                            <button
                                type="button"
                                onClick={onToggleSql}
                                className="ml-0.5 text-indigo-400 hover:text-indigo-700"
                                aria-label="Exit database mode"
                            >
                                ×
                            </button>
                        </div>
                    )}

                    {/* Sheets mode tag */}
                    {sheetsMode && !selectedImageId && !generateMode && (
                        <div className="flex shrink-0 items-center gap-1.5 rounded-full bg-green-50 border border-green-200 px-2.5 py-1">
                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-green-500">
                                <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
                                <line x1="3" y1="9" x2="21" y2="9" />
                                <line x1="3" y1="15" x2="21" y2="15" />
                                <line x1="9" y1="3" x2="9" y2="21" />
                            </svg>
                            <span className="text-xs font-medium text-green-700">Analyze spreadsheet</span>
                            <button
                                type="button"
                                onClick={onToggleSheets}
                                className="ml-0.5 text-green-400 hover:text-green-700"
                                aria-label="Exit sheets mode"
                            >
                                ×
                            </button>
                        </div>
                    )}

                    {/* Research mode tag */}
                    {researchMode && !selectedImageId && !generateMode && (
                        <div className="flex shrink-0 items-center gap-1.5 rounded-full bg-amber-50 border border-amber-200 px-2.5 py-1">
                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-amber-500">
                                <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
                                <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
                            </svg>
                            <span className="text-xs font-medium text-amber-700">Research papers</span>
                            <button
                                type="button"
                                onClick={onToggleResearch}
                                className="ml-0.5 text-amber-400 hover:text-amber-700"
                                aria-label="Exit research mode"
                            >
                                ×
                            </button>
                        </div>
                    )}

                    {/* Generate image mode tag */}
                    {generateMode && !selectedImageId && (
                        <div className="flex shrink-0 items-center gap-1 rounded-md bg-purple-50 px-2 py-1">
                            <span className="text-xs font-medium text-purple-700">Image</span>
                            <button
                                type="button"
                                onClick={() => setGenerateMode(false)}
                                className="text-xs text-purple-400 hover:text-purple-700"
                                aria-label="Cancel generate image"
                            >
                                ×
                            </button>
                        </div>
                    )}

                    <input
                        ref={textInputRef}
                        type="text"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        placeholder={selectedImageId
                            ? "Describe what to change…"
                            : (generateMode
                                ? "Describe the image to generate…"
                                : (researchMode
                                    ? "Enter a research topic…"
                                    : (sheetsMode
                                        ? "Ask a question about the spreadsheet…"
                                        : (sqlMode
                                            ? "Ask a question about the database…"
                                            : (ragMode
                                                ? "Ask about your documents…"
                                                : "Message Amzur AI…")))))}
                        className="min-h-9 flex-1 bg-transparent px-1 text-sm text-(--text-main) placeholder:text-(--text-muted) focus:outline-none"
                        disabled={isLoading}
                    />

                    <button
                        type="submit"
                        disabled={isLoading || (!input.trim() && files.length === 0)}
                        className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-(--text-main) text-white transition hover:bg-black disabled:opacity-30"
                    >
                        {isLoading ? (
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="animate-spin"><circle cx="12" cy="12" r="10" strokeDasharray="32" strokeDashoffset="12" /></svg>
                        ) : (
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="22" y1="2" x2="11" y2="13" /><polygon points="22 2 15 22 11 13 2 9 22 2" /></svg>
                        )}
                    </button>
                </div>
                <p className="mt-2 text-center text-xs text-(--text-muted)">
                    AI may produce inaccurate information. Verify important details.
                </p>
            </div>
        </form>
    );
}
