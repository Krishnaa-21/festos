import React, { createContext, useContext, useState, useEffect, useCallback } from "react";
import { api } from "../../api/client";

export interface UserProfile {
  id: string;
  email: string;
  full_name: string;
  role: string;
  contingent_id?: string | null;
  permissions?: string[];
}

export interface AuthContextType {
  user: UserProfile | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  hasPermission: (permission: string) => boolean;
  refetchUser: () => Promise<void>;
}

export const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem("festos_token"));
  const [user, setUser] = useState<UserProfile | null>(() => {
    const cached = localStorage.getItem("festos_user");
    return cached ? JSON.parse(cached) : null;
  });
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const fetchCurrentUser = useCallback(async (authToken: string) => {
    try {
      const res = await api.get<any>("/api/v1/auth/me", {
        headers: { Authorization: `Bearer ${authToken}` },
      });
      const userData: UserProfile = {
        id: res.id,
        email: res.email || "",
        full_name: res.name || res.full_name || "User",
        role: res.role,
        contingent_id: res.contingent_id,
        permissions: res.permissions || [],
      };
      setUser(userData);
      localStorage.setItem("festos_user", JSON.stringify(userData));
    } catch (err) {
      console.warn("Failed to fetch user with token, clearing session", err);
      localStorage.removeItem("festos_token");
      localStorage.removeItem("festos_user");
      setToken(null);
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (token) {
      fetchCurrentUser(token);
    } else {
      setIsLoading(false);
    }
  }, [token, fetchCurrentUser]);

  const login = async (email: string, password: string) => {
    const res = await api.post<any>("/api/v1/auth/login", { email, password });
    const { access_token, user: loggedUser } = res;
    localStorage.setItem("festos_token", access_token);
    setToken(access_token);

    const userProfile: UserProfile = {
      id: loggedUser.id,
      email: loggedUser.email,
      full_name: loggedUser.full_name,
      role: loggedUser.role,
      contingent_id: loggedUser.contingent_id,
    };
    setUser(userProfile);
    localStorage.setItem("festos_user", JSON.stringify(userProfile));

    // Fetch full permissions
    await fetchCurrentUser(access_token);
  };

  const logout = () => {
    localStorage.removeItem("festos_token");
    localStorage.removeItem("festos_user");
    setToken(null);
    setUser(null);
  };

  const hasPermission = useCallback(
    (permission: string): boolean => {
      if (!user) return false;
      if (user.role === "FESTIVAL_DIRECTOR") return true;

      const perms = user.permissions || [];
      if (perms.includes("*:*")) return true;

      const normalized = permission.replace(/\s+/g, "");
      if (perms.some((p) => p.replace(/\s+/g, "") === normalized)) return true;

      const [reqMod, reqAct] = normalized.split(":");
      return perms.some((p) => {
        const [mod, act] = p.replace(/\s+/g, "").split(":");
        return (mod === "*" || mod === reqMod) && (act === "*" || act === reqAct);
      });
    },
    [user]
  );

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isAuthenticated: !!token && !!user,
        isLoading,
        login,
        logout,
        hasPermission,
        refetchUser: async () => {
          if (token) await fetchCurrentUser(token);
        },
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider");
  return ctx;
};
