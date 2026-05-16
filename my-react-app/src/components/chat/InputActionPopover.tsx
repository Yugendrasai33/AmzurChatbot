import { useEffect, useRef } from "react";

interface InputActionPopoverProps {
    anchorRef: React.RefObject<HTMLButtonElement | null>;
    onAttachFiles: () => void;
    onGenerateImage: () => void;
    onDocSearch: () => void;
    onDbQuery: () => void;
    onSheetAnalyze: () => void;
    onResearch: () => void;
    onOpenGame?: () => void;
    onClose: () => void;
    ragMode?: boolean;
    sqlMode?: boolean;
    sheetsMode?: boolean;
    researchMode?: boolean;
}

export function InputActionPopover({
    anchorRef,
    onAttachFiles,
    onGenerateImage,
    onDocSearch,
    onDbQuery,
    onSheetAnalyze,
    onResearch,
    onOpenGame,
    onClose,
    ragMode,
    sqlMode,
    sheetsMode,
    researchMode,
}: InputActionPopoverProps) {
    const popoverRef = useRef<HTMLDivElement>(null);

    // Close on outside click
    useEffect(() => {
        const handler = (e: MouseEvent) => {
            if (
                popoverRef.current &&
                !popoverRef.current.contains(e.target as Node) &&
                anchorRef.current &&
                !anchorRef.current.contains(e.target as Node)
            ) {
                onClose();
            }
        };
        document.addEventListener("mousedown", handler);
        return () => document.removeEventListener("mousedown", handler);
    }, [anchorRef, onClose]);

    // Close on Escape
    useEffect(() => {
        const handler = (e: KeyboardEvent) => {
            if (e.key === "Escape") onClose();
        };
        document.addEventListener("keydown", handler);
        return () => document.removeEventListener("keydown", handler);
    }, [onClose]);

    const handleAttach = () => {
        onAttachFiles();
        onClose();
    };

    const handleGenerateImage = () => {
        onGenerateImage();
        onClose();
    };

    const handleDocSearch = () => {
        onDocSearch();
        onClose();
    };

    const handleDbQuery = () => {
        onDbQuery();
        onClose();
    };

    const handleSheetAnalyze = () => {
        onSheetAnalyze();
        onClose();
    };

    const handleResearch = () => {
        onResearch();
        onClose();
    };

    return (
        <div
            ref={popoverRef}
            role="menu"
            aria-label="Attachment actions"
            className="absolute bottom-full left-0 mb-2 z-50 min-w-44 overflow-hidden rounded-lg border border-(--line) bg-white shadow-lg"
        >
            <button
                type="button"
                role="menuitem"
                onClick={handleAttach}
                className="flex w-full items-center gap-3 px-3 py-2.5 text-left text-sm text-(--text-main) transition hover:bg-(--surface-soft)"
            >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-(--text-muted)"><path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48" /></svg>
                Attach files
            </button>
            <div className="mx-2 h-px bg-(--line)" />
            <button
                type="button"
                role="menuitem"
                onClick={handleGenerateImage}
                className="flex w-full items-center gap-3 px-3 py-2.5 text-left text-sm text-(--text-main) transition hover:bg-(--surface-soft)"
            >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-(--text-muted)"><rect x="3" y="3" width="18" height="18" rx="2" ry="2" /><circle cx="8.5" cy="8.5" r="1.5" /><polyline points="21 15 16 10 5 21" /></svg>
                Generate image
            </button>
            <div className="mx-2 h-px bg-(--line)" />
            <button
                type="button"
                role="menuitem"
                onClick={handleDocSearch}
                className={`flex w-full items-center gap-3 px-3 py-2.5 text-left text-sm transition hover:bg-(--surface-soft) ${ragMode ? "text-blue-600 font-medium" : "text-(--text-main)"}`}
            >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={ragMode ? "text-blue-500" : "text-(--text-muted)"}>
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                    <polyline points="14 2 14 8 20 8" />
                </svg>
                Search documents
                {ragMode && <span className="ml-auto text-xs text-blue-400">✓</span>}
            </button>
            <div className="mx-2 h-px bg-(--line)" />
            <button
                type="button"
                role="menuitem"
                onClick={handleDbQuery}
                className={`flex w-full items-center gap-3 px-3 py-2.5 text-left text-sm transition hover:bg-(--surface-soft) ${sqlMode ? "text-indigo-600 font-medium" : "text-(--text-main)"}`}
            >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={sqlMode ? "text-indigo-500" : "text-(--text-muted)"}>
                    <ellipse cx="12" cy="5" rx="9" ry="3" />
                    <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3" />
                    <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5" />
                </svg>
                Query database
                {sqlMode && <span className="ml-auto text-xs text-indigo-400">✓</span>}
            </button>
            <div className="mx-2 h-px bg-(--line)" />
            <button
                type="button"
                role="menuitem"
                onClick={handleSheetAnalyze}
                className={`flex w-full items-center gap-3 px-3 py-2.5 text-left text-sm transition hover:bg-(--surface-soft) ${sheetsMode ? "text-green-600 font-medium" : "text-(--text-main)"}`}
            >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={sheetsMode ? "text-green-500" : "text-(--text-muted)"}>
                    <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
                    <line x1="3" y1="9" x2="21" y2="9" />
                    <line x1="3" y1="15" x2="21" y2="15" />
                    <line x1="9" y1="3" x2="9" y2="21" />
                    <line x1="15" y1="3" x2="15" y2="21" />
                </svg>
                Analyze spreadsheet
                {sheetsMode && <span className="ml-auto text-xs text-green-400">✓</span>}
            </button>
            <div className="mx-2 h-px bg-(--line)" />
            <button
                type="button"
                role="menuitem"
                onClick={handleResearch}
                className={`flex w-full items-center gap-3 px-3 py-2.5 text-left text-sm transition hover:bg-(--surface-soft) ${researchMode ? "text-amber-600 font-medium" : "text-(--text-main)"}`}
            >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={researchMode ? "text-amber-500" : "text-(--text-muted)"}>
                    <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
                    <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
                </svg>
                Research papers
                {researchMode && <span className="ml-auto text-xs text-amber-400">✓</span>}
            </button>
            {onOpenGame && (
                <>
                    <div className="mx-2 h-px bg-(--line)" />
                    <button
                        type="button"
                        role="menuitem"
                        onClick={() => { onOpenGame(); onClose(); }}
                        className="flex w-full items-center gap-3 px-3 py-2.5 text-left text-sm text-(--text-main) transition hover:bg-(--surface-soft)"
                    >
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-(--text-muted)">
                            <rect x="3" y="3" width="7" height="7" /><rect x="14" y="3" width="7" height="7" /><rect x="3" y="14" width="7" height="7" /><rect x="14" y="14" width="7" height="7" />
                        </svg>
                        Tic Tac Toe
                    </button>
                </>
            )}
        </div>
    );
}
