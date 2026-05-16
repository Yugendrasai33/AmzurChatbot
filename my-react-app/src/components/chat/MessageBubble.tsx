import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeHighlight from "rehype-highlight";
import rehypeKatex from "rehype-katex";
import { type ChatMessage } from "../../types";
import { AttachmentRenderer } from "../attachments/AttachmentRenderer";

interface MessageBubbleProps {
    message: ChatMessage;
    onSelectImage?: (attachmentId: string) => void;
    selectedImageId?: string | null;
    onEditImage?: (attachmentId: string, editPrompt: string) => void;
}

export function MessageBubble({ message, onSelectImage, selectedImageId, onEditImage }: MessageBubbleProps) {
    const isUser = message.role === "user";

    return (
        <div className={`flex py-4 px-4 sm:px-6 ${isUser ? "justify-end" : "justify-start"}`}>
            <div className={`flex max-w-[85%] gap-3 sm:max-w-[75%] ${isUser ? "flex-row-reverse" : "flex-row"}`}>
                {/* Avatar */}
                <div className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-xs font-semibold ${isUser
                    ? "bg-(--text-main) text-white"
                    : "bg-emerald-600 text-white"
                    }`}>
                    {isUser ? "U" : "AI"}
                </div>

                {/* Content */}
                <div className="min-w-0 flex-1">
                    <p className={`mb-1 text-xs font-medium text-(--text-muted) ${isUser ? "text-right" : "text-left"}`}>
                        {isUser ? "You" : "Amzur AI"}
                    </p>
                    <div className={`rounded-2xl px-4 py-3 text-sm leading-relaxed ${isUser
                        ? "rounded-tr-sm bg-(--text-main) text-white"
                        : "rounded-tl-sm bg-(--surface-soft) text-(--text-main)"
                        }`}>
                        <div className={`prose prose-sm max-w-none text-justify ${isUser
                            ? "prose-invert text-white"
                            : "text-(--text-main)"
                            } prose-p:leading-7 prose-pre:rounded-lg prose-pre:bg-gray-900 prose-code:text-sm`}>
                            <ReactMarkdown
                                remarkPlugins={[remarkGfm, remarkMath]}
                                rehypePlugins={[rehypeHighlight, rehypeKatex]}
                            >
                                {message.content}
                            </ReactMarkdown>
                        </div>
                    </div>
                    {message.attachments && message.attachments.length > 0 && (
                        <div className="mt-2">
                            <AttachmentRenderer
                                attachments={message.attachments}
                                onSelectImage={onSelectImage}
                                selectedImageId={selectedImageId}
                                onEditImage={onEditImage}
                            />
                        </div>
                    )}
                    {message.sources && message.sources.length > 0 && (
                        <div className={`mt-2 ${isUser ? "text-right" : ""}`}>
                            <p className="text-xs font-medium text-(--text-muted)">Sources</p>
                            <div className={`mt-1 flex flex-wrap gap-1.5 ${isUser ? "justify-end" : ""}`}>
                                {message.sources.map((source, idx) => (
                                    <span
                                        key={idx}
                                        className="inline-flex items-center gap-1 rounded-md bg-(--surface-soft) px-2 py-1 text-xs font-medium text-(--text-soft) ring-1 ring-(--line)"
                                    >
                                        {source}
                                    </span>
                                ))}
                            </div>
                        </div>
                    )}
                    {message.sql_query && (
                        <details className="mt-3 rounded-lg border border-(--line) bg-(--surface-soft)">
                            <summary className="cursor-pointer select-none px-3 py-2 text-xs font-medium text-(--text-soft) hover:text-(--text-main)">
                                <span className="inline-flex items-center gap-1.5">
                                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="16 18 22 12 16 6" /><polyline points="8 6 2 12 8 18" /></svg>
                                    SQL Query
                                </span>
                            </summary>
                            <pre className="overflow-x-auto border-t border-(--line) bg-gray-900 px-4 py-3 text-xs leading-relaxed text-emerald-400 font-mono rounded-b-lg">
                                <code>{message.sql_query}</code>
                            </pre>
                        </details>
                    )}
                    {message.sql_result && message.sql_result.columns.length > 0 && (
                        <div className="mt-3 overflow-hidden rounded-lg border border-(--line)">
                            <div className="overflow-x-auto">
                                <table className="w-full border-collapse text-left text-xs">
                                    <thead>
                                        <tr className="bg-(--surface-soft)">
                                            {message.sql_result.columns.map((col, idx) => (
                                                <th
                                                    key={idx}
                                                    className="whitespace-nowrap border border-(--line) px-3 py-2 text-xs font-semibold text-(--text-main)"
                                                >
                                                    {col}
                                                </th>
                                            ))}
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {message.sql_result.rows.map((row, rowIdx) => (
                                            <tr key={rowIdx} className="bg-white hover:bg-(--surface-soft) transition-colors">
                                                {row.map((cell, cellIdx) => (
                                                    <td
                                                        key={cellIdx}
                                                        className="whitespace-nowrap border border-(--line) px-3 py-2 text-xs text-(--text-soft)"
                                                    >
                                                        {cell.length > 60 ? cell.slice(0, 60) + "…" : cell}
                                                    </td>
                                                ))}
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                            <div className="border-t border-(--line) bg-(--surface-soft) px-3 py-1.5 text-right text-xs text-(--text-muted)">
                                {message.sql_result.rows.length} row{message.sql_result.rows.length !== 1 ? "s" : ""}
                            </div>
                        </div>
                    )}
                    {message.sheet_meta && (
                        <div className="mt-2 inline-flex items-center gap-1.5 rounded-md bg-green-50 border border-green-200 px-2.5 py-1.5 text-xs text-green-700">
                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-green-500">
                                <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
                                <line x1="3" y1="9" x2="21" y2="9" />
                                <line x1="3" y1="15" x2="21" y2="15" />
                                <line x1="9" y1="3" x2="9" y2="21" />
                            </svg>
                            <span className="font-medium">{message.sheet_meta.rows} rows</span>
                            <span className="text-green-500">·</span>
                            <span>{message.sheet_meta.columns.length} columns</span>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
