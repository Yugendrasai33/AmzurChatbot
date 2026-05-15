import { useState } from "react";
import { chatApi } from "../../lib/api";
import { type AttachmentMeta } from "../../types";
import { AttachmentRenderer } from "../attachments/AttachmentRenderer";

interface ImageGeneratorProps {
    threadId?: string | null;
}

export function ImageGenerator({ threadId }: ImageGeneratorProps) {
    const [prompt, setPrompt] = useState("");
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [result, setResult] = useState<AttachmentMeta | null>(null);

    const onGenerate = async () => {
        const trimmed = prompt.trim();
        if (!trimmed) {
            setError("Please enter a prompt.");
            return;
        }

        setIsLoading(true);
        setError(null);
        try {
            const attachment = await chatApi.generateImage(trimmed, threadId ?? null);
            setResult(attachment);
        } catch {
            setError("Image generation failed. Try again.");
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <section className="rounded-2xl border border-(--line) bg-white/75 p-4">
            <div className="flex flex-col gap-3 sm:flex-row">
                <input
                    value={prompt}
                    onChange={(e) => setPrompt(e.target.value)}
                    className="h-11 flex-1 rounded-xl border border-(--line) px-3 text-sm text-(--text-main) outline-none focus:border-(--accent)"
                    placeholder="Describe the image to generate..."
                />
                <button
                    type="button"
                    onClick={onGenerate}
                    disabled={isLoading}
                    className="h-11 rounded-xl bg-(--accent) px-4 text-sm font-semibold text-white disabled:opacity-60"
                >
                    {isLoading ? "Generating image..." : "Generate"}
                </button>
            </div>
            {error && <p className="mt-3 text-sm text-red-700">{error}</p>}
            {result && (
                <div className="mt-4">
                    <AttachmentRenderer attachments={[result]} />
                </div>
            )}
        </section>
    );
}
