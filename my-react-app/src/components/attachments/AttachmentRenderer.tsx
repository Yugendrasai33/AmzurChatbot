import { useEffect, useState, useRef, type FormEvent } from "react";
import { type AttachmentMeta } from "../../types";

/**
 * Fetches a protected media URL with the auth token and returns a blob object URL
 * that a plain <img> or <video> tag can use without needing custom headers.
 */
function useAuthedMedia(url: string): { src: string | null; error: boolean } {
    const [src, setSrc] = useState<string | null>(null);
    const [error, setError] = useState(false);

    useEffect(() => {
        let objectUrl: string | null = null;
        let cancelled = false;

        const load = async () => {
            try {
                const token = localStorage.getItem("auth_token");
                const resp = await fetch(url, {
                    headers: token ? { Authorization: `Bearer ${token}` } : {},
                });
                if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
                const blob = await resp.blob();
                if (cancelled) return;
                objectUrl = URL.createObjectURL(blob);
                setSrc(objectUrl);
            } catch {
                if (!cancelled) setError(true);
            }
        };

        void load();
        return () => {
            cancelled = true;
            if (objectUrl) URL.revokeObjectURL(objectUrl);
        };
    }, [url]);

    return { src, error };
}

interface AttachmentRendererProps {
    attachments: AttachmentMeta[];
    onSelectImage?: (attachmentId: string) => void;
    selectedImageId?: string | null;
    onEditImage?: (attachmentId: string, editPrompt: string) => void;
}

export function AttachmentRenderer({ attachments, onSelectImage, selectedImageId, onEditImage }: AttachmentRendererProps) {
    if (!attachments || attachments.length === 0) return null;

    return (
        <div className="mt-3 grid gap-3">
            {attachments.map((att) => (
                <div key={att.id}>
                    {att.type_category === "image" && <ImageAttachment attachment={att} />}
                    {att.type_category === "generated_image" && (
                        <ImageAttachment
                            attachment={att}
                            generated
                            onSelectImage={onSelectImage}
                            isSelected={selectedImageId === att.id}
                            onEditImage={onEditImage}
                        />
                    )}
                    {att.type_category === "video" && <VideoAttachment attachment={att} />}
                    {att.type_category === "pdf" && <PdfAttachment attachment={att} />}
                    {att.type_category === "code" && <FileAttachment attachment={att} icon="📄" />}
                    {att.type_category === "table" && <FileAttachment attachment={att} icon="📊" />}
                    {att.type_category === "document" && <FileAttachment attachment={att} icon="📝" />}
                </div>
            ))}
        </div>
    );
}

