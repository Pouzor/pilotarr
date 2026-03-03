import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("../../lib/pilotarrClient", () => ({
  default: { get: vi.fn() },
}));

import pilotarrClient from "../../lib/pilotarrClient";
import { getMonitoringItems } from "../monitoringService";

beforeEach(() => vi.clearAllMocks());

describe("getMonitoringItems", () => {
  it("calls /monitoring/items", async () => {
    pilotarrClient.get.mockResolvedValue({ data: [] });
    await getMonitoringItems();
    expect(pilotarrClient.get).toHaveBeenCalledWith("/monitoring/items");
  });

  it("returns response data", async () => {
    const items = [{ id: "1", title: "Inception", monitoring_status: "monitored" }];
    pilotarrClient.get.mockResolvedValue({ data: items });
    expect(await getMonitoringItems()).toEqual(items);
  });

  it("returns empty array when data is null", async () => {
    pilotarrClient.get.mockResolvedValue({ data: null });
    expect(await getMonitoringItems()).toEqual([]);
  });

  it("returns empty array on error", async () => {
    pilotarrClient.get.mockRejectedValue(new Error("Network error"));
    expect(await getMonitoringItems()).toEqual([]);
  });
});
