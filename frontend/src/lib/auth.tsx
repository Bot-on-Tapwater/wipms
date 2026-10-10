"use client";

// Keeps the logged in user and their permission codes for the whole app.
//
// Permissions come from the backend (GET /permissions/me), never from code,
// so changing a role's permissions on the backend changes what people see.
// Use `can("projects.create")` or the <Can> component to hide things.

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { api, clearTokens, getAccessToken, getRefreshToken, saveTokens } from "./api";
import type { Permission } from "./permissions";
import type { LoginResponse, MyPermissions, TokenPair, User } from "./types";

interface AuthState {
  user: User | null;
  permissions: string[];
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  reload: () => Promise<void>;
  storeTokens: (tokens: TokenPair) => void;
  can: (permission: Permission) => boolean;
}

const AuthContext = createContext<AuthState | null>(null);

/** Holds the logged in user and their permissions for every page below it. */
export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [permissions, setPermissions] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);

  // Loads the user and permissions for the stored token (if any).
  const reload = useCallback(async () => {
    if (!getAccessToken()) {
      setUser(null);
      setPermissions([]);
      setLoading(false);
      return;
    }
    try {
      const [me, mine] = await Promise.all([
        api.get<User>("/users/me"),
        api.get<MyPermissions>("/permissions/me"),
      ]);
      setUser(me);
      setPermissions(mine.permissions);
    } catch {
      clearTokens();
      setUser(null);
      setPermissions([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // Runs once when the app opens in the browser.
    async function loadOnStart() {
      await reload();
    }
    loadOnStart();
  }, [reload]);

  /** Log in, store the tokens and keep the user and permissions. */
  async function login(email: string, password: string) {
    const result = await api.post<LoginResponse>("/auth/login", { email, password });
    saveTokens(result);
    setUser(result.user);
    setPermissions(result.permissions);
  }

  /** Cancel the refresh token on the backend, clear the tokens and open the login page. */
  async function logout() {
    const refreshToken = getRefreshToken();
    try {
      if (refreshToken) {
        await api.post("/auth/logout", { refresh_token: refreshToken });
      }
    } catch {
      // Already expired: logging out locally is enough.
    }
    clearTokens();
    // A full page load (not router.push) clears every bit of the previous user's state.
    // eslint-disable-next-line @next/next/no-location-assign-relative-destination
    window.location.href = "/login?logged_out=1";
  }

  // Change password returns a new token pair; older tokens stop working.
  function storeTokens(tokens: TokenPair) {
    saveTokens(tokens);
  }

  /** True when the user has the permission. */
  function can(permission: Permission): boolean {
    return permissions.includes(permission);
  }

  return (
    <AuthContext.Provider
      value={{ user, permissions, loading, login, logout, reload, storeTokens, can }}
    >
      {children}
    </AuthContext.Provider>
  );
}

/** The logged in user, permissions and auth actions. Use inside <AuthProvider>. */
export function useAuth(): AuthState {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used inside <AuthProvider>");
  }
  return context;
}