function ImageAttachment({
    attachment,
    generated = false,
    onSelectImage,
    isSelected = false,
    onEditImage,
}: {
    attachment: AttachmentMeta;
    generated?: boolean;
    onSelectImage?: (attachmentId: string) => void;
    isSelected?: boolean;
    onEditImage?: (attachmentId: string, editPrompt: string) => void;
}) {
    const { src, error } = useAuthedMedia(attachment.url);
    const [editInput, setEditInput] = useState("");
    const [isEditing, setIsEditing] = useState(false);
    const inputRef = useRef<HTMLInputElement>(null);

    const handleEditSubmit = (e: FormEvent) => {
        e.preventDefault();
        const trimmed = editInput.trim();
        if (!trimmed || !onEditImage) return;
        onEditImage(attachment.id, trimmed);
        setEditInput("");
        setIsEditing(false);
    };

    if (error) {
        return (
            <div className="rounded-lg border border-(--line) px-4 py-3 text-sm text-(--text-soft)">
                Could not load image: {attachment.filename}
            </div>
        );
    }

    return (
        <div className={`group overflow-hidden rounded-lg border p-1.5 transition ${isSelected
            ? "border-(--text-main) bg-gray-50 ring-1 ring-(--text-main)"
            : "border-(--line) bg-white"
            }`}>
            {src ? (
                <a href={src} target="_blank" rel="noopener noreferrer" className="block">
                    <img
                        src={src}
                        alt={attachment.filename}
                        className="max-h-72 w-full rounded-md object-cover transition hover:opacity-90"
                        loading="lazy"
                    />
                </a>
            ) : (
                <div className="flex h-32 items-center justify-center rounded-md bg-(--surface-soft) text-sm text-(--text-muted)">
                    Loading image…
                </div>
            )}
            <div className="mt-2 flex items-center justify-between gap-3 px-1">
                <div className="min-w-0">
                    <p className="truncate text-sm font-medium text-(--text-main)">{attachment.filename}</p>
                    <p className="text-xs text-(--text-soft)">{formatSize(attachment.size_bytes)}</p>
                </div>
                <div className="flex items-center gap-2">
                    {generated && onEditImage && (
                        <button
                            type="button"
                            onClick={() => {
                                setIsEditing((prev) => !prev);
                                if (onSelectImage) onSelectImage(attachment.id);
                                setTimeout(() => inputRef.current?.focus(), 0);
                            }}
                            title={isSelected ? "Selected for editing" : "Select to edit this image"}
                            className={`flex h-7 w-7 items-center justify-center rounded-md border transition ${isSelected
                                ? "border-(--text-main) bg-(--text-main) text-white"
                                : "border-(--line) bg-white text-(--text-soft) hover:border-(--text-main) hover:text-(--text-main)"
                                }`}
                        >
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                <polyline points="9 14 4 9 9 4" />
                                <path d="M20 20v-7a4 4 0 0 0-4-4H4" />
                            </svg>
                        </button>
                    )}
                    <span className="rounded-md bg-(--surface-soft) px-2 py-0.5 text-[10px] font-medium text-(--text-muted)">
                        {generated ? "AI Generated" : "image"}
                    </span>
                </div>
            </div>
            {/* Inline edit input below the image */}
            {generated && onEditImage && isEditing && (
                <form onSubmit={handleEditSubmit} className="mt-2 flex items-center gap-2 rounded-lg border border-(--line) bg-(--surface-soft) p-2">
                    <input
                        ref={inputRef}
                        type="text"
                        value={editInput}
                        onChange={(e) => setEditInput(e.target.value)}
                        placeholder="Describe what to change…"
                        className="flex-1 bg-transparent px-2 py-1 text-sm text-(--text-main) placeholder:text-(--text-muted) outline-none"
                    />
                    <button
                        type="submit"
                        disabled={!editInput.trim()}
                        className="shrink-0 rounded-md bg-(--text-main) px-3 py-1.5 text-xs font-medium text-white transition hover:bg-black disabled:opacity-40"
                    >
                        Edit
                    </button>
                    <button
                        type="button"
                        onClick={() => { setIsEditing(false); setEditInput(""); }}
                        className="shrink-0 px-2 py-1.5 text-xs text-(--text-muted) hover:text-(--text-main)"
                    >
                        ×
                    </button>
                </form>
            )}
        </div>
    );
}

function VideoAttachment({ attachment }: { attachment: AttachmentMeta }) {
    const { src, error } = useAuthedMedia(attachment.url);

    if (error) {
        return (
            <div className="rounded-lg border border-(--line) px-4 py-3 text-sm text-(--text-soft)">
                Could not load video: {attachment.filename}
            </div>
        );
    }

    return (
        <div className="overflow-hidden rounded-lg border border-(--line) bg-black">
            {src ? (
                <video controls className="max-w-full rounded-lg" preload="metadata">
                    <source src={src} type={attachment.mime_type} />
                    Your browser does not support the video tag.
                </video>
            ) : (
                <div className="flex h-32 items-center justify-center text-sm text-white/60">
                    Loading video…
                </div>
            )}
        </div>
    );
}

function PdfAttachment({ attachment }: { attachment: AttachmentMeta }) {
    return (
        <a
            href={attachment.url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex w-full items-center gap-3 rounded-lg border border-(--line) px-3 py-2.5 text-sm text-(--text-main) transition hover:bg-(--surface-soft) sm:w-auto"
        >
            <span className="flex h-8 w-8 items-center justify-center rounded-md bg-amber-50 text-base">📕</span>
            <span className="min-w-0 flex-1">
                <span className="block truncate font-medium">{attachment.filename}</span>
                <span className="text-xs text-(--text-muted)">{formatSize(attachment.size_bytes)}</span>
            </span>
        </a>
    );
}

function FileAttachment({ attachment, icon }: { attachment: AttachmentMeta; icon: string }) {
    return (
        <a
            href={attachment.url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex w-full items-center gap-3 rounded-lg border border-(--line) px-3 py-2.5 text-sm text-(--text-main) transition hover:bg-(--surface-soft) sm:w-auto"
        >
            <span className="flex h-8 w-8 items-center justify-center rounded-md bg-(--surface-soft) text-base">{icon}</span>
            <span className="min-w-0 flex-1">
                <span className="block truncate font-medium">{attachment.filename}</span>
                <span className="text-xs text-(--text-muted)">{formatSize(attachment.size_bytes)}</span>
            </span>
        </a>
    );
}

function formatSize(sizeBytes: number): string {
    if (sizeBytes < 1024) return `${sizeBytes} B`;
    if (sizeBytes < 1024 * 1024) return `${(sizeBytes / 1024).toFixed(0)} KB`;
    return `${(sizeBytes / (1024 * 1024)).toFixed(1)} MB`;
}
