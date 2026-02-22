import axios from "axios";

const apiUrl = import.meta.env?.VITE_PILOTARR_API_URL;

if (!apiUrl) {
  console.warn(
    "Missing Pilotarr environment variable VITE_PILOTARR_API_URL. Please check your .env file.",
  );
}

/**
 * Pilotarr API Client
 * Backend API for all data operations and service integrations
 */
export const PilotarrClient = axios?.create({
  baseURL: apiUrl,
  headers: {
    "Content-Type": "application/json",
  },
  timeout: 30000,
});

// Inject JWT Bearer token from localStorage on every request
PilotarrClient?.interceptors?.request?.use((config) => {
  const token = localStorage.getItem("pilotarr_token");
  if (token) {
    config.headers["Authorization"] = `Bearer ${token}`;
  }
  return config;
});

// Add response interceptor for error handling
PilotarrClient?.interceptors?.response?.use(
  (response) => response,
  (error) => {
    // Only log errors that aren't 404s (those are handled by individual services)
    if (error?.response?.status !== 404) {
      // Only log if it's not a network error (API might be down)
      if (error?.code !== "ERR_NETWORK" && error?.message !== "Network Error") {
        console.error("Pilotarr API Error:", error?.response?.data || error?.message);
      }
    }
    return Promise.reject(error);
  },
);

export default PilotarrClient;
