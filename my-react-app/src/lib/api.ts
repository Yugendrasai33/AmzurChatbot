import axios from "axios";
import { z } from "zod";
import {
    type AttachmentMeta,
    type AuthResponse,
    type AuthUser,
    type ChatMessage,
    type ChatSendResponse,
    type ImageEditRequest,
    type ImageGenerationRequest,
    type IngestResponse,
    type ResearchEvent,
    type ResearchMeta,
    type ResearchSection,
    type SheetMetaData,
    type SqlResultData,
    type Thread,
} from "../types";

const api = axios.create({
    baseURL: "/api",
    headers: {
        "Content-Type": "application/json",
    },
    withCredentials: true,
});

api.interceptors.request.use((config) => {
    const token = localStorage.getItem("auth_token");
    if (token) {
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
});

export const authApi = {
    signup: async (payload: { email: string; password: string; full_name?: string }) => {
        const { data } = await api.post<AuthResponse>("/auth/signup", payload);
        return data;
    },
    login: async (payload: { email: string; password: string }) => {
        const { data } = await api.post<AuthResponse>("/auth/login", payload);
        return data;
    },
    me: async () => {
        const { data } = await api.get<AuthUser>("/auth/me");
        return data;
    },
    googleLoginUrl: () => "/api/auth/google/login",
};

export const chatApi = {
    listThreads: async () => {
        const { data } = await api.get<Thread[]>("/threads");
        return data;
    },
    createThread: async (payload?: { title?: string }) => {
        const { data } = await api.post<Thread>("/threads", payload ?? {});
        return data;
    },
    renameThread: async (threadId: string, title: string) => {
        const { data } = await api.put<Thread>(`/threads/${threadId}`, { title });
        return data;
    },
    deleteThread: async (threadId: string) => {
        const { data } = await api.delete<{ deleted: boolean }>(`/threads/${threadId}`);
        return data;
    },
    getThreadMessages: async (threadId: string) => {
        const { data } = await api.get<ChatMessage[]>(`/chat/threads/${threadId}/messages`);
        return data;
    },
    sendMessage: async (payload: { message: string; thread_id?: string | null; attachment_ids?: string[] }) => {
        const { data } = await api.post<ChatSendResponse>("/chat/messages", payload);
        return data;
    },
    uploadFile: async (file: File): Promise<AttachmentMeta> => {
        const formData = new FormData();
        formData.append("file", file);
        const { data } = await api.post<AttachmentMeta>("/chat/upload", formData, {
            headers: { "Content-Type": "multipart/form-data" },
        });
        return data;
    },
    generateImage: async (prompt: string, threadId?: string | null): Promise<AttachmentMeta> => {
        const payload: ImageGenerationRequest = { prompt, thread_id: threadId ?? null };
        const { data } = await api.post<AttachmentMeta>("/chat/generate-image", payload);
        return data;
    },
    editImage: async (attachmentId: string, editPrompt: string, threadId?: string | null): Promise<AttachmentMeta> => {
        const payload: ImageEditRequest = { attachment_id: attachmentId, edit_prompt: editPrompt, thread_id: threadId ?? null };
        const { data } = await api.post<AttachmentMeta>("/chat/edit-image", payload);
        return data;
    },
};

export const ragApi = {
    ingestAttachment: async (attachmentId: string): Promise<IngestResponse> => {
        const { data } = await api.post<IngestResponse>(`/rag/ingest/${attachmentId}`);
        return data;
    },

    streamRag: async (
        threadId: string,
        message: string,
        onToken: (token: string) => void,
        onSources?: (sources: string[]) => void,
        attachmentIds?: string[],
    ): Promise<void> => {
        const token = localStorage.getItem("auth_token");
        const response = await fetch("/api/rag/stream", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                ...(token ? { Authorization: `Bearer ${token}` } : {}),
            },
            body: JSON.stringify({
                thread_id: threadId,
                message,
                attachment_ids: attachmentIds?.length ? attachmentIds : undefined,
            }),
        });

        if (!response.ok) {
            const errorBody = await response.json().catch(() => null);
            const detail = errorBody?.detail;
            const msg = typeof detail === "string"
                ? detail
                : detail?.message ?? "RAG query failed.";
            throw new Error(msg);
        }

        const reader = response.body?.getReader();
        if (!reader) throw new Error("No response stream available.");

        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split("\n");
            buffer = lines.pop() ?? "";

            for (const line of lines) {
                if (!line.startsWith("data: ")) continue;
                const payload = line.slice(6);
                if (payload === "[DONE]") return;
                // Check for error marker
                if (payload.startsWith("[ERROR] ")) {
                    throw new Error(payload.slice(8));
                }
                // Check for sources marker
                if (payload.includes("[SOURCES]")) {
                    const idx = payload.indexOf("[SOURCES]");
                    const textBefore = payload.slice(0, idx);
                    if (textBefore) onToken(textBefore);
                    const sourcesJson = payload.slice(idx + "[SOURCES]".length);
                    try {
                        const sources = JSON.parse(sourcesJson);
                        if (onSources) onSources(sources);
                    } catch { /* ignore parse errors */ }
                    continue;
                }
                onToken(payload);
            }
        }
    },
};

