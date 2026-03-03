import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";

vi.mock("../../../components/AppIcon", () => ({
  default: ({ name }) => <span data-testid={`icon-${name}`} />,
}));

vi.mock("../../../components/AppImage", () => ({
  default: ({ alt }) => <img alt={alt} />,
}));

import EventSidebar from "../components/EventSidebar";

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const SELECTED_DATE = new Date(2024, 0, 15); // Monday, January 15, 2024

const makeEvent = (overrides = {}) => ({
  id: "e1",
  title: "Inception",
  type: "movie",
  eventType: "release",
  releaseDate: "2024-01-15",
  imageUrl: "/poster.jpg",
  imageAlt: "Inception poster",
  status: "available",
  ...overrides,
});

const renderSidebar = (props = {}) =>
  render(<EventSidebar selectedDate={SELECTED_DATE} events={[]} isLoading={false} {...props} />);

// ---------------------------------------------------------------------------
// Loading state
// ---------------------------------------------------------------------------

describe("EventSidebar – loading state", () => {
  it("shows loading spinner when isLoading is true", () => {
    renderSidebar({ isLoading: true });
    expect(screen.getByTestId("icon-Loader2")).toBeInTheDocument();
  });

  it("does not show events while loading", () => {
    renderSidebar({ isLoading: true, events: [makeEvent()] });
    expect(screen.queryByText("Inception")).not.toBeInTheDocument();
  });

  it("does not show empty-state message while loading", () => {
    renderSidebar({ isLoading: true });
    expect(screen.queryByText(/no events for this date/i)).not.toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Header
// ---------------------------------------------------------------------------

describe("EventSidebar – header", () => {
  it("shows 'Events' heading", () => {
    renderSidebar();
    expect(screen.getByRole("heading", { name: "Events" })).toBeInTheDocument();
  });

  it("shows formatted selected date", () => {
    renderSidebar();
    // Jan 15, 2024 → "Monday, January 15, 2024"
    expect(screen.getByText(/january 15, 2024/i)).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Empty state
// ---------------------------------------------------------------------------

describe("EventSidebar – empty state", () => {
  it("shows 'No events for this date' when events list is empty", () => {
    renderSidebar();
    expect(screen.getByText(/no events for this date/i)).toBeInTheDocument();
  });

  it("shows Calendar icon in empty state", () => {
    renderSidebar();
    expect(screen.getByTestId("icon-Calendar")).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Event cards — type badges
// ---------------------------------------------------------------------------

describe("EventSidebar – event type badges", () => {
  it("shows 'Movie Release' badge for a movie release event", () => {
    renderSidebar({ events: [makeEvent({ type: "movie", eventType: "release" })] });
    expect(screen.getByText("Movie Release")).toBeInTheDocument();
  });

  it("shows 'TV Episode Release' badge for a TV release event", () => {
    renderSidebar({ events: [makeEvent({ type: "tv", eventType: "release" })] });
    expect(screen.getByText("TV Episode Release")).toBeInTheDocument();
  });

  it("shows 'Viewed' badge for a view event", () => {
    renderSidebar({ events: [makeEvent({ eventType: "view" })] });
    expect(screen.getByText("Viewed")).toBeInTheDocument();
  });

  it("shows 'Download' badge for a download event", () => {
    renderSidebar({ events: [makeEvent({ eventType: "download" })] });
    expect(screen.getByText("Download")).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Event cards — content fields
// ---------------------------------------------------------------------------

describe("EventSidebar – event card content", () => {
  it("renders the event title", () => {
    renderSidebar({ events: [makeEvent()] });
    expect(screen.getByText("Inception")).toBeInTheDocument();
  });

  it("shows episode info when event has an episode field", () => {
    renderSidebar({ events: [makeEvent({ episode: "S01E05 - Pilot" })] });
    expect(screen.getByText("S01E05 - Pilot")).toBeInTheDocument();
  });

  it("does not show episode section when episode is null", () => {
    renderSidebar({ events: [makeEvent({ episode: null })] });
    expect(screen.queryByText(/S\d+E\d+/)).not.toBeInTheDocument();
  });

  it("shows download progress bar when progress is defined", () => {
    renderSidebar({ events: [makeEvent({ progress: 65 })] });
    expect(screen.getByText("Download Progress")).toBeInTheDocument();
    expect(screen.getByText("65%")).toBeInTheDocument();
  });

  it("does not show download progress when progress is undefined", () => {
    renderSidebar({ events: [makeEvent()] });
    expect(screen.queryByText("Download Progress")).not.toBeInTheDocument();
  });

  it("shows 'Viewed by' info when viewedBy is present", () => {
    renderSidebar({ events: [makeEvent({ viewedBy: "alice" })] });
    expect(screen.getByText("Viewed by alice")).toBeInTheDocument();
  });

  it("does not show 'Viewed by' when viewedBy is absent", () => {
    renderSidebar({ events: [makeEvent()] });
    expect(screen.queryByText(/viewed by/i)).not.toBeInTheDocument();
  });

  it("shows capitalized status badge", () => {
    renderSidebar({ events: [makeEvent({ status: "available" })] });
    expect(screen.getByText("available")).toBeInTheDocument();
  });

  it("renders poster image with correct alt text", () => {
    renderSidebar({ events: [makeEvent({ imageAlt: "Inception poster" })] });
    expect(screen.getByAltText("Inception poster")).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Multiple events
// ---------------------------------------------------------------------------

describe("EventSidebar – multiple events", () => {
  it("renders all events in the list", () => {
    const events = [
      makeEvent({ id: "e1", title: "Movie A" }),
      makeEvent({ id: "e2", title: "Movie B" }),
      makeEvent({ id: "e3", title: "Movie C" }),
    ];
    renderSidebar({ events });
    expect(screen.getByText("Movie A")).toBeInTheDocument();
    expect(screen.getByText("Movie B")).toBeInTheDocument();
    expect(screen.getByText("Movie C")).toBeInTheDocument();
  });

  it("does not show empty-state message when there are events", () => {
    renderSidebar({ events: [makeEvent()] });
    expect(screen.queryByText(/no events for this date/i)).not.toBeInTheDocument();
  });
});
