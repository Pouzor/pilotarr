import axios from "axios";

const apiUrl = import.meta.env?.VITE_PILOTARR_API_URL;

// Separate client — no X-API-Key, auth is handled via Bearer token
const authClient = axios.create({
  baseURL: apiUrl,
  headers: { "Content-Type": "application/json" },
  timeout: 10000,
});

const bearerHeader = (token) => ({ Authorization: `Bearer ${token}` });

export const loginApi = async (username, password) => {
  const response = await authClient.post("/auth/login", { username, password });
  return response.data; // { access_token, token_type, username }
};

export const meApi = async (token) => {
  const response = await authClient.get("/auth/me", { headers: bearerHeader(token) });
  return response.data; // { username, is_active }
};

export const changePasswordApi = async (token, currentPassword, newPassword, confirmPassword) => {
  await authClient.post(
    "/auth/change-password",
    {
      current_password: currentPassword,
      new_password: newPassword,
      confirm_password: confirmPassword,
    },
    { headers: bearerHeader(token) },
  );
};
