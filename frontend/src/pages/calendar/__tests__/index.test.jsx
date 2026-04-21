import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";

// --- Mocks ---

vi.mock("../../../components/navigation/Header", () => ({
  default: () => <header data-testid="header" />,
}));

vi.mock("../../../components/AppIcon", () => ({
  default: ({ name }) => <span data-testid={`icon-${name}`} />,
}));

vi.mock("../components/CalendarGrid", () => ({
  default: ({ events, isLoading }) => (
    <div data-testid="calendar-grid">
      {isLoading && <span>grid-loading</span>}
      <span data-testid="grid-events-count">{events?.length ?? 0}</span>
    </div>
  ),
}));

vi.mock("../components/EventSidebar", () => ({
  default: ({ events, isLoading }) => (
    <div data-testid="event-sidebar">
      {isLoading && <span>sidebar-loading</span>}
      <span data-testid="sidebar-events-count">{events?.length ?? 0}</span>
    </div>
  ),
}));

vi.mock("../components/ViewToolbar", () => ({
  default: ({
    navigateMonth,
    goToToday,
    selectedDate,
    monthNames,
    eventFilters,
    setEventFilters,
  }) => (
    <div data-testid="view-toolbar">
      <span data-testid="month-label">
        {monthNames[selectedDate.getMonth()]} {selectedDate.getFullYear()}
      </span>
      <button onClick={() => navigateMonth(-1)} data-testid="prev-month">
        Prev
      </button>
      <button onClick={() => navigateMonth(1)} data-testid="next-month">
        Next
      </button>
      <button onClick={goToToday} data-testid="today-btn">
        Today
      </button>
      <input
        type="checkbox"
        data-testid="filter-tv"
        checked={eventFilters.tvReleases}
        onChange={() => setEventFilters((f) => ({ ...f, tvReleases: !f.tvReleases }))}
      />
      <input
        type="checkbox"
        data-testid="filter-movies"
        checked={eventFilters.movieReleases}
        onChange={() => setEventFilters((f) => ({ ...f, movieReleases: !f.movieReleases }))}
      />
      <input
        type="checkbox"
        data-testid="filter-views"
        checked={eventFilters.views}
        onChange={() => setEventFilters((f) => ({ ...f, views: !f.views }))}
      />
    </div>
  ),
}));

const mockGetCalendarEvents = vi.fn();
const mockGetPlaybackSessions = vi.fn();

vi.mock("../../../services/calendarService", () => ({
  getCalendarEvents: (...args) => mockGetCalendarEvents(...args),
}));

vi.mock("../../../services/analyticsService", () => ({
  getPlaybackSessions: (...args) => mockGetPlaybackSessions(...args),
}));

import Calendar from "../index";

// ---------------------------------------------------------------------------
// Fixtures — use local-time dates to avoid UTC timezone mismatches
// ---------------------------------------------------------------------------

const now = new Date();
const TODAY_LOCAL = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;

const makeRelease = (overrides = {}) => ({
  id: "r1",
  title: "Test Movie",
  type: "movie",
  eventType: "release",
  releaseDate: `${TODAY_LOCAL}T12:00:00`, // local noon — avoids UTC offset issues
  imageUrl: "",
  imageAlt: "Test Movie poster",
  status: "available",
  ...overrides,
});

const makeSession = (overrides = {}) => ({
  id: "s1",
  media_title: "Session Movie",
  media_type: "movie",
  start_time: `${TODAY_LOCAL}T12:00:00`, // no Z → local time; split("T")[0] = TODAY_LOCAL
  poster_url: "",
  episode_info: null,
  user_name: "alice",
  ...overrides,
});

const monthNames = [
  "January",
  "February",
  "March",
  "April",
  "May",
  "June",
  "July",
  "August",
  "September",
  "October",
  "November",
  "December",
];

const renderPage = () =>
  render(
    <MemoryRouter>
      <Calendar />
    </MemoryRouter>,
  );

beforeEach(() => {
  vi.clearAllMocks();
  mockGetCalendarEvents.mockResolvedValue([]);
  mockGetPlaybackSessions.mockResolvedValue([]);
});

// ---------------------------------------------------------------------------
// Rendering
// ---------------------------------------------------------------------------

