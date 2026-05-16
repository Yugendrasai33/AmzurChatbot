import { useEffect, useState } from "react";
import ChatPage from "./pages/ChatPage";
import GamePage from "./pages/GamePage";
import LoginPage from "./pages/LoginPage";
import { authApi } from "./lib/api";
import { type AuthUser } from "./types";

function App() {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isBootstrapping, setIsBootstrapping] = useState(true);
  const [authError, setAuthError] = useState<string | null>(null);
  const [page, setPage] = useState<"chat" | "game">("chat");

  useEffect(() => {
    const boot = async () => {
      const currentUrl = new URL(window.location.href);
      if (currentUrl.pathname === "/auth/google/callback") {
        const accessToken = currentUrl.searchParams.get("access_token");
        const userId = currentUrl.searchParams.get("user_id");
        const email = currentUrl.searchParams.get("email");
        const fullName = currentUrl.searchParams.get("full_name");
        const error = currentUrl.searchParams.get("error");

        window.history.replaceState({}, "", "/");

        if (error) {
          setAuthError(error);
          setIsBootstrapping(false);
          return;
        }

        if (accessToken && userId && email) {
          const authUser: AuthUser = {
            id: userId,
            email,
            full_name: fullName || null,
          };
          localStorage.setItem("auth_token", accessToken);
          localStorage.setItem("auth_user", JSON.stringify(authUser));
          setUser(authUser);
          setIsBootstrapping(false);
          return;
        }
      }

      const token = localStorage.getItem("auth_token");
      if (!token) {
        setIsBootstrapping(false);
        return;
      }

      try {
        const me = await authApi.me();
        setUser(me);
      } catch {
        localStorage.removeItem("auth_token");
        localStorage.removeItem("auth_user");
      } finally {
        setIsBootstrapping(false);
      }
    };

    void boot();
  }, []);

  if (isBootstrapping) {
    return <div className="flex h-screen items-center justify-center text-sm text-(--text-muted)">Loading...</div>;
  }

  if (!user) {
    return <LoginPage initialError={authError} onAuthenticated={(_, authUser) => setUser(authUser)} />;
  }

  if (page === "game") {
    return <GamePage user={user} onBack={() => setPage("chat")} />;
  }

  return <ChatPage user={user} onLogout={() => {
    localStorage.removeItem("auth_token");
    localStorage.removeItem("auth_user");
    setUser(null);
  }} onOpenGame={() => setPage("game")} />;
}

export default App
