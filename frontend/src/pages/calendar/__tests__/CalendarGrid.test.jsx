import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

vi.mock("../../../components/AppIcon", () => ({
  default: ({ name }) => <span data-testid={`icon-${name}`} />,
}));

import CalendarGrid from "../components/CalendarGrid";

// ---------------------------------------------------------------------------
// Fixtures — January 2024: starts Monday (day 1), 31 days
// ---------------------------------------------------------------------------

// Jan 15, 2024 (local noon avoids UTC timezone mismatches)
const JAN_15_2024 = new Date(2024, 0, 15);

const defaultFilters = { tvReleases: true, movieReleases: true, views: true };

const makeEvent = (overrides = {}) => ({
  id: "e1",
  title: "Test Event",
  type: "movie",
  eventType: "release",
  // Local noon on Jan 15 — new Date("2024-01-15T12:00:00") is local time, getDate()=15 everywhere
  releaseDate: "2024-01-15T12:00:00",
  ...overrides,
});

const renderGrid = (props = {}) =>
  render(
    <CalendarGrid
      selectedDate={JAN_15_2024}
      setSelectedDate={vi.fn()}
      events={[]}
      eventFilters={defaultFilters}
      viewMode="month"
      isLoading={false}
      {...props}
    />,
  );

beforeEach(() => vi.clearAllMocks());

// ---------------------------------------------------------------------------
// Loading state
// ---------------------------------------------------------------------------

describe("CalendarGrid – loading state", () => {
  it("shows loading spinner when isLoading is true", () => {
    renderGrid({ isLoading: true });
    expect(screen.getByTestId("icon-Loader2")).toBeInTheDocument();
  });

  it("does not render day headers while loading", () => {
    renderGrid({ isLoading: true });
    expect(screen.queryByText("Sun")).not.toBeInTheDocument();
  });

  it("does not render day cells while loading", () => {
    renderGrid({ isLoading: true });
    expect(screen.queryByText("1")).not.toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Month view structure
// ---------------------------------------------------------------------------

describe("CalendarGrid – month view structure", () => {
  it("renders all 7 day name headers", () => {
    renderGrid();
    ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].forEach((day) => {
      expect(screen.getByText(day)).toBeInTheDocument();
    });
  });

  it("renders all 31 days for January", () => {
    renderGrid();
    for (let d = 1; d <= 31; d++) {
      expect(screen.getByText(String(d))).toBeInTheDocument();
    }
  });

  it("shows legend entries", () => {
    renderGrid();
    expect(screen.getByText("TV Episode Release")).toBeInTheDocument();
    expect(screen.getByText("Movie Release")).toBeInTheDocument();
    expect(screen.getByText("Viewing Activity")).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Day selection
// ---------------------------------------------------------------------------

describe("CalendarGrid – day selection", () => {
  it("clicking a day calls setSelectedDate with that date", async () => {
    const user = userEvent.setup();
    const setSelectedDate = vi.fn();
    renderGrid({ setSelectedDate });
    await user.click(screen.getByText("10"));
    expect(setSelectedDate).toHaveBeenCalledWith(new Date(2024, 0, 10));
  });

  it("clicking different days calls setSelectedDate with correct dates", async () => {
    const user = userEvent.setup();
    const setSelectedDate = vi.fn();
    renderGrid({ setSelectedDate });
    await user.click(screen.getByText("20"));
    expect(setSelectedDate).toHaveBeenCalledWith(new Date(2024, 0, 20));
  });
});

// ---------------------------------------------------------------------------
// Event dots
// ---------------------------------------------------------------------------

describe("CalendarGrid – event dots", () => {
  it("shows an event dot (title attribute) for a day that has an event", () => {
    const event = makeEvent({ title: "Inception" });
    renderGrid({ events: [event] });
    expect(screen.getByTitle("Inception")).toBeInTheDocument();
  });

  it("shows '+N more' when a day has more than 3 events", () => {
    const events = Array.from({ length: 5 }, (_, i) =>
      makeEvent({ id: `e${i}`, title: `Event ${i}` }),
    );
    renderGrid({ events });
    expect(screen.getByText("+2 more")).toBeInTheDocument();
  });

  it("does not show '+N more' when 3 or fewer events", () => {
    const events = Array.from({ length: 3 }, (_, i) =>
      makeEvent({ id: `e${i}`, title: `Event ${i}` }),
    );
    renderGrid({ events });
    expect(screen.queryByText(/more/)).not.toBeInTheDocument();
  });

  it("does not show dots for events on other days", () => {
    const event = makeEvent({ releaseDate: "2024-01-20T12:00:00", title: "Jan 20 Movie" });
    renderGrid({ events: [event] });
    // Jan 15 has no event dot, Jan 20 has one
    expect(screen.getByTitle("Jan 20 Movie")).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Event filters
// ---------------------------------------------------------------------------

describe("CalendarGrid – event filters", () => {
  it("hides TV release events when tvReleases filter is off", () => {
    const event = makeEvent({ type: "tv", eventType: "release", title: "TV Show" });
    renderGrid({ events: [event], eventFilters: { ...defaultFilters, tvReleases: false } });
    expect(screen.queryByTitle("TV Show")).not.toBeInTheDocument();
  });

  it("shows TV release events when tvReleases filter is on", () => {
    const event = makeEvent({ type: "tv", eventType: "release", title: "TV Show" });
    renderGrid({ events: [event], eventFilters: defaultFilters });
    expect(screen.getByTitle("TV Show")).toBeInTheDocument();
  });

  it("hides movie release events when movieReleases filter is off", () => {
    const event = makeEvent({ type: "movie", eventType: "release", title: "Movie Title" });
    renderGrid({ events: [event], eventFilters: { ...defaultFilters, movieReleases: false } });
    expect(screen.queryByTitle("Movie Title")).not.toBeInTheDocument();
  });

  it("shows movie release events when movieReleases filter is on", () => {
    const event = makeEvent({ type: "movie", eventType: "release", title: "Movie Title" });
    renderGrid({ events: [event], eventFilters: defaultFilters });
    expect(screen.getByTitle("Movie Title")).toBeInTheDocument();
  });

  it("hides view events when views filter is off", () => {
    const event = makeEvent({ eventType: "view", title: "Viewed Movie" });
    renderGrid({ events: [event], eventFilters: { ...defaultFilters, views: false } });
    expect(screen.queryByTitle("Viewed Movie")).not.toBeInTheDocument();
  });

  it("shows view events when views filter is on", () => {
    const event = makeEvent({ eventType: "view", title: "Viewed Movie" });
    renderGrid({ events: [event], eventFilters: defaultFilters });
    expect(screen.getByTitle("Viewed Movie")).toBeInTheDocument();
  });

  it("hides all events when all filters are off", () => {
    const events = [
      makeEvent({ id: "e1", type: "tv", eventType: "release", title: "TV" }),
      makeEvent({ id: "e2", type: "movie", eventType: "release", title: "Movie" }),
      makeEvent({ id: "e3", eventType: "view", title: "View" }),
    ];
    renderGrid({
      events,
      eventFilters: { tvReleases: false, movieReleases: false, views: false },
    });
    expect(screen.queryByTitle("TV")).not.toBeInTheDocument();
    expect(screen.queryByTitle("Movie")).not.toBeInTheDocument();
    expect(screen.queryByTitle("View")).not.toBeInTheDocument();
  });
});
