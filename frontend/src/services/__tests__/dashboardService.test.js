import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("../../lib/pilotarrClient", () => ({
  default: { get: vi.fn(), post: vi.fn() },
}));

import pilotarrClient from "../../lib/pilotarrClient";
import {
  getDashboardStatistics,
  getDashboardStatistic,
  getRecentItems,
  saveDashboardStatistic,
  bulkUpdateDashboardStatistics,
} from "../dashboardService";

beforeEach(() => vi.clearAllMocks());

// ---------------------------------------------------------------------------
// getDashboardStatistics
// ---------------------------------------------------------------------------

describe("getDashboardStatistics", () => {
  it("calls /dashboard/statistics", async () => {
    pilotarrClient.get.mockResolvedValue({ data: [] });
    await getDashboardStatistics();
    expect(pilotarrClient.get).toHaveBeenCalledWith("/dashboard/statistics");
  });

  it("returns response data", async () => {
    pilotarrClient.get.mockResolvedValue({ data: [{ type: "movies", count: 42 }] });
    expect(await getDashboardStatistics()).toEqual([{ type: "movies", count: 42 }]);
  });

  it("returns empty array on error", async () => {
    pilotarrClient.get.mockRejectedValue(new Error("fail"));
    expect(await getDashboardStatistics()).toEqual([]);
  });

  it("returns empty array when data is null", async () => {
    pilotarrClient.get.mockResolvedValue({ data: null });
    expect(await getDashboardStatistics()).toEqual([]);
  });
});

// ---------------------------------------------------------------------------
// getDashboardStatistic
// ---------------------------------------------------------------------------

describe("getDashboardStatistic", () => {
  it("calls /dashboard/statistics/{statType}", async () => {
    pilotarrClient.get.mockResolvedValue({ data: { type: "movies", count: 42 } });
    await getDashboardStatistic("movies");
    expect(pilotarrClient.get).toHaveBeenCalledWith("/dashboard/statistics/movies");
  });

  it("returns the statistic object", async () => {
    pilotarrClient.get.mockResolvedValue({ data: { type: "movies", count: 42 } });
    expect(await getDashboardStatistic("movies")).toEqual({ type: "movies", count: 42 });
  });

  it("returns null on error", async () => {
    pilotarrClient.get.mockRejectedValue(new Error("fail"));
    expect(await getDashboardStatistic("movies")).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// getRecentItems
// ---------------------------------------------------------------------------

describe("getRecentItems", () => {
  it("calls /dashboard/recent-items with default limit=20", async () => {
    pilotarrClient.get.mockResolvedValue({ data: [] });
    await getRecentItems();
    expect(pilotarrClient.get).toHaveBeenCalledWith(
      expect.stringContaining("/dashboard/recent-items?limit=20"),
    );
  });

  it("passes custom limit", async () => {
    pilotarrClient.get.mockResolvedValue({ data: [] });
    await getRecentItems(5);
    expect(pilotarrClient.get).toHaveBeenCalledWith(expect.stringContaining("limit=5"));
  });

  it("returns response data", async () => {
    pilotarrClient.get.mockResolvedValue({ data: [{ id: "1", title: "Inception" }] });
    expect(await getRecentItems()).toEqual([{ id: "1", title: "Inception" }]);
  });

  it("returns empty array on error", async () => {
    pilotarrClient.get.mockRejectedValue(new Error("fail"));
    expect(await getRecentItems()).toEqual([]);
  });
});

// ---------------------------------------------------------------------------
// saveDashboardStatistic
// ---------------------------------------------------------------------------

describe("saveDashboardStatistic", () => {
  it("posts to /dashboard/statistics with correct payload", async () => {
    pilotarrClient.post.mockResolvedValue({ data: {} });
    await saveDashboardStatistic("movies", 100, { foo: "bar" });
    expect(pilotarrClient.post).toHaveBeenCalledWith(
      "/dashboard/statistics",
      expect.objectContaining({ statType: "movies", totalCount: 100, details: { foo: "bar" } }),
    );
  });

  it("includes lastSynced timestamp", async () => {
    pilotarrClient.post.mockResolvedValue({ data: {} });
    await saveDashboardStatistic("movies", 100, {});
    const payload = pilotarrClient.post.mock.calls[0][1];
    expect(payload.lastSynced).toBeDefined();
  });

  it("returns response data", async () => {
    pilotarrClient.post.mockResolvedValue({ data: { id: "stat-1" } });
    expect(await saveDashboardStatistic("movies", 100, {})).toEqual({ id: "stat-1" });
  });

  it("throws on error", async () => {
    pilotarrClient.post.mockRejectedValue(new Error("fail"));
    await expect(saveDashboardStatistic("movies", 100, {})).rejects.toThrow();
  });
});

// ---------------------------------------------------------------------------
// bulkUpdateDashboardStatistics
// ---------------------------------------------------------------------------

describe("bulkUpdateDashboardStatistics", () => {
  it("posts to /dashboard/statistics/bulk with statistics array", async () => {
    pilotarrClient.post.mockResolvedValue({ data: [] });
    const stats = [{ type: "movies" }, { type: "shows" }];
    await bulkUpdateDashboardStatistics(stats);
    expect(pilotarrClient.post).toHaveBeenCalledWith("/dashboard/statistics/bulk", {
      statistics: stats,
    });
  });

  it("returns response data", async () => {
    pilotarrClient.post.mockResolvedValue({ data: [{ type: "movies" }] });
    expect(await bulkUpdateDashboardStatistics([])).toEqual([{ type: "movies" }]);
  });

  it("throws on error", async () => {
    pilotarrClient.post.mockRejectedValue(new Error("fail"));
    await expect(bulkUpdateDashboardStatistics([])).rejects.toThrow();
  });
});
