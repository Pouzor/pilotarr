import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("../../lib/pilotarrClient", () => ({
  default: { get: vi.fn() },
}));

import pilotarrClient from "../../lib/pilotarrClient";
import { getTorrents } from "../torrentService";

beforeEach(() => vi.clearAllMocks());

describe("getTorrents", () => {
  it("calls /torrents/all", async () => {
    pilotarrClient.get.mockResolvedValue({ data: [] });
    await getTorrents();
    expect(pilotarrClient.get).toHaveBeenCalledWith("/torrents/all");
  });

  it("returns response data", async () => {
    const torrents = [{ hash: "abc123", name: "Inception.mkv", progress: 1.0 }];
    pilotarrClient.get.mockResolvedValue({ data: torrents });
    expect(await getTorrents()).toEqual(torrents);
  });

  it("propagates errors (no silent catch)", async () => {
    pilotarrClient.get.mockRejectedValue(new Error("503 Service Unavailable"));
    await expect(getTorrents()).rejects.toThrow("503 Service Unavailable");
  });
});
