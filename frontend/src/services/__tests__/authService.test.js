import { describe, it, expect, vi, beforeEach } from "vitest";

// Mock axios before importing authService (authService creates its own axios instance)
vi.mock("axios", () => {
  const mockClient = {
    post: vi.fn(),
    get: vi.fn(),
  };
  return {
    default: {
      create: vi.fn(() => mockClient),
    },
    __mockClient: mockClient,
  };
});

import axios from "axios";
import { loginApi, logoutApi, meApi, changePasswordApi } from "../authService";

const mockClient = axios.create();

beforeEach(() => {
  vi.clearAllMocks();
});

describe("loginApi", () => {
  it("posts credentials and returns response data", async () => {
    mockClient.post.mockResolvedValue({
      data: { username: "alice", is_active: true },
    });

    const result = await loginApi("alice", "pass");

    expect(mockClient.post).toHaveBeenCalledWith("/auth/login", {
      username: "alice",
      password: "pass",
    });
    expect(result).toEqual({ username: "alice", is_active: true });
  });

  it("throws on network error", async () => {
    mockClient.post.mockRejectedValue(new Error("Network Error"));
    await expect(loginApi("alice", "bad")).rejects.toThrow("Network Error");
  });
});

describe("logoutApi", () => {
  it("posts to /auth/logout", async () => {
    mockClient.post.mockResolvedValue({});
    await logoutApi();
    expect(mockClient.post).toHaveBeenCalledWith("/auth/logout");
  });
});

describe("meApi", () => {
  it("fetches /auth/me with no explicit headers (cookie sent automatically)", async () => {
    mockClient.get.mockResolvedValue({ data: { username: "alice", is_active: true } });

    const result = await meApi();

    expect(mockClient.get).toHaveBeenCalledWith("/auth/me");
    expect(result).toEqual({ username: "alice", is_active: true });
  });

  it("throws on 401", async () => {
    mockClient.get.mockRejectedValue({ response: { status: 401 } });
    await expect(meApi()).rejects.toBeDefined();
  });
});

describe("changePasswordApi", () => {
  it("posts change-password with correct body (no Authorization header)", async () => {
    mockClient.post.mockResolvedValue({});

    await changePasswordApi("old", "newpass", "newpass");

    expect(mockClient.post).toHaveBeenCalledWith("/auth/change-password", {
      current_password: "old",
      new_password: "newpass",
      confirm_password: "newpass",
    });
  });

  it("throws on validation error", async () => {
    mockClient.post.mockRejectedValue({ response: { status: 422 } });
    await expect(changePasswordApi("old", "x", "y")).rejects.toBeDefined();
  });
});