export const sqlApi = {
    streamQuery: async (
        threadId: string,
        question: string,
        onToken: (token: string) => void,
        onSql?: (sqlQuery: string) => void,
        onSqlResult?: (result: SqlResultData) => void,
    ): Promise<void> => {
        const token = localStorage.getItem("auth_token");
        const response = await fetch("/api/sql/query", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                ...(token ? { Authorization: `Bearer ${token}` } : {}),
            },
            body: JSON.stringify({ thread_id: threadId, question }),
        });

        if (!response.ok) {
            const errorBody = await response.json().catch(() => null);
            const detail = errorBody?.detail;
            const msg = typeof detail === "string"
                ? detail
                : detail?.message ?? "Database query failed.";
            throw new Error(msg);
        }

        const reader = response.body?.getReader();
        if (!reader) throw new Error("No response stream available.");

        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split("\n");
            buffer = lines.pop() ?? "";

            for (const line of lines) {
                if (!line.startsWith("data: ")) continue;
                const payload = line.slice(6);
                if (payload === "[DONE]") return;
                if (payload.startsWith("[ERROR] ")) {
                    throw new Error(payload.slice(8));
                }
                if (payload.includes("[SQL]")) {
                    const idx = payload.indexOf("[SQL]");
                    const textBefore = payload.slice(0, idx);
                    if (textBefore) onToken(textBefore);
                    const sqlJson = payload.slice(idx + "[SQL]".length);
                    try {
                        const sqlQuery = JSON.parse(sqlJson);
                        if (onSql) onSql(sqlQuery);
                    } catch { /* ignore parse errors */ }
                    continue;
                }
                if (payload.includes("[SQL_RESULT]")) {
                    const idx = payload.indexOf("[SQL_RESULT]");
                    const textBefore = payload.slice(0, idx);
                    if (textBefore) onToken(textBefore);
                    const resultJson = payload.slice(idx + "[SQL_RESULT]".length);
                    try {
                        const result = JSON.parse(resultJson) as SqlResultData;
                        if (onSqlResult) onSqlResult(result);
                    } catch { /* ignore parse errors */ }
                    continue;
                }
                onToken(payload);
            }
        }
    },
};

export const sheetsApi = {
    streamQuery: async (
        threadId: string,
        question: string,
        sourceType: string,
        onToken: (t: string) => void,
        onSheetMeta?: (meta: SheetMetaData) => void,
        sheetUrl?: string,
        attachmentId?: string,
    ) => {
        const token = localStorage.getItem("auth_token");
        const response = await fetch("/api/sheets/query", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                ...(token ? { Authorization: `Bearer ${token}` } : {}),
            },
            credentials: "include",
            body: JSON.stringify({
                thread_id: threadId,
                question,
                source_type: sourceType,
                sheet_url: sheetUrl ?? null,
                attachment_id: attachmentId ?? null,
            }),
        });

        if (!response.ok) {
            const detail = await response.json().then((d) => d.detail).catch(() => null);
            const msg = typeof detail === "string"
                ? detail
                : detail?.message ?? "Spreadsheet query failed.";
            throw new Error(msg);
        }

        const reader = response.body?.getReader();
        if (!reader) throw new Error("No response stream available.");

        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split("\n");
            buffer = lines.pop() ?? "";

            for (const line of lines) {
                if (!line.startsWith("data: ")) continue;
                const payload = line.slice(6);
                if (payload === "[DONE]") return;
                if (payload.startsWith("[ERROR] ")) {
                    throw new Error(payload.slice(8));
                }
                if (payload.includes("[SHEET_META]")) {
                    const idx = payload.indexOf("[SHEET_META]");
                    const textBefore = payload.slice(0, idx);
                    if (textBefore) onToken(textBefore);
                    const metaJson = payload.slice(idx + "[SHEET_META]".length);
                    try {
                        const meta = JSON.parse(metaJson) as SheetMetaData;
                        if (onSheetMeta) onSheetMeta(meta);
                    } catch { /* ignore */ }
                    continue;
                }
                onToken(payload + "\n");
            }
        }
    },
};

