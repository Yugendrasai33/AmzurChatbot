interface FilePreviewProps {
    files: File[];
    onRemove: (index: number) => void;
}

export function FilePreview({ files, onRemove }: FilePreviewProps) {
    if (files.length === 0) return null;

    return (
        <div className="mb-2 flex flex-wrap gap-2">
            {files.map((file, index) => (
                <div
                    key={`${file.name}-${index}`}
                    className="group relative flex items-center gap-2.5 rounded-lg border border-(--line) bg-(--surface-soft) px-3 py-2 text-sm"
                >
                    {file.type.startsWith("image/") ? (
                        <img
                            src={URL.createObjectURL(file)}
                            alt={file.name}
                            className="h-9 w-9 rounded-md object-cover"
                        />
                    ) : (
                        <span className="flex h-9 w-9 items-center justify-center rounded-md bg-white text-base">{getFileIcon(file.type)}</span>
                    )}
                    <div className="min-w-0">
                        <p className="max-w-36 truncate text-xs font-medium text-(--text-main)">
                            {file.name}
                        </p>
                        <p className="text-xs text-(--text-muted)">
                            {(file.size / 1024).toFixed(0)} KB
                        </p>
                    </div>
                    <button
                        type="button"
                        onClick={() => onRemove(index)}
                        className="ml-1 flex h-5 w-5 items-center justify-center rounded-full text-xs text-(--text-muted) transition hover:bg-red-100 hover:text-red-600 sm:opacity-0 sm:group-hover:opacity-100"
                        aria-label={`Remove ${file.name}`}
                    >
                        ×
                    </button>
                </div>
            ))}
        </div>
    );
}

function getFileIcon(mimeType: string): string {
    if (mimeType.startsWith("video/")) return "🎬";
    if (mimeType === "application/pdf") return "📕";
    if (mimeType === "text/csv" || mimeType.includes("spreadsheet")) return "📊";
    if (mimeType.startsWith("text/") || mimeType === "application/json") return "📄";
    return "📎";
}
