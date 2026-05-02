export interface ChatMessage {
    id: string;
    role: "user" | "assistant";
    content: string;
    thread_id?: string;
    model?: string | null;
    created_at?: string;
}

export interface ChatRequest {
    message: string;
    thread_id?: string | null;
}

export interface ChatResponse {
    response: string;
    model: string;
}

export interface Thread {
    id: string;
    title: string;
    created_at: string;
    updated_at: string;
}

export interface ChatSendResponse {
    thread: Thread;
    user_message: ChatMessage;
    assistant_message: ChatMessage;
    model: string;
}

export interface AuthUser {
    id: string;
    email: string;
    full_name?: string | null;
}

export interface AuthResponse {
    access_token: string;
    refresh_token: string;
    user: AuthUser;
}
