import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("../../lib/pilotarrClient", () => ({
  default: { get: vi.fn(), put: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}));

import pilotarrClient from "../../lib/pilotarrClient";
import {
  getServiceConfigurations,
  getServiceConfiguration,
  saveServiceConfiguration,
  testServiceConnection,
  updateServiceTestStatus,
  deleteServiceConfiguration,
} from "../configService";

beforeEach(() => vi.clearAllMocks());

const rawService = {
  service_name: "radarr",
  url: "http://localhost:7878",
  username: null,
  port: 7878,
  is_active: true,
  id: "svc-1",
  last_tested_at: "2024-01-01T00:00:00Z",
  test_status: "success",
  test_message: "OK",
  created_at: "2024-01-01T00:00:00Z",
  updated_at: "2024-01-01T00:00:00Z",
  has_api_key: true,
  has_password: false,
};

const mappedService = {
  serviceName: "radarr",
  url: "http://localhost:7878",
  username: null,
  port: 7878,
  isActive: true,
  id: "svc-1",
  hasApiKey: true,
  hasPassword: false,
};

// ---------------------------------------------------------------------------
// getServiceConfigurations
// ---------------------------------------------------------------------------

describe("getServiceConfigurations", () => {
  it("fetches all 6 known services individually", async () => {
    pilotarrClient.get.mockResolvedValue({ data: rawService });
    await getServiceConfigurations();
    const calledPaths = pilotarrClient.get.mock.calls.map((c) => c[0]);
    expect(calledPaths).toContain("/services/radarr");
    expect(calledPaths).toContain("/services/sonarr");
    expect(calledPaths).toContain("/services/jellyfin");
    expect(calledPaths).toContain("/services/jellyseerr");
    expect(calledPaths).toContain("/services/qbittorrent");
    expect(calledPaths).toContain("/services/prowlarr");
  });

  it("maps response to camelCase", async () => {
    pilotarrClient.get.mockResolvedValue({ data: rawService });
    const result = await getServiceConfigurations();
    expect(result[0]).toMatchObject(mappedService);
  });

  it("filters out 404 services (not configured)", async () => {
    pilotarrClient.get
      .mockResolvedValueOnce({ data: rawService }) // radarr
      .mockRejectedValue({ response: { status: 404 } }); // rest
    const result = await getServiceConfigurations();
    expect(result).toHaveLength(1);
  });

  it("returns empty array on general error", async () => {
    pilotarrClient.get.mockRejectedValue(new Error("Network error"));
    expect(await getServiceConfigurations()).toEqual([]);
  });
});

// ---------------------------------------------------------------------------
// getServiceConfiguration
// ---------------------------------------------------------------------------

describe("getServiceConfiguration", () => {
  it("calls /services/{name}", async () => {
    pilotarrClient.get.mockResolvedValue({ data: rawService });
    await getServiceConfiguration("radarr");
    expect(pilotarrClient.get).toHaveBeenCalledWith("/services/radarr");
  });

  it("maps response to camelCase", async () => {
    pilotarrClient.get.mockResolvedValue({ data: rawService });
    const result = await getServiceConfiguration("radarr");
    expect(result).toMatchObject(mappedService);
  });

  it("returns null on error", async () => {
    pilotarrClient.get.mockRejectedValue(new Error("fail"));
    expect(await getServiceConfiguration("radarr")).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// saveServiceConfiguration
// ---------------------------------------------------------------------------

describe("saveServiceConfiguration", () => {
  it("puts to /services/{name} with mapped payload", async () => {
    pilotarrClient.put.mockResolvedValue({ data: rawService });
    await saveServiceConfiguration("radarr", {
      url: "http://localhost:7878",
      port: "7878",
      isActive: true,
      apiKey: "mykey",
    });
    expect(pilotarrClient.put).toHaveBeenCalledWith(
      "/services/radarr",
      expect.objectContaining({
        service_name: "radarr",
        url: "http://localhost:7878",
        port: 7878,
        is_active: true,
        api_key: "mykey",
      }),
    );
  });

  it("omits api_key when not provided", async () => {
    pilotarrClient.put.mockResolvedValue({ data: rawService });
    await saveServiceConfiguration("radarr", { url: "http://localhost:7878" });
    const payload = pilotarrClient.put.mock.calls[0][1];
    expect(payload).not.toHaveProperty("api_key");
  });

  it("omits password when not provided", async () => {
    pilotarrClient.put.mockResolvedValue({ data: rawService });
    await saveServiceConfiguration("qbittorrent", { url: "http://localhost:8080" });
    const payload = pilotarrClient.put.mock.calls[0][1];
    expect(payload).not.toHaveProperty("password");
  });

  it("returns mapped service on success", async () => {
    pilotarrClient.put.mockResolvedValue({ data: rawService });
    const result = await saveServiceConfiguration("radarr", { url: "http://localhost:7878" });
    expect(result).toMatchObject(mappedService);
  });

  it("throws on error", async () => {
    pilotarrClient.put.mockRejectedValue(new Error("fail"));
    await expect(saveServiceConfiguration("radarr", {})).rejects.toThrow();
  });
});

// ---------------------------------------------------------------------------
// testServiceConnection
// ---------------------------------------------------------------------------

describe("testServiceConnection", () => {
  it("posts to /services/{name}/test", async () => {
    pilotarrClient.post.mockResolvedValue({
      data: { success: true, message: "OK", tested_at: "2024-01-01T00:00:00Z" },
    });
    await testServiceConnection("radarr");
    expect(pilotarrClient.post).toHaveBeenCalledWith("/services/radarr/test", {});
  });

  it("returns success, message, testedAt", async () => {
    pilotarrClient.post.mockResolvedValue({
      data: { success: true, message: "Connected", tested_at: "2024-01-01T00:00:00Z" },
    });
    const result = await testServiceConnection("radarr");
    expect(result).toEqual({
      success: true,
      message: "Connected",
      testedAt: "2024-01-01T00:00:00Z",
    });
  });

  it("throws on error", async () => {
    pilotarrClient.post.mockRejectedValue(new Error("fail"));
    await expect(testServiceConnection("radarr")).rejects.toThrow();
  });
});

// ---------------------------------------------------------------------------
// updateServiceTestStatus
// ---------------------------------------------------------------------------

describe("updateServiceTestStatus", () => {
  it("patches /services/{name}/test with status and message", async () => {
    pilotarrClient.patch.mockResolvedValue({ data: rawService });
    await updateServiceTestStatus("radarr", "success", "All good");
    expect(pilotarrClient.patch).toHaveBeenCalledWith(
      "/services/radarr/test",
      expect.objectContaining({ test_status: "success", test_message: "All good" }),
    );
  });

  it("returns mapped service on success", async () => {
    pilotarrClient.patch.mockResolvedValue({ data: rawService });
    const result = await updateServiceTestStatus("radarr", "success", "OK");
    expect(result).toMatchObject(mappedService);
  });

  it("throws on error", async () => {
    pilotarrClient.patch.mockRejectedValue(new Error("fail"));
    await expect(updateServiceTestStatus("radarr", "error", "down")).rejects.toThrow();
  });
});

// ---------------------------------------------------------------------------
// deleteServiceConfiguration
// ---------------------------------------------------------------------------

describe("deleteServiceConfiguration", () => {
  it("calls DELETE on /services/{name}", async () => {
    pilotarrClient.delete.mockResolvedValue({});
    await deleteServiceConfiguration("radarr");
    expect(pilotarrClient.delete).toHaveBeenCalledWith("/services/radarr");
  });

  it("returns true on success", async () => {
    pilotarrClient.delete.mockResolvedValue({});
    expect(await deleteServiceConfiguration("radarr")).toBe(true);
  });

  it("returns false on error", async () => {
    pilotarrClient.delete.mockRejectedValue(new Error("fail"));
    expect(await deleteServiceConfiguration("radarr")).toBe(false);
  });
});