// ----------------------------------------------------------------------
// Research (Project 10) — SSE stream of decompose → search → synthesize.
// Payloads are newline-delimited JSON ResearchEvent objects, validated
// with zod before being passed to callbacks.
// ----------------------------------------------------------------------

const researchSectionIdSchema = z.enum([
    "overview",
    "key_papers",
    "themes",
    "gaps",
    "future",
    "references",
    "error",
]);

const researchEventSchema = z.discriminatedUnion("event", [
    z.object({ event: z.literal("status"), message: z.string() }),
    z.object({
        event: z.literal("section"),
        id: researchSectionIdSchema,
        title: z.string(),
        content: z.string(),
    }),
    z.object({
        event: z.literal("done"),
        total_papers: z.number(),
        coverage: z.number(),
    }),
]);

export const researchApi = {
    streamResearch: async (
        threadId: string,
        topic: string,
        onStatus: (message: string) => void,
        onSection: (section: ResearchSection) => void,
        onDone: (meta: ResearchMeta) => void,
        onError: (message: string) => void,
    ): Promise<void> => {
        const token = localStorage.getItem("auth_token");
        const response = await fetch("/api/research/query", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                ...(token ? { Authorization: `Bearer ${token}` } : {}),
            },
            credentials: "include",
            body: JSON.stringify({ thread_id: threadId, topic }),
        });

        if (!response.ok) {
            const detail = await response.json().then((d) => d.detail).catch(() => null);
            const msg = typeof detail === "string"
                ? detail
                : detail?.message ?? "Research request failed.";
            throw new Error(msg);
        }

        const reader = response.body?.getReader();
        if (!reader) throw new Error("No response stream available.");

        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split("\n");
            buffer = lines.pop() ?? "";

            for (const line of lines) {
                if (!line.startsWith("data: ")) continue;
                const payload = line.slice(6);
                if (!payload) continue;
                if (payload === "[DONE]") return;
                if (payload.startsWith("[ERROR] ")) {
                    onError(payload.slice(8));
                    continue;
                }

                let parsed: unknown;
                try {
                    parsed = JSON.parse(payload);
                } catch {
                    continue;
                }

                const result = researchEventSchema.safeParse(parsed);
                if (!result.success) continue;
                const evt: ResearchEvent = result.data;

                if (evt.event === "status") {
                    onStatus(evt.message);
                } else if (evt.event === "section") {
                    onSection({ id: evt.id, title: evt.title, content: evt.content });
                } else if (evt.event === "done") {
                    onDone({ total_papers: evt.total_papers, coverage: evt.coverage });
                }
            }
        }
    },
};

// ── Tic Tac Toe Game API ──

export const gameApi = {
    startGame: async (difficulty: string = "hard") => {
        const { data } = await api.post<import("../types").GameStartResponse>("/game/start", { difficulty });
        return data;
    },
    makeMove: async (gameId: string, row: number, col: number) => {
        const { data } = await api.post<import("../types").GameMoveResponse>("/game/move", {
            game_id: gameId,
            row,
            col,
        });
        return data;
    },
    restartGame: async (gameId: string) => {
        const { data } = await api.post<import("../types").GameStartResponse>(`/game/restart/${gameId}`);
        return data;
    },
    getHistory: async () => {
        const { data } = await api.get<import("../types").GameScoreResponse>("/game/history");
        return data;
    },
};

export default api;
