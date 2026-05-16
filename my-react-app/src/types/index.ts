export interface AttachmentMeta {
    id: string;
    filename: string;
    mime_type: string;
    size_bytes: number;
    type_category: "image" | "video" | "pdf" | "code" | "table" | "generated_image";
    url: string;
}

export interface ImageGenerationRequest {
    prompt: string;
    thread_id?: string | null;
}

export interface ImageEditRequest {
    attachment_id: string;
    edit_prompt: string;
    thread_id?: string | null;
}

export interface SqlResultData {
    columns: string[];
    rows: string[][];
}

export interface SheetMetaData {
    rows: number;
    columns: string[];
}

export type ResearchSectionId =
    | "overview"
    | "key_papers"
    | "themes"
    | "gaps"
    | "future"
    | "references"
    | "error";

export interface ResearchSection {
    id: ResearchSectionId;
    title: string;
    content: string;
}

export interface ResearchMeta {
    total_papers: number;
    coverage: number;
}

export type ResearchEvent =
    | { event: "status"; message: string }
    | { event: "section"; id: ResearchSectionId; title: string; content: string }
    | { event: "done"; total_papers: number; coverage: number };

export interface ChatMessage {
    id: string;
    role: "user" | "assistant";
    content: string;
    thread_id?: string;
    model?: string | null;
    created_at?: string;
    attachments?: AttachmentMeta[];
    sources?: string[];
    sql_query?: string;
    sql_result?: SqlResultData;
    sheet_meta?: SheetMetaData;
    research_sections?: ResearchSection[];
    research_meta?: ResearchMeta;
    research_status?: string;
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

export interface IngestResponse {
    attachment_id: string;
    chunks_ingested: number;
}

export interface RagQueryRequest {
    thread_id: string;
    message: string;
    attachment_ids?: string[];
}

export interface AuthResponse {
    access_token: string;
    refresh_token: string;
    user: AuthUser;
}

export interface SqlQueryRequest {
    thread_id: string;
    question: string;
}

export interface SqlQueryResponse {
    answer: string;
    sql_query: string;
    thread_id: string;
}

export interface SheetsQueryRequest {
    thread_id: string;
    question: string;
    source_type: string;
    sheet_url?: string;
    attachment_id?: string;
}

export interface ResearchRequest {
    thread_id: string;
    topic: string;
}
