import { useState, type FormEvent } from "react";
import { authApi } from "../lib/api";
import { type AuthUser } from "../types";

interface LoginPageProps {
    onAuthenticated: (token: string, user: AuthUser) => void;
    initialError?: string | null;
}

export default function LoginPage({ onAuthenticated, initialError = null }: LoginPageProps) {
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [fullName, setFullName] = useState("");
    const [isSignup, setIsSignup] = useState(false);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(initialError);

    const handleSubmit = async (e: FormEvent) => {
        e.preventDefault();
        setError(null);
        setIsLoading(true);

        try {
            const payload = isSignup
                ? await authApi.signup({ email, password, full_name: fullName || undefined })
                : await authApi.login({ email, password });

            localStorage.setItem("auth_token", payload.access_token);
            localStorage.setItem("auth_user", JSON.stringify(payload.user));
            onAuthenticated(payload.access_token, payload.user);
        } catch (err: unknown) {
            // Show the actual server error message if available
            let message = "Authentication failed. Check credentials and try again.";
            if (err && typeof err === "object" && "response" in err) {
                const resp = (err as { response?: { data?: { detail?: string } } }).response;
                if (resp?.data?.detail) {
                    message = resp.data.detail;
                }
            }
            setError(message);
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <main className="relative min-h-screen overflow-hidden p-4 sm:p-8">
            <div className="pointer-events-none absolute -left-10 top-8 h-40 w-40 rounded-full bg-teal-300/35 blur-3xl sm:h-56 sm:w-56" />
            <div className="pointer-events-none absolute -right-12 bottom-10 h-44 w-44 rounded-full bg-amber-300/35 blur-3xl sm:h-60 sm:w-60" />

            <div className="relative mx-auto max-w-md rounded-3xl border border-(--line) bg-(--surface)/90 p-6 shadow-[0_22px_70px_rgba(32,21,10,0.14)] sm:p-8">
                <p className="text-xs font-semibold uppercase tracking-[0.28em] text-(--text-soft)">Stackyon Employee Portal</p>
                <h1 className="mt-2 text-2xl font-semibold text-(--text-main)">
                    {isSignup ? "Create account" : "Welcome back"}
                </h1>

                <form onSubmit={handleSubmit} className="mt-6 space-y-3">
                    {isSignup && (
                        <input
                            type="text"
                            placeholder="Full name"
                            value={fullName}
                            onChange={(e) => setFullName(e.target.value)}
                            className="w-full rounded-xl border border-(--line) bg-white px-4 py-3 text-sm outline-none focus:border-teal-600"
                        />
                    )}
                    <input
                        type="email"
                        placeholder="Employee email"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        className="w-full rounded-xl border border-(--line) bg-white px-4 py-3 text-sm outline-none focus:border-teal-600"
                        required
                    />
                    <input
                        type="password"
                        placeholder="Password"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        className="w-full rounded-xl border border-(--line) bg-white px-4 py-3 text-sm outline-none focus:border-teal-600"
                        required
                    />
                    {error && <p className="text-sm text-red-600">{error}</p>}
                    <button
                        type="submit"
                        disabled={isLoading}
                        className="w-full rounded-xl bg-(--accent) py-3 text-sm font-semibold text-white transition hover:bg-(--accent-strong) disabled:opacity-40"
                    >
                        {isLoading ? "Please wait..." : isSignup ? "Sign up" : "Log in"}
                    </button>
                </form>

                <div className="my-4 flex items-center gap-3">
                    <div className="h-px flex-1 bg-(--line)" />
                    <span className="text-xs uppercase tracking-[0.2em] text-(--text-soft)">or</span>
                    <div className="h-px flex-1 bg-(--line)" />
                </div>

                <button
                    type="button"
                    onClick={() => {
                        window.location.href = authApi.googleLoginUrl();
                    }}
                    className="w-full rounded-xl border border-(--line) bg-white py-3 text-sm font-semibold text-(--text-main) transition hover:border-amber-300 hover:bg-amber-50"
                >
                    Continue with Google
                </button>

                <button
                    type="button"
                    onClick={() => setIsSignup((prev) => !prev)}
                    className="mt-4 text-sm text-(--text-soft) underline-offset-2 hover:text-(--text-main) hover:underline"
                >
                    {isSignup ? "Already have an account? Log in" : "No account? Sign up"}
                </button>
            </div>
        </main>
    );
}
