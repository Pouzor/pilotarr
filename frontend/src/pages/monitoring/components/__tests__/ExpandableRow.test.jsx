import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";

vi.mock("../../../../components/AppIcon", () => ({
  default: ({ name }) => <span data-testid={`icon-${name}`} />,
}));

import ExpandableRow from "../ExpandableRow";

const movieItem = {
  id: "1",
  title: "Inception",
  service: "radarr",
  monitoringStatus: "monitored",
  fileSize: "12.4 GB",
  downloadHistory: [
    { date: "2024-01-10", action: "Downloaded", quality: "1080p" },
    { date: "2024-02-01", action: "Downloaded", quality: "4K" },
  ],
};

const tvItem = {
  id: "2",
  title: "Breaking Bad",
  service: "sonarr",
  monitoringStatus: "monitored",
  fileSize: "50 GB",
  seasons: [
    { number: 1, episodes: 7, monitored: 7, available: 7, is_monitored: true },
    { number: 2, episodes: 13, monitored: 13, available: 10, is_monitored: true },
  ],
  downloadHistory: [],
};

describe("ExpandableRow – movie (radarr)", () => {
  it("shows File Information section", () => {
    render(<ExpandableRow item={movieItem} />);
    expect(screen.getByText("File Information")).toBeInTheDocument();
  });

  it("shows file size", () => {
    render(<ExpandableRow item={movieItem} />);
    expect(screen.getByText("12.4 GB")).toBeInTheDocument();
  });

  it("does not show Season Information for movies", () => {
    render(<ExpandableRow item={movieItem} />);
    expect(screen.queryByText("Season Information")).not.toBeInTheDocument();
  });

  it("shows download history entries", () => {
    render(<ExpandableRow item={movieItem} />);
    expect(screen.getAllByText("Downloaded").length).toBeGreaterThan(0);
    expect(screen.getAllByText("1080p").length).toBeGreaterThan(0);
  });

  it("does not show Unmonitor/Monitor action buttons", () => {
    render(<ExpandableRow item={movieItem} />);
    expect(screen.queryByText("Unmonitor")).not.toBeInTheDocument();
    render(<ExpandableRow item={{ ...movieItem, monitoringStatus: "unmonitored" }} />);
    expect(screen.queryByText("Monitor")).not.toBeInTheDocument();
  });
});

describe("ExpandableRow – TV show (sonarr)", () => {
  it("shows Season Information section", () => {
    render(<ExpandableRow item={tvItem} />);
    expect(screen.getByText("Season Information")).toBeInTheDocument();
  });

  it("renders a row for each season", () => {
    render(<ExpandableRow item={tvItem} />);
    expect(screen.getByText("S1")).toBeInTheDocument();
    expect(screen.getByText("S2")).toBeInTheDocument();
  });

  it("shows episode counts for each season", () => {
    render(<ExpandableRow item={tvItem} />);
    expect(screen.getByText("7/7 episodes")).toBeInTheDocument();
    expect(screen.getByText("10/13 episodes")).toBeInTheDocument();
  });

  it("shows 'No download history' when history is empty", () => {
    render(<ExpandableRow item={tvItem} />);
    expect(screen.getByText("No download history")).toBeInTheDocument();
  });
});
