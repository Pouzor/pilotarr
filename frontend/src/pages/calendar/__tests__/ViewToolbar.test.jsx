import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

vi.mock("../../../components/AppIcon", () => ({
  default: ({ name }) => <span data-testid={`icon-${name}`} />,
}));

// Button renders children or iconName as text (no children → iconName is the accessible label)
vi.mock("../../../components/ui/Button", () => ({
  default: ({ children, onClick, iconName }) => (
    <button onClick={onClick} data-icon={iconName}>
      {children || iconName}
    </button>
  ),
}));

vi.mock("../../../components/ui/Checkbox", () => ({
  Checkbox: ({ checked, onChange }) => (
    <input type="checkbox" checked={checked} onChange={onChange} />
  ),
}));

import ViewToolbar from "../components/ViewToolbar";

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

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

const defaultProps = {
  viewMode: "month",
  setViewMode: vi.fn(),
  eventFilters: { tvReleases: true, movieReleases: true, views: true },
  setEventFilters: vi.fn(),
  selectedDate: new Date(2024, 2, 15), // March 15, 2024
  monthNames,
  navigateMonth: vi.fn(),
  goToToday: vi.fn(),
};

const renderToolbar = (overrides = {}) => render(<ViewToolbar {...defaultProps} {...overrides} />);

beforeEach(() => vi.clearAllMocks());

// ---------------------------------------------------------------------------
// Month display
// ---------------------------------------------------------------------------

describe("ViewToolbar – month display", () => {
  it("shows current month name and year", () => {
    renderToolbar();
    expect(screen.getByText("March 2024")).toBeInTheDocument();
  });

  it("reflects a different selected date", () => {
    renderToolbar({ selectedDate: new Date(2024, 11, 1) }); // December
    expect(screen.getByText("December 2024")).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Navigation buttons
// ---------------------------------------------------------------------------

describe("ViewToolbar – navigation", () => {
  it("clicking ChevronLeft calls navigateMonth(-1)", async () => {
    const user = userEvent.setup();
    const navigateMonth = vi.fn();
    renderToolbar({ navigateMonth });
    await user.click(screen.getByRole("button", { name: "ChevronLeft" }));
    expect(navigateMonth).toHaveBeenCalledWith(-1);
  });

  it("clicking ChevronRight calls navigateMonth(1)", async () => {
    const user = userEvent.setup();
    const navigateMonth = vi.fn();
    renderToolbar({ navigateMonth });
    await user.click(screen.getByRole("button", { name: "ChevronRight" }));
    expect(navigateMonth).toHaveBeenCalledWith(1);
  });

  it("clicking Today calls goToToday", async () => {
    const user = userEvent.setup();
    const goToToday = vi.fn();
    renderToolbar({ goToToday });
    await user.click(screen.getByRole("button", { name: /today/i }));
    expect(goToToday).toHaveBeenCalledOnce();
  });
});

// ---------------------------------------------------------------------------
// Filter checkboxes — initial state
// ---------------------------------------------------------------------------

describe("ViewToolbar – filter checkboxes initial state", () => {
  it("all three checkboxes are checked by default", () => {
    renderToolbar();
    const checkboxes = screen.getAllByRole("checkbox");
    expect(checkboxes).toHaveLength(3);
    checkboxes.forEach((cb) => expect(cb).toBeChecked());
  });

  it("TV Episode Releases label is visible", () => {
    renderToolbar();
    expect(screen.getByText("TV Episode Releases")).toBeInTheDocument();
  });

  it("Movie Releases label is visible", () => {
    renderToolbar();
    expect(screen.getByText("Movie Releases")).toBeInTheDocument();
  });

  it("Viewing Activity label is visible", () => {
    renderToolbar();
    expect(screen.getByText("Viewing Activity")).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Filter toggles
// ---------------------------------------------------------------------------

describe("ViewToolbar – filter toggles", () => {
  it("toggling TV filter calls setEventFilters and toggles tvReleases", async () => {
    const user = userEvent.setup();
    const setEventFilters = vi.fn();
    renderToolbar({ setEventFilters });

    const [tvCheckbox] = screen.getAllByRole("checkbox");
    await user.click(tvCheckbox);

    expect(setEventFilters).toHaveBeenCalledOnce();
    const updater = setEventFilters.mock.calls[0][0];
    const result = updater({ tvReleases: true, movieReleases: true, views: true });
    expect(result).toEqual({ tvReleases: false, movieReleases: true, views: true });
  });

  it("toggling Movie filter calls setEventFilters and toggles movieReleases", async () => {
    const user = userEvent.setup();
    const setEventFilters = vi.fn();
    renderToolbar({ setEventFilters });

    const [, movieCheckbox] = screen.getAllByRole("checkbox");
    await user.click(movieCheckbox);

    const updater = setEventFilters.mock.calls[0][0];
    const result = updater({ tvReleases: true, movieReleases: true, views: true });
    expect(result).toEqual({ tvReleases: true, movieReleases: false, views: true });
  });

  it("toggling Views filter calls setEventFilters and toggles views", async () => {
    const user = userEvent.setup();
    const setEventFilters = vi.fn();
    renderToolbar({ setEventFilters });

    const [, , viewsCheckbox] = screen.getAllByRole("checkbox");
    await user.click(viewsCheckbox);

    const updater = setEventFilters.mock.calls[0][0];
    const result = updater({ tvReleases: true, movieReleases: true, views: true });
    expect(result).toEqual({ tvReleases: true, movieReleases: true, views: false });
  });

  it("reflects unchecked state from props", () => {
    renderToolbar({
      eventFilters: { tvReleases: false, movieReleases: true, views: true },
    });
    const [tvCheckbox] = screen.getAllByRole("checkbox");
    expect(tvCheckbox).not.toBeChecked();
  });
});
