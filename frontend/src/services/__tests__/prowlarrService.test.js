import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("../../lib/pilotarrClient", () => ({
  default: { get: vi.fn(), post: vi.fn(), patch: vi.fn() },
}));

import pilotarrClient from "../../lib/pilotarrClient";
import {
  getIndexers,
  toggleIndexer,
  getHistory,
  searchIndexers,
  grabResult,
} from "../prowlarrService";

beforeEach(() => vi.clearAllMocks());

// ---------------------------------------------------------------------------
// getIndexers
// ---------------------------------------------------------------------------

describe("getIndexers", () => {
  it("calls /prowlarr/indexers", async () => {
    pilotarrClient.get.mockResolvedValue({ data: [] });
    await getIndexers();
    expect(pilotarrClient.get).toHaveBeenCalledWith("/prowlarr/indexers");
  });

  it("returns response data", async () => {
    pilotarrClient.get.mockResolvedValue({ data: [{ id: 1, name: "NZBGeek" }] });
    expect(await getIndexers()).toEqual([{ id: 1, name: "NZBGeek" }]);
  });

  it("returns empty array when data is null", async () => {
    pilotarrClient.get.mockResolvedValue({ data: null });
    expect(await getIndexers()).toEqual([]);
  });

  it("propagates errors (no silent catch)", async () => {
    pilotarrClient.get.mockRejectedValue(new Error("503"));
    await expect(getIndexers()).rejects.toThrow("503");
  });
});

// ---------------------------------------------------------------------------
// toggleIndexer
// ---------------------------------------------------------------------------

describe("toggleIndexer", () => {
  it("patches /prowlarr/indexers/{id} with enable flag", async () => {
    pilotarrClient.patch.mockResolvedValue({});
    await toggleIndexer(42, true);
    expect(pilotarrClient.patch).toHaveBeenCalledWith("/prowlarr/indexers/42", { enable: true });
  });

  it("returns true on success", async () => {
    pilotarrClient.patch.mockResolvedValue({});
    expect(await toggleIndexer(42, false)).toBe(true);
  });

  it("returns false on error", async () => {
    pilotarrClient.patch.mockRejectedValue(new Error("fail"));
    expect(await toggleIndexer(42, true)).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// getHistory
// ---------------------------------------------------------------------------

describe("getHistory", () => {
  it("calls /prowlarr/history with default limit=20", async () => {
    pilotarrClient.get.mockResolvedValue({ data: [] });
    await getHistory();
    expect(pilotarrClient.get).toHaveBeenCalledWith("/prowlarr/history?limit=20");
  });

  it("passes custom limit", async () => {
    pilotarrClient.get.mockResolvedValue({ data: [] });
    await getHistory(50);
    expect(pilotarrClient.get).toHaveBeenCalledWith("/prowlarr/history?limit=50");
  });

  it("returns response data", async () => {
    pilotarrClient.get.mockResolvedValue({ data: [{ id: "h1" }] });
    expect(await getHistory()).toEqual([{ id: "h1" }]);
  });

  it("propagates errors", async () => {
    pilotarrClient.get.mockRejectedValue(new Error("503"));
    await expect(getHistory()).rejects.toThrow("503");
  });
});

// ---------------------------------------------------------------------------
// searchIndexers
// ---------------------------------------------------------------------------

describe("searchIndexers", () => {
  it("calls /prowlarr/search with query and default type=search", async () => {
    pilotarrClient.get.mockResolvedValue({ data: [] });
    await searchIndexers("inception");
    const url = pilotarrClient.get.mock.calls[0][0];
    expect(url).toContain("query=inception");
    expect(url).toContain("type=search");
  });

  it("passes custom type", async () => {
    pilotarrClient.get.mockResolvedValue({ data: [] });
    await searchIndexers("inception", "movie");
    expect(pilotarrClient.get.mock.calls[0][0]).toContain("type=movie");
  });

  it("returns response data", async () => {
    pilotarrClient.get.mockResolvedValue({ data: [{ title: "Inception 1080p" }] });
    expect(await searchIndexers("inception")).toEqual([{ title: "Inception 1080p" }]);
  });

  it("propagates errors", async () => {
    pilotarrClient.get.mockRejectedValue(new Error("fail"));
    await expect(searchIndexers("inception")).rejects.toThrow();
  });
});

// ---------------------------------------------------------------------------
// grabResult
// ---------------------------------------------------------------------------

describe("grabResult", () => {
  it("posts to /prowlarr/grab with guid and indexerId", async () => {
    pilotarrClient.post.mockResolvedValue({});
    await grabResult("guid-abc", 7);
    expect(pilotarrClient.post).toHaveBeenCalledWith("/prowlarr/grab", {
      guid: "guid-abc",
      indexerId: 7,
    });
  });

  it("returns true on success", async () => {
    pilotarrClient.post.mockResolvedValue({});
    expect(await grabResult("guid-abc", 7)).toBe(true);
  });

  it("returns false on error", async () => {
    pilotarrClient.post.mockRejectedValue(new Error("fail"));
    expect(await grabResult("guid-abc", 7)).toBe(false);
  });
});