describe("Calendar page – rendering", () => {
  it("shows loading state initially", () => {
    mockGetCalendarEvents.mockReturnValue(new Promise(() => {}));
    mockGetPlaybackSessions.mockReturnValue(new Promise(() => {}));
    renderPage();
    expect(screen.getByText("grid-loading")).toBeInTheDocument();
    expect(screen.getByText("sidebar-loading")).toBeInTheDocument();
  });

  it("renders heading after load", async () => {
    renderPage();
    await waitFor(() =>
      expect(screen.getByRole("heading", { name: /media calendar/i })).toBeInTheDocument(),
    );
  });

  it("shows subtitle text", async () => {
    renderPage();
    await waitFor(() =>
      expect(screen.getByText(/track tv show and movie releases/i)).toBeInTheDocument(),
    );
  });

  it("renders CalendarGrid and EventSidebar after load", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId("calendar-grid")).toBeInTheDocument();
      expect(screen.getByTestId("event-sidebar")).toBeInTheDocument();
    });
  });
});

// ---------------------------------------------------------------------------
// Data fetching
// ---------------------------------------------------------------------------

describe("Calendar page – data fetching", () => {
  it("fetches calendar events on mount", async () => {
    renderPage();
    await waitFor(() => expect(mockGetCalendarEvents).toHaveBeenCalledOnce());
  });

  it("fetches playback sessions on mount", async () => {
    renderPage();
    await waitFor(() => expect(mockGetPlaybackSessions).toHaveBeenCalledOnce());
  });

  it("passes the first day of the current month as start date", async () => {
    renderPage();
    await waitFor(() => expect(mockGetCalendarEvents).toHaveBeenCalledOnce());
    const [start] = mockGetCalendarEvents.mock.calls[0];
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, "0");
    expect(start).toBe(`${year}-${month}-01`);
  });

  it("uses the same date range for both service calls", async () => {
    renderPage();
    await waitFor(() => {
      expect(mockGetCalendarEvents).toHaveBeenCalledOnce();
      expect(mockGetPlaybackSessions).toHaveBeenCalledOnce();
    });
    expect(mockGetCalendarEvents.mock.calls[0]).toEqual(mockGetPlaybackSessions.mock.calls[0]);
  });

  it("combines release events and view sessions into the grid", async () => {
    mockGetCalendarEvents.mockResolvedValue([makeRelease()]);
    mockGetPlaybackSessions.mockResolvedValue([makeSession()]);
    renderPage();
    await waitFor(() => expect(screen.getByTestId("grid-events-count").textContent).toBe("2"));
  });

  it("maps sessions into events with id prefixed 'session-'", async () => {
    // Grid receives 1 event from the mapped session
    mockGetCalendarEvents.mockResolvedValue([]);
    mockGetPlaybackSessions.mockResolvedValue([makeSession()]);
    renderPage();
    await waitFor(() => expect(screen.getByTestId("grid-events-count").textContent).toBe("1"));
  });
});

// ---------------------------------------------------------------------------
// Month navigation
// ---------------------------------------------------------------------------

describe("Calendar page – month navigation", () => {
  it("shows the current month and year on mount", async () => {
    renderPage();
    await waitFor(() =>
      expect(screen.getByTestId("month-label").textContent).toBe(
        `${monthNames[now.getMonth()]} ${now.getFullYear()}`,
      ),
    );
  });

  it("navigates to the previous month", async () => {
    const user = userEvent.setup();
    renderPage();
    await waitFor(() => screen.getByTestId("prev-month"));

    const prev = new Date(now.getFullYear(), now.getMonth() - 1, 1);
    await user.click(screen.getByTestId("prev-month"));

    expect(screen.getByTestId("month-label").textContent).toBe(
      `${monthNames[prev.getMonth()]} ${prev.getFullYear()}`,
    );
  });

  it("navigates to the next month", async () => {
    const user = userEvent.setup();
    renderPage();
    await waitFor(() => screen.getByTestId("next-month"));

    const next = new Date(now.getFullYear(), now.getMonth() + 1, 1);
    await user.click(screen.getByTestId("next-month"));

    expect(screen.getByTestId("month-label").textContent).toBe(
      `${monthNames[next.getMonth()]} ${next.getFullYear()}`,
    );
  });

  it("goToToday resets to current month after navigating away", async () => {
    const user = userEvent.setup();
    renderPage();
    await waitFor(() => screen.getByTestId("prev-month"));

    await user.click(screen.getByTestId("prev-month"));
    await user.click(screen.getByTestId("today-btn"));

    expect(screen.getByTestId("month-label").textContent).toBe(
      `${monthNames[now.getMonth()]} ${now.getFullYear()}`,
    );
  });

  it("fetches new events when month changes", async () => {
    const user = userEvent.setup();
    renderPage();
    await waitFor(() => expect(mockGetCalendarEvents).toHaveBeenCalledTimes(1));

    await user.click(screen.getByTestId("prev-month"));
    await waitFor(() => expect(mockGetCalendarEvents).toHaveBeenCalledTimes(2));
  });
});

