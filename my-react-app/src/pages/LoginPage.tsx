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
        <main className="flex min-h-screen items-center justify-center bg-white px-4">
            <div className="w-full max-w-sm">
                <div className="mb-8 text-center">
                    <div className="mx-auto flex h-10 w-10 items-center justify-center rounded-lg bg-(--text-main) text-sm font-bold text-white">AI</div>
                    <h1 className="mt-4 text-xl font-semibold text-(--text-main)">
                        {isSignup ? "Create your account" : "Welcome back"}
                    </h1>
                    <p className="mt-1 text-sm text-(--text-soft)">Sign in to continue to Amzur AI Chat</p>
                </div>

                <form onSubmit={handleSubmit} className="space-y-3">
                    {isSignup && (
                        <input
                            type="text"
                            placeholder="Full name"
                            value={fullName}
                            onChange={(e) => setFullName(e.target.value)}
                            className="w-full rounded-lg border border-(--line) px-3 py-2.5 text-sm outline-none transition focus:border-(--text-main) focus:ring-1 focus:ring-(--text-main)"
                        />
                    )}
                    <input
                        type="email"
                        placeholder="Email address"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        className="w-full rounded-lg border border-(--line) px-3 py-2.5 text-sm outline-none transition focus:border-(--text-main) focus:ring-1 focus:ring-(--text-main)"
                        required
                    />
                    <input
                        type="password"
                        placeholder="Password"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        className="w-full rounded-lg border border-(--line) px-3 py-2.5 text-sm outline-none transition focus:border-(--text-main) focus:ring-1 focus:ring-(--text-main)"
                        required
                    />
                    {error && <p className="rounded-lg bg-red-50 px-3 py-2.5 text-sm text-red-700">{error}</p>}
                    <button
                        type="submit"
                        disabled={isLoading}
                        className="w-full rounded-lg bg-(--text-main) py-2.5 text-sm font-medium text-white transition hover:bg-black disabled:opacity-40"
                    >
                        {isLoading ? "Please wait..." : isSignup ? "Sign up" : "Continue"}
                    </button>
                </form>

                <div className="my-5 flex items-center gap-3">
                    <div className="h-px flex-1 bg-(--line)" />
                    <span className="text-xs text-(--text-muted)">or</span>
                    <div className="h-px flex-1 bg-(--line)" />
                </div>

                <button
                    type="button"
                    onClick={() => {
                        window.location.href = authApi.googleLoginUrl();
                    }}
                    className="w-full rounded-lg border border-(--line) py-2.5 text-sm font-medium text-(--text-main) transition hover:bg-(--surface-soft)"
                >
                    Continue with Google
                </button>

                <p className="mt-5 text-center text-sm text-(--text-soft)">
                    <button
                        type="button"
                        onClick={() => setIsSignup((prev) => !prev)}
                        className="font-medium text-(--text-main) underline-offset-4 hover:underline"
                    >
                        {isSignup ? "Already have an account? Log in" : "Don't have an account? Sign up"}
                    </button>
                </p>
            </div>
        </main>
    );
}
