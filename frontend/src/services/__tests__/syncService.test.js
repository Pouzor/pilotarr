import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("../../lib/pilotarrClient", () => ({
  default: { get: vi.fn(), post: vi.fn() },
}));

import pilotarrClient from "../../lib/pilotarrClient";
import {
  getAllSyncMetadata,
  getSyncMetadata,
  updateSyncStatus,
  completeSyncMetadata,
  getServicesNeedingSync,
  triggerSync,
} from "../syncService";

beforeEach(() => vi.clearAllMocks());

// ---------------------------------------------------------------------------
// getAllSyncMetadata
// ---------------------------------------------------------------------------

describe("getAllSyncMetadata", () => {
  it("calls /sync/metadata", async () => {
    pilotarrClient.get.mockResolvedValue({ data: [] });
    await getAllSyncMetadata();
    expect(pilotarrClient.get).toHaveBeenCalledWith("/sync/metadata");
  });

  it("returns response data", async () => {
    pilotarrClient.get.mockResolvedValue({ data: [{ service: "radarr" }] });
    expect(await getAllSyncMetadata()).toEqual([{ service: "radarr" }]);
  });

  it("returns empty array on error", async () => {
    pilotarrClient.get.mockRejectedValue(new Error("fail"));
    expect(await getAllSyncMetadata()).toEqual([]);
  });
});

// ---------------------------------------------------------------------------
// getSyncMetadata
// ---------------------------------------------------------------------------

describe("getSyncMetadata", () => {
  it("calls /sync/metadata/{serviceName}", async () => {
    pilotarrClient.get.mockResolvedValue({ data: { service: "radarr" } });
    await getSyncMetadata("radarr");
    expect(pilotarrClient.get).toHaveBeenCalledWith("/sync/metadata/radarr");
  });

  it("returns the metadata object", async () => {
    pilotarrClient.get.mockResolvedValue({ data: { service: "radarr", status: "ok" } });
    expect(await getSyncMetadata("radarr")).toEqual({ service: "radarr", status: "ok" });
  });

  it("returns null on error", async () => {
    pilotarrClient.get.mockRejectedValue(new Error("fail"));
    expect(await getSyncMetadata("radarr")).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// updateSyncStatus
// ---------------------------------------------------------------------------

describe("updateSyncStatus", () => {
  it("posts to /sync/status with serviceName and status", async () => {
    pilotarrClient.post.mockResolvedValue({ data: {} });
    await updateSyncStatus("radarr", "in_progress");
    expect(pilotarrClient.post).toHaveBeenCalledWith(
      "/sync/status",
      expect.objectContaining({ serviceName: "radarr", status: "in_progress" }),
    );
  });

  it("includes lastSyncTime when status is in_progress", async () => {
    pilotarrClient.post.mockResolvedValue({ data: {} });
    await updateSyncStatus("radarr", "in_progress");
    const payload = pilotarrClient.post.mock.calls[0][1];
    expect(payload.lastSyncTime).toBeDefined();
  });

  it("does not include lastSyncTime when status is not in_progress", async () => {
    pilotarrClient.post.mockResolvedValue({ data: {} });
    await updateSyncStatus("radarr", "success");
    const payload = pilotarrClient.post.mock.calls[0][1];
    expect(payload.lastSyncTime).toBeUndefined();
  });

  it("includes optional errorMessage", async () => {
    pilotarrClient.post.mockResolvedValue({ data: {} });
    await updateSyncStatus("radarr", "error", "Something broke");
    const payload = pilotarrClient.post.mock.calls[0][1];
    expect(payload.errorMessage).toBe("Something broke");
  });

  it("throws on error", async () => {
    pilotarrClient.post.mockRejectedValue(new Error("fail"));
    await expect(updateSyncStatus("radarr", "in_progress")).rejects.toThrow();
  });
});

// ---------------------------------------------------------------------------
// completeSyncMetadata
// ---------------------------------------------------------------------------

describe("completeSyncMetadata", () => {
  it("posts to /sync/complete with all fields", async () => {
    pilotarrClient.post.mockResolvedValue({ data: {} });
    await completeSyncMetadata("radarr", 150, 2000, "2024-02-01T00:00:00Z");
    expect(pilotarrClient.post).toHaveBeenCalledWith("/sync/complete", {
      serviceName: "radarr",
      recordsSynced: 150,
      durationMs: 2000,
      nextSyncTime: "2024-02-01T00:00:00Z",
    });
  });

  it("returns response data", async () => {
    pilotarrClient.post.mockResolvedValue({ data: { id: "sync-1" } });
    expect(await completeSyncMetadata("radarr", 150, 2000, null)).toEqual({ id: "sync-1" });
  });

  it("throws on error", async () => {
    pilotarrClient.post.mockRejectedValue(new Error("fail"));
    await expect(completeSyncMetadata("radarr", 0, 0, null)).rejects.toThrow();
  });
});

// ---------------------------------------------------------------------------
// getServicesNeedingSync
// ---------------------------------------------------------------------------

describe("getServicesNeedingSync", () => {
  it("calls /sync/pending", async () => {
    pilotarrClient.get.mockResolvedValue({ data: [] });
    await getServicesNeedingSync();
    expect(pilotarrClient.get).toHaveBeenCalledWith("/sync/pending");
  });

  it("returns response data", async () => {
    pilotarrClient.get.mockResolvedValue({ data: ["radarr", "sonarr"] });
    expect(await getServicesNeedingSync()).toEqual(["radarr", "sonarr"]);
  });

  it("returns empty array on error", async () => {
    pilotarrClient.get.mockRejectedValue(new Error("fail"));
    expect(await getServicesNeedingSync()).toEqual([]);
  });
});

// ---------------------------------------------------------------------------
// triggerSync
// ---------------------------------------------------------------------------

describe("triggerSync", () => {
  it("posts to /sync/trigger", async () => {
    pilotarrClient.post.mockResolvedValue({ data: { success: true } });
    await triggerSync();
    expect(pilotarrClient.post).toHaveBeenCalledWith("/sync/trigger");
  });

  it("returns response data on success", async () => {
    pilotarrClient.post.mockResolvedValue({ data: { success: true, message: "Started" } });
    expect(await triggerSync()).toEqual({ success: true, message: "Started" });
  });

  it("returns { success: false } with error message on error", async () => {
    pilotarrClient.post.mockRejectedValue(new Error("Network error"));
    const result = await triggerSync();
    expect(result.success).toBe(false);
    expect(result.error).toBe("Network error");
  });
});
