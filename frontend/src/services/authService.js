import axios from "axios";

const apiUrl = import.meta.env?.VITE_PILOTARR_API_URL;

// Separate client for auth endpoints — cookie is sent automatically via withCredentials
const authClient = axios.create({
  baseURL: apiUrl,
  headers: { "Content-Type": "application/json" },
  timeout: 10000,
  withCredentials: true,
});

export const loginApi = async (username, password) => {
  const response = await authClient.post("/auth/login", { username, password });
  return response.data; // { username, is_active }
};

export const logoutApi = async () => {
  await authClient.post("/auth/logout");
};

export const meApi = async () => {
  const response = await authClient.get("/auth/me");
  return response.data; // { username, is_active }
};

export const changePasswordApi = async (currentPassword, newPassword, confirmPassword) => {
  await authClient.post("/auth/change-password", {
    current_password: currentPassword,
    new_password: newPassword,
    confirm_password: confirmPassword,
  });
};
