import { useCallback, useEffect, useState } from "react";
import { ticketsApi } from "../lib/api";
import type { AuthUser, TicketCreateResponse, TicketListItem } from "../types";

interface TicketsPageProps {
    user: AuthUser;
    onBack: () => void;
    threadId?: string | null;
}

export default function TicketsPage({ user, onBack, threadId }: TicketsPageProps) {
    const [activeTab, setActiveTab] = useState<"create" | "list">("create");
    const [message, setMessage] = useState("");
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [result, setResult] = useState<TicketCreateResponse | null>(null);
    const [error, setError] = useState<string | null>(null);

    const [tickets, setTickets] = useState<TicketListItem[]>([]);
    const [isLoadingTickets, setIsLoadingTickets] = useState(false);
    const [selectedTicket, setSelectedTicket] = useState<TicketListItem | null>(null);

    const [sortField, setSortField] = useState<"created_at" | "priority" | "status">("created_at");
    const [filterStatus, setFilterStatus] = useState<string>("all");

    const loadTickets = useCallback(async () => {
        setIsLoadingTickets(true);
        try {
            const data = await ticketsApi.list();
            setTickets(data);
        } catch {
            // silently fail — user will see empty list
        } finally {
            setIsLoadingTickets(false);
        }
    }, []);

    useEffect(() => {
        if (activeTab === "list") {
            void loadTickets();
        }
    }, [activeTab, loadTickets]);

    const handleSubmit = async () => {
        if (!message.trim() || message.trim().length < 10) {
            setError("Please describe your issue in at least 10 characters.");
            return;
        }
        setError(null);
        setIsSubmitting(true);
        try {
            const response = await ticketsApi.create(message.trim(), threadId ?? undefined);
            setResult(response);
            setMessage("");
        } catch (err: unknown) {
            const axiosErr = err as { response?: { data?: { detail?: string }; status?: number } };
            if (axiosErr.response?.data?.detail) {
                setError(axiosErr.response.data.detail);
            } else {
                setError("An unexpected error occurred. Please try again.");
            }
        } finally {
            setIsSubmitting(false);
        }
    };

    const handleReset = () => {
        setResult(null);
        setError(null);
        setMessage("");
    };

    const priorityColor = (p: string) => {
        switch (p) {
            case "high": return "bg-red-100 text-red-700";
            case "medium": return "bg-yellow-100 text-yellow-700";
            case "low": return "bg-green-100 text-green-700";
            default: return "bg-gray-100 text-gray-700";
        }
    };

    const statusColor = (s: string) => {
        switch (s) {
            case "open": return "bg-blue-100 text-blue-700";
            case "in_progress": return "bg-purple-100 text-purple-700";
            case "resolved": return "bg-green-100 text-green-700";
            case "closed": return "bg-gray-100 text-gray-600";
            default: return "bg-gray-100 text-gray-700";
        }
    };

    const priorityOrder: Record<string, number> = { high: 0, medium: 1, low: 2 };

    const filteredTickets = tickets
        .filter((t) => filterStatus === "all" || t.status === filterStatus)
        .sort((a, b) => {
            if (sortField === "created_at") return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
            if (sortField === "priority") return (priorityOrder[a.priority] ?? 3) - (priorityOrder[b.priority] ?? 3);
            if (sortField === "status") return a.status.localeCompare(b.status);
            return 0;
        });

    return (
        <div className="flex h-screen flex-col bg-linear-to-br from-slate-50 to-orange-50">
            {/* Header */}
            <header className="flex shrink-0 items-center justify-between border-b border-gray-200 bg-white/80 backdrop-blur px-4 py-3 sm:px-6">
                <div className="flex items-center gap-3">
                    <button
                        onClick={onBack}
                        className="rounded-lg p-1.5 text-gray-500 transition hover:bg-gray-100 hover:text-gray-700"
                        title="Back to chat"
                    >
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <path d="M19 12H5" /><polyline points="12 19 5 12 12 5" />
                        </svg>
                    </button>
                    <h1 className="text-base font-semibold text-gray-900">Support Tickets</h1>
                    <span className="rounded-full bg-orange-100 px-2 py-0.5 text-[10px] font-medium text-orange-700 uppercase tracking-wider">
                        n8n Automation
                    </span>
                </div>
                <span className="text-xs text-gray-500">{user.email}</span>
            </header>

            {/* Tabs */}
            <div className="flex border-b border-gray-200 bg-white px-4 sm:px-6">
                <button
                    onClick={() => setActiveTab("create")}
                    className={`px-4 py-3 text-sm font-medium border-b-2 transition ${activeTab === "create"
                        ? "border-orange-500 text-orange-700"
                        : "border-transparent text-gray-500 hover:text-gray-700"
                        }`}
                >
                    Create Ticket
                </button>
                <button
                    onClick={() => setActiveTab("list")}
                    className={`px-4 py-3 text-sm font-medium border-b-2 transition ${activeTab === "list"
                        ? "border-orange-500 text-orange-700"
                        : "border-transparent text-gray-500 hover:text-gray-700"
                        }`}
                >
                    My Tickets {tickets.length > 0 && `(${tickets.length})`}
                </button>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto px-4 py-6 sm:px-6">
                {activeTab === "create" && (
                    <div className="mx-auto max-w-2xl">
                        {!result ? (
                            <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
                                <h2 className="text-lg font-semibold text-gray-900 mb-1">Describe your issue</h2>
                                <p className="text-sm text-gray-500 mb-4">
                                    Our AI will classify your ticket and route it to the right team automatically.
                                </p>

                                <textarea
                                    value={message}
                                    onChange={(e) => setMessage(e.target.value)}
                                    placeholder="Describe the issue you're experiencing in detail..."
                                    className="w-full rounded-lg border border-gray-200 bg-gray-50 px-4 py-3 text-sm text-gray-900 placeholder:text-gray-400 outline-none transition focus:border-orange-300 focus:ring-2 focus:ring-orange-100 resize-none"
                                    rows={5}
                                    disabled={isSubmitting}
                                    maxLength={2000}
                                />
                                <div className="mt-1 flex justify-between">
                                    <span className="text-xs text-gray-400">Min 10 characters</span>
                                    <span className="text-xs text-gray-400">{message.length}/2000</span>
                                </div>

                                {error && (
                                    <div className="mt-3 rounded-lg border border-red-200 bg-red-50 px-4 py-2.5 text-sm text-red-700">
                                        {error}
                                    </div>
                                )}

                                <button
                                    onClick={handleSubmit}
                                    disabled={isSubmitting || message.trim().length < 10}
                                    className="mt-4 w-full rounded-lg bg-orange-600 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-orange-700 disabled:opacity-50 disabled:cursor-not-allowed"
                                >
                                    {isSubmitting ? (
                                        <span className="flex items-center justify-center gap-2">
                                            <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                                                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                                                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                                            </svg>
                                            Processing with AI...
                                        </span>
                                    ) : (
                                        "Submit Ticket"
                                    )}
                                </button>
                            </div>
                        ) : (
                            <div className="rounded-xl border border-green-200 bg-white p-6 shadow-sm">
                                <div className="flex items-center gap-2 mb-4">
                                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-green-600">
                                        <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" /><polyline points="22 4 12 14.01 9 11.01" />
                                    </svg>
                                    <h2 className="text-lg font-semibold text-green-800">Ticket Created Successfully</h2>
                                </div>

                                <div className="space-y-3">
                                    <div className="flex items-center justify-between rounded-lg bg-gray-50 px-4 py-2.5">
                                        <span className="text-sm text-gray-500">Ticket ID</span>
                                        <span className="text-sm font-mono font-semibold text-gray-900">{result.ticket_id}</span>
                                    </div>
                                    <div className="flex items-center justify-between rounded-lg bg-gray-50 px-4 py-2.5">
                                        <span className="text-sm text-gray-500">Category</span>
                                        <span className="text-sm font-medium text-gray-900">{result.category}</span>
                                    </div>
                                    <div className="flex items-center justify-between rounded-lg bg-gray-50 px-4 py-2.5">
                                        <span className="text-sm text-gray-500">Priority</span>
                                        <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${priorityColor(result.priority)}`}>
                                            {result.priority}
                                        </span>
                                    </div>
                                    <div className="flex items-center justify-between rounded-lg bg-gray-50 px-4 py-2.5">
                                        <span className="text-sm text-gray-500">Assigned Team</span>
                                        <span className="text-sm font-medium text-gray-900">{result.assigned_team}</span>
                                    </div>
                                    <div className="flex items-center justify-between rounded-lg bg-gray-50 px-4 py-2.5">
                                        <span className="text-sm text-gray-500">Status</span>
                                        <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${statusColor(result.status)}`}>
                                            {result.status}
                                        </span>
                                    </div>
                                </div>

                                <div className="mt-4 rounded-lg border border-blue-100 bg-blue-50 px-4 py-2.5 text-sm text-blue-700">
                                    ✉️ A confirmation email has been sent to your inbox.
                                </div>

                                <div className="mt-5 flex gap-3">
                                    <button
                                        onClick={handleReset}
                                        className="flex-1 rounded-lg border border-gray-200 px-4 py-2.5 text-sm font-medium text-gray-700 transition hover:bg-gray-50"
                                    >
                                        Create another
                                    </button>
                                    <button
                                        onClick={() => { setActiveTab("list"); void loadTickets(); }}
                                        className="flex-1 rounded-lg bg-orange-600 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-orange-700"
                                    >
                                        View my tickets
                                    </button>
                                </div>
                            </div>
                        )}
                    </div>
                )}

                {activeTab === "list" && (
                    <div className="mx-auto max-w-4xl">
                        {/* Filters */}
                        <div className="mb-4 flex flex-wrap items-center gap-3">
                            <select
                                value={filterStatus}
                                onChange={(e) => setFilterStatus(e.target.value)}
                                className="rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-700 outline-none"
                            >
                                <option value="all">All statuses</option>
                                <option value="open">Open</option>
                                <option value="in_progress">In Progress</option>
                                <option value="resolved">Resolved</option>
                                <option value="closed">Closed</option>
                            </select>
                            <select
                                value={sortField}
                                onChange={(e) => setSortField(e.target.value as typeof sortField)}
                                className="rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-700 outline-none"
                            >
                                <option value="created_at">Sort by date</option>
                                <option value="priority">Sort by priority</option>
                                <option value="status">Sort by status</option>
                            </select>
                        </div>

                        {isLoadingTickets ? (
                            <div className="flex items-center justify-center py-12">
                                <svg className="animate-spin h-6 w-6 text-orange-500" viewBox="0 0 24 24" fill="none">
                                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                                </svg>
                            </div>
                        ) : filteredTickets.length === 0 ? (
                            <div className="rounded-xl border border-gray-200 bg-white p-8 text-center">
                                <p className="text-sm text-gray-500">
                                    {tickets.length === 0 ? "No tickets yet. Create your first one!" : "No tickets match the current filter."}
                                </p>
                            </div>
                        ) : (
                            <div className="space-y-2">
                                {filteredTickets.map((ticket) => (
                                    <button
                                        key={ticket.id}
                                        onClick={() => setSelectedTicket(ticket)}
                                        className="w-full rounded-xl border border-gray-200 bg-white p-4 text-left shadow-sm transition hover:border-orange-200 hover:shadow"
                                    >
                                        <div className="flex items-start justify-between gap-3">
                                            <div className="min-w-0 flex-1">
                                                <div className="flex items-center gap-2 mb-1">
                                                    <span className="text-xs font-mono text-gray-500">{ticket.ticket_id}</span>
                                                    <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded-full ${priorityColor(ticket.priority)}`}>
                                                        {ticket.priority}
                                                    </span>
                                                    <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded-full ${statusColor(ticket.status)}`}>
                                                        {ticket.status}
                                                    </span>
                                                </div>
                                                <p className="text-sm text-gray-900 truncate">{ticket.issue}</p>
                                                <div className="mt-1 flex items-center gap-3 text-xs text-gray-400">
                                                    <span>{ticket.category}</span>
                                                    {ticket.assigned_team && <span>→ {ticket.assigned_team}</span>}
                                                    <span>{new Date(ticket.created_at).toLocaleDateString()}</span>
                                                </div>
                                            </div>
                                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="shrink-0 text-gray-300">
                                                <polyline points="9 18 15 12 9 6" />
                                            </svg>
                                        </div>
                                    </button>
                                ))}
                            </div>
                        )}
                    </div>
                )}
            </div>

            {/* Ticket detail modal */}
            {selectedTicket && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
                    <div className="w-full max-w-lg rounded-xl border border-gray-200 bg-white p-6 shadow-xl">
                        <div className="flex items-center justify-between mb-4">
                            <h2 className="text-base font-semibold text-gray-900">{selectedTicket.ticket_id}</h2>
                            <button
                                onClick={() => setSelectedTicket(null)}
                                className="rounded-lg p-1 text-gray-400 hover:text-gray-600"
                            >
                                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                    <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
                                </svg>
                            </button>
                        </div>
                        <div className="space-y-3">
                            <div>
                                <span className="text-xs text-gray-500">Issue</span>
                                <p className="text-sm text-gray-900 mt-0.5">{selectedTicket.issue}</p>
                            </div>
                            <div className="grid grid-cols-2 gap-3">
                                <div>
                                    <span className="text-xs text-gray-500">Category</span>
                                    <p className="text-sm font-medium text-gray-900 mt-0.5">{selectedTicket.category}</p>
                                </div>
                                <div>
                                    <span className="text-xs text-gray-500">Priority</span>
                                    <p className="mt-0.5">
                                        <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${priorityColor(selectedTicket.priority)}`}>
                                            {selectedTicket.priority}
                                        </span>
                                    </p>
                                </div>
                                <div>
                                    <span className="text-xs text-gray-500">Status</span>
                                    <p className="mt-0.5">
                                        <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${statusColor(selectedTicket.status)}`}>
                                            {selectedTicket.status}
                                        </span>
                                    </p>
                                </div>
                                <div>
                                    <span className="text-xs text-gray-500">Assigned Team</span>
                                    <p className="text-sm font-medium text-gray-900 mt-0.5">{selectedTicket.assigned_team || "—"}</p>
                                </div>
                                <div>
                                    <span className="text-xs text-gray-500">Created</span>
                                    <p className="text-sm text-gray-900 mt-0.5">{new Date(selectedTicket.created_at).toLocaleString()}</p>
                                </div>
                                <div>
                                    <span className="text-xs text-gray-500">Updated</span>
                                    <p className="text-sm text-gray-900 mt-0.5">{new Date(selectedTicket.updated_at).toLocaleString()}</p>
                                </div>
                            </div>
                            {selectedTicket.next_action && (
                                <div>
                                    <span className="text-xs text-gray-500">Next Action</span>
                                    <p className="text-sm text-gray-900 mt-0.5">{selectedTicket.next_action}</p>
                                </div>
                            )}
                        </div>
                        <button
                            onClick={() => setSelectedTicket(null)}
                            className="mt-5 w-full rounded-lg border border-gray-200 px-4 py-2.5 text-sm font-medium text-gray-700 transition hover:bg-gray-50"
                        >
                            Close
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
}
