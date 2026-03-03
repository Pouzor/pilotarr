import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("../../lib/pilotarrClient", () => ({
  default: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}));

import pilotarrClient from "../../lib/pilotarrClient";
import {
  getCalendarEvents,
  addCalendarEvent,
  updateCalendarEventStatus,
  deleteCalendarEvent,
} from "../calendarService";

beforeEach(() => vi.clearAllMocks());

// ---------------------------------------------------------------------------
// getCalendarEvents
// ---------------------------------------------------------------------------

describe("getCalendarEvents", () => {
  const rawEvent = {
    id: "evt-1",
    title: "Inception",
    media_type: "movie",
    release_date: "2024-06-01",
    image_url: "https://img.example.com/poster.jpg",
    image_alt: "Inception poster",
    episode: null,
    status: "announced",
  };

  it("calls /dashboard/calendar with start and end params", async () => {
    pilotarrClient.get.mockResolvedValue({ data: [] });
    await getCalendarEvents("2024-06-01", "2024-06-30");
    const url = pilotarrClient.get.mock.calls[0][0];
    expect(url).toContain("start=2024-06-01");
    expect(url).toContain("end=2024-06-30");
  });

  it("omits params when not provided", async () => {
    pilotarrClient.get.mockResolvedValue({ data: [] });
    await getCalendarEvents();
    expect(pilotarrClient.get.mock.calls[0][0]).not.toContain("start=");
  });

  it("maps snake_case fields to camelCase", async () => {
    pilotarrClient.get.mockResolvedValue({ data: [rawEvent] });
    const result = await getCalendarEvents();
    expect(result[0]).toMatchObject({
      id: "evt-1",
      title: "Inception",
      type: "movie",
      eventType: "release",
      releaseDate: "2024-06-01",
      imageUrl: "https://img.example.com/poster.jpg",
      imageAlt: "Inception poster",
      status: "announced",
    });
  });

  it("returns empty array on error", async () => {
    pilotarrClient.get.mockRejectedValue(new Error("fail"));
    expect(await getCalendarEvents()).toEqual([]);
  });

  it("returns empty array when data is null", async () => {
    pilotarrClient.get.mockResolvedValue({ data: null });
    expect(await getCalendarEvents()).toEqual([]);
  });
});

// ---------------------------------------------------------------------------
// addCalendarEvent
// ---------------------------------------------------------------------------

describe("addCalendarEvent", () => {
  it("posts to /calendar/events with event data", async () => {
    const event = { title: "New Show" };
    pilotarrClient.post.mockResolvedValue({ data: { id: "new-1", ...event } });
    await addCalendarEvent(event);
    expect(pilotarrClient.post).toHaveBeenCalledWith("/calendar/events", event);
  });

  it("returns the created event", async () => {
    pilotarrClient.post.mockResolvedValue({ data: { id: "new-1", title: "New Show" } });
    expect(await addCalendarEvent({ title: "New Show" })).toMatchObject({ id: "new-1" });
  });

  it("returns null on error", async () => {
    pilotarrClient.post.mockRejectedValue(new Error("fail"));
    expect(await addCalendarEvent({})).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// updateCalendarEventStatus
// ---------------------------------------------------------------------------

describe("updateCalendarEventStatus", () => {
  it("patches the correct endpoint with status", async () => {
    pilotarrClient.patch.mockResolvedValue({});
    await updateCalendarEventStatus("evt-1", "released");
    expect(pilotarrClient.patch).toHaveBeenCalledWith("/calendar/events/evt-1", {
      status: "released",
    });
  });

  it("returns true on success", async () => {
    pilotarrClient.patch.mockResolvedValue({});
    expect(await updateCalendarEventStatus("evt-1", "released")).toBe(true);
  });

  it("returns false on error", async () => {
    pilotarrClient.patch.mockRejectedValue(new Error("fail"));
    expect(await updateCalendarEventStatus("evt-1", "released")).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// deleteCalendarEvent
// ---------------------------------------------------------------------------

describe("deleteCalendarEvent", () => {
  it("calls DELETE on the correct endpoint", async () => {
    pilotarrClient.delete.mockResolvedValue({});
    await deleteCalendarEvent("evt-1");
    expect(pilotarrClient.delete).toHaveBeenCalledWith("/calendar/events/evt-1");
  });

  it("returns true on success", async () => {
    pilotarrClient.delete.mockResolvedValue({});
    expect(await deleteCalendarEvent("evt-1")).toBe(true);
  });

  it("returns false on error", async () => {
    pilotarrClient.delete.mockRejectedValue(new Error("fail"));
    expect(await deleteCalendarEvent("evt-1")).toBe(false);
  });
});
