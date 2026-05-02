import axios from "axios";
import {
    type AuthResponse,
    type AuthUser,
    type ChatMessage,
    type ChatSendResponse,
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
    sendMessage: async (payload: { message: string; thread_id?: string | null }) => {
        const { data } = await api.post<ChatSendResponse>("/chat/messages", payload);
        return data;
    },
};

export default api;
