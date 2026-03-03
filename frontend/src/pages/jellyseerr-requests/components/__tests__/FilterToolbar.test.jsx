import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

vi.mock("../../../../components/AppIcon", () => ({
  default: ({ name }) => <span data-testid={`icon-${name}`} />,
}));

// Minimal Select stub that renders a native <select>
vi.mock("../../../../components/ui/Select", () => ({
  default: ({ options, value, onChange, placeholder }) => (
    <select
      aria-label={placeholder}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      data-testid={`select-${placeholder}`}
    >
      {options.map((o) => (
        <option key={o.value} value={o.value}>
          {o.label}
        </option>
      ))}
    </select>
  ),
}));

vi.mock("../../../../components/ui/Button", () => ({
  default: ({ children, onClick }) => <button onClick={onClick}>{children}</button>,
}));

import FilterToolbar from "../FilterToolbar";

const defaultFilters = { status: "all", type: "all", user: "all" };
const defaultUniqueUsers = ["all", "Alice", "Bob"];

const defaultProps = {
  searchQuery: "",
  onSearchChange: vi.fn(),
  filters: defaultFilters,
  onFilterChange: vi.fn(),
  totalResults: 10,
  uniqueUsers: defaultUniqueUsers,
};

const render$ = (props = {}) => render(<FilterToolbar {...defaultProps} {...props} />);

beforeEach(() => {
  vi.clearAllMocks();
});

// ── Rendering ─────────────────────────────────────────────────────────────────

describe("FilterToolbar – rendering", () => {
  it("renders the search input", () => {
    render$();
    expect(screen.getByPlaceholderText(/search requests by title/i)).toBeInTheDocument();
  });

  it("renders the status select", () => {
    render$();
    expect(screen.getByTestId("select-Status")).toBeInTheDocument();
  });

  it("renders the type select", () => {
    render$();
    expect(screen.getByTestId("select-Request Type")).toBeInTheDocument();
  });

  it("renders the user select", () => {
    render$();
    expect(screen.getByTestId("select-Requested By")).toBeInTheDocument();
  });

  it("shows total results count (plural)", () => {
    render$({ totalResults: 10 });
    expect(screen.getByText("10")).toBeInTheDocument();
    expect(screen.getByText(/requests/)).toBeInTheDocument();
  });

  it("shows singular 'request' when totalResults is 1", () => {
    render$({ totalResults: 1 });
    expect(screen.getByText("1")).toBeInTheDocument();
    expect(screen.getByText(/\brequest\b/)).toBeInTheDocument();
    expect(screen.queryByText(/\brequests\b/)).not.toBeInTheDocument();
  });

  it("reflects uniqueUsers list as options in user select", () => {
    render$({ uniqueUsers: ["all", "Alice", "Bob", "Charlie"] });
    const select = screen.getByTestId("select-Requested By");
    const options = Array.from(select.querySelectorAll("option")).map((o) => o.value);
    expect(options).toContain("all");
    expect(options).toContain("Alice");
    expect(options).toContain("Bob");
    expect(options).toContain("Charlie");
  });

  it("labels 'all' user option as 'All Users'", () => {
    render$({ uniqueUsers: ["all", "Alice"] });
    const select = screen.getByTestId("select-Requested By");
    const allOption = Array.from(select.querySelectorAll("option")).find((o) => o.value === "all");
    expect(allOption?.textContent).toBe("All Users");
  });
});

// ── Clear Filters visibility ──────────────────────────────────────────────────

describe("FilterToolbar – Clear Filters button visibility", () => {
  it("does NOT show Clear Filters when all filters are 'all' and no search", () => {
    render$();
    expect(screen.queryByText(/clear filters/i)).not.toBeInTheDocument();
  });

  it("shows Clear Filters when searchQuery is set", () => {
    render$({ searchQuery: "Inception" });
    expect(screen.getByText(/clear filters/i)).toBeInTheDocument();
  });

  it("shows Clear Filters when status filter is not 'all'", () => {
    render$({ filters: { ...defaultFilters, status: "pending" } });
    expect(screen.getByText(/clear filters/i)).toBeInTheDocument();
  });

  it("shows Clear Filters when type filter is not 'all'", () => {
    render$({ filters: { ...defaultFilters, type: "movie" } });
    expect(screen.getByText(/clear filters/i)).toBeInTheDocument();
  });

  it("shows Clear Filters when user filter is not 'all'", () => {
    render$({ filters: { ...defaultFilters, user: "Alice" } });
    expect(screen.getByText(/clear filters/i)).toBeInTheDocument();
  });
});

// ── Interactions ──────────────────────────────────────────────────────────────

describe("FilterToolbar – interactions", () => {
  it("calls onSearchChange when typing in the search box", async () => {
    const user = userEvent.setup();
    const onSearchChange = vi.fn();
    render$({ onSearchChange });

    await user.type(screen.getByPlaceholderText(/search requests by title/i), "Oz");

    expect(onSearchChange).toHaveBeenCalled();
  });

  it("calls onFilterChange with ('status', value) when status select changes", async () => {
    const user = userEvent.setup();
    const onFilterChange = vi.fn();
    render$({ onFilterChange });

    await user.selectOptions(screen.getByTestId("select-Status"), "pending");

    expect(onFilterChange).toHaveBeenCalledWith("status", "pending");
  });

  it("calls onFilterChange with ('type', value) when type select changes", async () => {
    const user = userEvent.setup();
    const onFilterChange = vi.fn();
    render$({ onFilterChange });

    await user.selectOptions(screen.getByTestId("select-Request Type"), "movie");

    expect(onFilterChange).toHaveBeenCalledWith("type", "movie");
  });

  it("calls onFilterChange with ('user', value) when user select changes", async () => {
    const user = userEvent.setup();
    const onFilterChange = vi.fn();
    render$({ onFilterChange, uniqueUsers: ["all", "Alice", "Bob"] });

    await user.selectOptions(screen.getByTestId("select-Requested By"), "Alice");

    expect(onFilterChange).toHaveBeenCalledWith("user", "Alice");
  });

  it("clicking Clear Filters resets all: calls onSearchChange('') and resets all filters", async () => {
    const user = userEvent.setup();
    const onSearchChange = vi.fn();
    const onFilterChange = vi.fn();
    render$({
      searchQuery: "test",
      onSearchChange,
      onFilterChange,
      filters: { status: "pending", type: "movie", user: "Alice" },
    });

    await user.click(screen.getByText(/clear filters/i));

    expect(onSearchChange).toHaveBeenCalledWith("");
    expect(onFilterChange).toHaveBeenCalledWith("status", "all");
    expect(onFilterChange).toHaveBeenCalledWith("type", "all");
    expect(onFilterChange).toHaveBeenCalledWith("user", "all");
  });

  it("clicking Clear Filters calls onSearchChange('') when only search is active", async () => {
    const user = userEvent.setup();
    const onSearchChange = vi.fn();
    const onFilterChange = vi.fn();
    render$({
      searchQuery: "Inception",
      onSearchChange,
      onFilterChange,
    });

    await user.click(screen.getByText(/clear filters/i));

    expect(onSearchChange).toHaveBeenCalledWith("");
  });

  it("clicking Clear Filters resets status filter when only status is active", async () => {
    const user = userEvent.setup();
    const onFilterChange = vi.fn();
    render$({
      filters: { ...defaultFilters, status: "approved" },
      onFilterChange,
    });

    await user.click(screen.getByText(/clear filters/i));

    expect(onFilterChange).toHaveBeenCalledWith("status", "all");
  });
});
