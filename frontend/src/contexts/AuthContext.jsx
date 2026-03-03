import React, { createContext, useContext, useState, useEffect } from "react";
import { loginApi, meApi, logoutApi, changePasswordApi } from "../services/authService";

const AuthContext = createContext({});

export const useAuth = () => {
  return useContext(AuthContext);
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [initializing, setInitializing] = useState(true);

  // On mount: restore session from httpOnly cookie via /auth/me
  useEffect(() => {
    const restore = async () => {
      try {
        const data = await meApi();
        setUser({ username: data.username });
      } catch {
        // No valid cookie or expired token — user is not authenticated
        setUser(null);
      } finally {
        setInitializing(false);
      }
    };
    restore();
  }, []);

  const login = async (username, password) => {
    try {
      const data = await loginApi(username, password);
      setUser({ username: data.username });
      return { ok: true };
    } catch (err) {
      const message = err?.response?.data?.detail || "Invalid credentials";
      return { ok: false, error: message };
    }
  };

  const logout = async () => {
    try {
      await logoutApi();
    } catch {
      // ignore — clear local state regardless
    }
    setUser(null);
  };

  const changePassword = async (currentPassword, newPassword, confirmPassword) => {
    try {
      await changePasswordApi(currentPassword, newPassword, confirmPassword);
      return { ok: true };
    } catch (err) {
      const detail = err?.response?.data?.detail;
      const message = Array.isArray(detail)
        ? detail.map((d) => d.msg).join(", ")
        : detail || "Failed to change password";
      return { ok: false, error: message };
    }
  };

  const value = {
    user,
    initializing,
    login,
    logout,
    changePassword,
    isAuthenticated: !!user,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};