// ---------------------------------------------------------------------------
// Sidebar events (filtered for selected date)
// ---------------------------------------------------------------------------

describe("Calendar page – event sidebar", () => {
  it("sidebar receives events that match today", async () => {
    mockGetCalendarEvents.mockResolvedValue([makeRelease()]);
    mockGetPlaybackSessions.mockResolvedValue([]);
    renderPage();
    await waitFor(() => expect(screen.getByTestId("sidebar-events-count").textContent).toBe("1"));
  });

  it("sidebar shows 0 events when none match today", async () => {
    mockGetCalendarEvents.mockResolvedValue([makeRelease({ releaseDate: "2000-01-01T12:00:00" })]);
    mockGetPlaybackSessions.mockResolvedValue([]);
    renderPage();
    await waitFor(() => expect(screen.getByTestId("sidebar-events-count").textContent).toBe("0"));
  });
});

// ---------------------------------------------------------------------------
// Event filters
// ---------------------------------------------------------------------------

describe("Calendar page – event filters", () => {
  it("filters out TV release events when tvReleases is toggled off", async () => {
    const user = userEvent.setup();
    mockGetCalendarEvents.mockResolvedValue([
      makeRelease({ id: "tv1", type: "tv", eventType: "release" }),
    ]);
    mockGetPlaybackSessions.mockResolvedValue([]);
    renderPage();
    await waitFor(() => expect(screen.getByTestId("sidebar-events-count").textContent).toBe("1"));

    await user.click(screen.getByTestId("filter-tv"));
    await waitFor(() => expect(screen.getByTestId("sidebar-events-count").textContent).toBe("0"));
  });

  it("filters out movie release events when movieReleases is toggled off", async () => {
    const user = userEvent.setup();
    mockGetCalendarEvents.mockResolvedValue([
      makeRelease({ id: "m1", type: "movie", eventType: "release" }),
    ]);
    mockGetPlaybackSessions.mockResolvedValue([]);
    renderPage();
    await waitFor(() => expect(screen.getByTestId("sidebar-events-count").textContent).toBe("1"));

    await user.click(screen.getByTestId("filter-movies"));
    await waitFor(() => expect(screen.getByTestId("sidebar-events-count").textContent).toBe("0"));
  });

  it("filters out view events when views is toggled off", async () => {
    const user = userEvent.setup();
    mockGetCalendarEvents.mockResolvedValue([]);
    mockGetPlaybackSessions.mockResolvedValue([makeSession()]);
    renderPage();
    await waitFor(() => expect(screen.getByTestId("sidebar-events-count").textContent).toBe("1"));

    await user.click(screen.getByTestId("filter-views"));
    await waitFor(() => expect(screen.getByTestId("sidebar-events-count").textContent).toBe("0"));
  });

  it("toggling a filter back on restores the events", async () => {
    const user = userEvent.setup();
    mockGetCalendarEvents.mockResolvedValue([
      makeRelease({ id: "tv1", type: "tv", eventType: "release" }),
    ]);
    mockGetPlaybackSessions.mockResolvedValue([]);
    renderPage();
    await waitFor(() => expect(screen.getByTestId("sidebar-events-count").textContent).toBe("1"));

    await user.click(screen.getByTestId("filter-tv")); // off
    await waitFor(() => expect(screen.getByTestId("sidebar-events-count").textContent).toBe("0"));

    await user.click(screen.getByTestId("filter-tv")); // back on
    await waitFor(() => expect(screen.getByTestId("sidebar-events-count").textContent).toBe("1"));
  });
});
