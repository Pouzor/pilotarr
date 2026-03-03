import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("../../lib/pilotarrClient", () => ({
  default: { get: vi.fn(), post: vi.fn() },
}));

import pilotarrClient from "../../lib/pilotarrClient";
import {
  getUsageAnalytics,
  getDeviceBreakdown,
  getMediaAnalytics,
  getServerMetrics,
  getPlaybackSessions,
  getUserLeaderboard,
} from "../analyticsService";

beforeEach(() => vi.clearAllMocks());

// ---------------------------------------------------------------------------
// getUsageAnalytics
// ---------------------------------------------------------------------------

describe("getUsageAnalytics", () => {
  it("calls /analytics/usage with start_date and end_date params", async () => {
    pilotarrClient.get.mockResolvedValue({ data: [] });
    await getUsageAnalytics("2024-01-01", "2024-01-31");
    expect(pilotarrClient.get).toHaveBeenCalledWith("/analytics/usage", {
      params: { start_date: "2024-01-01", end_date: "2024-01-31" },
    });
  });

  it("returns response data", async () => {
    pilotarrClient.get.mockResolvedValue({ data: [{ date: "2024-01-01", hours: 2 }] });
    const result = await getUsageAnalytics("2024-01-01", "2024-01-31");
    expect(result).toEqual([{ date: "2024-01-01", hours: 2 }]);
  });

  it("returns empty array on error", async () => {
    pilotarrClient.get.mockRejectedValue(new Error("Network error"));
    expect(await getUsageAnalytics()).toEqual([]);
  });

  it("returns empty array when data is null", async () => {
    pilotarrClient.get.mockResolvedValue({ data: null });
    expect(await getUsageAnalytics()).toEqual([]);
  });
});

// ---------------------------------------------------------------------------
// getDeviceBreakdown
// ---------------------------------------------------------------------------

describe("getDeviceBreakdown", () => {
  it("calls /analytics/devices with default period_days=365", async () => {
    pilotarrClient.get.mockResolvedValue({ data: [] });
    await getDeviceBreakdown();
    expect(pilotarrClient.get).toHaveBeenCalledWith("/analytics/devices", {
      params: { period_days: 365 },
    });
  });

  it("passes custom period_days", async () => {
    pilotarrClient.get.mockResolvedValue({ data: [] });
    await getDeviceBreakdown(30);
    expect(pilotarrClient.get).toHaveBeenCalledWith("/analytics/devices", {
      params: { period_days: 30 },
    });
  });

  it("returns response data", async () => {
    pilotarrClient.get.mockResolvedValue({ data: [{ device: "Chrome", pct: 60 }] });
    const result = await getDeviceBreakdown();
    expect(result).toEqual([{ device: "Chrome", pct: 60 }]);
  });

  it("returns empty array on error", async () => {
    pilotarrClient.get.mockRejectedValue(new Error("fail"));
    expect(await getDeviceBreakdown()).toEqual([]);
  });
});

// ---------------------------------------------------------------------------
// getMediaAnalytics
// ---------------------------------------------------------------------------

describe("getMediaAnalytics", () => {
  it("calls /analytics/media with default params", async () => {
    pilotarrClient.get.mockResolvedValue({ data: [] });
    await getMediaAnalytics();
    expect(pilotarrClient.get).toHaveBeenCalledWith("/analytics/media", {
      params: { limit: 10, sort_by: "plays", order: "desc" },
    });
  });

  it("passes custom limit, sortBy and order", async () => {
    pilotarrClient.get.mockResolvedValue({ data: [] });
    await getMediaAnalytics(5, "duration", "asc");
    expect(pilotarrClient.get).toHaveBeenCalledWith("/analytics/media", {
      params: { limit: 5, sort_by: "duration", order: "asc" },
    });
  });

  it("returns response data", async () => {
    pilotarrClient.get.mockResolvedValue({ data: [{ title: "Inception", plays: 3 }] });
    expect(await getMediaAnalytics()).toEqual([{ title: "Inception", plays: 3 }]);
  });

  it("returns empty array on error", async () => {
    pilotarrClient.get.mockRejectedValue(new Error("fail"));
    expect(await getMediaAnalytics()).toEqual([]);
  });
});

// ---------------------------------------------------------------------------
// getServerMetrics
// ---------------------------------------------------------------------------

describe("getServerMetrics", () => {
  it("calls /analytics/server-metrics", async () => {
    pilotarrClient.get.mockResolvedValue({ data: { cpu: 42 } });
    await getServerMetrics();
    expect(pilotarrClient.get).toHaveBeenCalledWith("/analytics/server-metrics");
  });

  it("returns the metrics object", async () => {
    pilotarrClient.get.mockResolvedValue({ data: { cpu: 42, memory: 70 } });
    expect(await getServerMetrics()).toEqual({ cpu: 42, memory: 70 });
  });

  it("returns null on error", async () => {
    pilotarrClient.get.mockRejectedValue(new Error("fail"));
    expect(await getServerMetrics()).toBeNull();
  });

  it("returns null when data is null", async () => {
    pilotarrClient.get.mockResolvedValue({ data: null });
    expect(await getServerMetrics()).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// getPlaybackSessions
// ---------------------------------------------------------------------------

describe("getPlaybackSessions", () => {
  it("appends start and end query params when provided", async () => {
    pilotarrClient.get.mockResolvedValue({ data: [] });
    await getPlaybackSessions("2024-01-01", "2024-01-31");
    const url = pilotarrClient.get.mock.calls[0][0];
    expect(url).toContain("start=2024-01-01");
    expect(url).toContain("end=2024-01-31");
  });

  it("omits params when not provided", async () => {
    pilotarrClient.get.mockResolvedValue({ data: [] });
    await getPlaybackSessions();
    const url = pilotarrClient.get.mock.calls[0][0];
    expect(url).not.toContain("start=");
    expect(url).not.toContain("end=");
  });

  it("returns response data", async () => {
    pilotarrClient.get.mockResolvedValue({ data: [{ id: "s1" }] });
    expect(await getPlaybackSessions()).toEqual([{ id: "s1" }]);
  });

  it("returns empty array on error", async () => {
    pilotarrClient.get.mockRejectedValue(new Error("fail"));
    expect(await getPlaybackSessions()).toEqual([]);
  });
});

// ---------------------------------------------------------------------------
// getUserLeaderboard
// ---------------------------------------------------------------------------

describe("getUserLeaderboard", () => {
  it("calls /analytics/users with default limit=10", async () => {
    pilotarrClient.get.mockResolvedValue({ data: [] });
    await getUserLeaderboard();
    expect(pilotarrClient.get).toHaveBeenCalledWith("/analytics/users", { params: { limit: 10 } });
  });

  it("passes custom limit", async () => {
    pilotarrClient.get.mockResolvedValue({ data: [] });
    await getUserLeaderboard(5);
    expect(pilotarrClient.get).toHaveBeenCalledWith("/analytics/users", { params: { limit: 5 } });
  });

  it("returns response data", async () => {
    pilotarrClient.get.mockResolvedValue({ data: [{ user: "alice", hours: 10 }] });
    expect(await getUserLeaderboard()).toEqual([{ user: "alice", hours: 10 }]);
  });

  it("returns empty array on error", async () => {
    pilotarrClient.get.mockRejectedValue(new Error("fail"));
    expect(await getUserLeaderboard()).toEqual([]);
  });
});
