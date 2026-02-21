import React, { createContext, useContext, useState, useEffect } from "react";
import { loginApi, meApi, changePasswordApi } from "../services/authService";

const AuthContext = createContext({});

export const useAuth = () => {
  return useContext(AuthContext);
};

const TOKEN_KEY = "pilotarr_token";

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [initializing, setInitializing] = useState(true);

  // On mount: restore session from stored token
  useEffect(() => {
    const restore = async () => {
      const token = localStorage.getItem(TOKEN_KEY);
      if (!token) {
        setInitializing(false);
        return;
      }
      try {
        const data = await meApi(token);
        setUser({ username: data.username, token });
      } catch {
        // Token expired or invalid — clear it
        localStorage.removeItem(TOKEN_KEY);
      } finally {
        setInitializing(false);
      }
    };
    restore();
  }, []);

  const login = async (username, password) => {
    try {
      const data = await loginApi(username, password);
      const userData = { username: data.username, token: data.access_token };
      localStorage.setItem(TOKEN_KEY, data.access_token);
      setUser(userData);
      return { ok: true };
    } catch (err) {
      const message = err?.response?.data?.detail || "Invalid credentials";
      return { ok: false, error: message };
    }
  };

  const logout = () => {
    localStorage.removeItem(TOKEN_KEY);
    setUser(null);
  };

  const changePassword = async (currentPassword, newPassword, confirmPassword) => {
    try {
      await changePasswordApi(user?.token, currentPassword, newPassword, confirmPassword);
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
