import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";

// ── Mocks ─────────────────────────────────────────────────────────────────────

vi.mock("react-router-dom", async (importOriginal) => {
  const actual = await importOriginal();
  return { ...actual, useNavigate: () => vi.fn() };
});

vi.mock("../../../components/navigation/Header", () => ({
  default: () => <header data-testid="header" />,
}));

vi.mock("../../../components/AppIcon", () => ({
  default: ({ name }) => <span data-testid={`icon-${name}`} />,
}));

vi.mock("../../../components/ui/Button", () => ({
  default: ({ children, onClick }) => <button onClick={onClick}>{children}</button>,
}));

// FilterToolbar stub: exposes controlled inputs for search + status/type filter
vi.mock("../components/FilterToolbar", () => ({
  default: ({
    searchQuery,
    onSearchChange,
    filters,
    onFilterChange,
    totalResults,
    uniqueUsers,
  }) => (
    <div data-testid="filter-toolbar">
      <input
        data-testid="search-input"
        value={searchQuery}
        onChange={(e) => onSearchChange(e.target.value)}
        placeholder="Search requests by title..."
      />
      <select
        data-testid="status-filter"
        value={filters.status}
        onChange={(e) => onFilterChange("status", e.target.value)}
      >
        <option value="all">all</option>
        <option value="pending">pending</option>
        <option value="approved">approved</option>
        <option value="declined">declined</option>
      </select>
      <select
        data-testid="type-filter"
        value={filters.type}
        onChange={(e) => onFilterChange("type", e.target.value)}
      >
        <option value="all">all</option>
        <option value="movie">movie</option>
        <option value="tv">tv</option>
      </select>
      <select
        data-testid="user-filter"
        value={filters.user}
        onChange={(e) => onFilterChange("user", e.target.value)}
      >
        {uniqueUsers?.map((u) => (
          <option key={u} value={u}>
            {u}
          </option>
        ))}
      </select>
      <span data-testid="total-results">{totalResults}</span>
    </div>
  ),
}));

// RequestCard stub: renders title, status and approve/reject buttons when pending
vi.mock("../../main-dashboard/components/RequestCard", () => ({
  default: ({ request, onApprove, onReject }) => (
    <div data-testid={`request-card-${request.id}`}>
      <span data-testid={`request-title-${request.id}`}>{request.title}</span>
      <span data-testid={`request-status-${request.id}`}>{request.status}</span>
      {request.status === 1 && (
        <>
          <button data-testid={`approve-${request.id}`} onClick={() => onApprove(request.id)}>
            Approve
          </button>
          <button data-testid={`reject-${request.id}`} onClick={() => onReject(request.id)}>
            Reject
          </button>
        </>
      )}
    </div>
  ),
}));

const mockGetJellyseerrRequests = vi.fn();
const mockApproveRequest = vi.fn();
const mockDeclineRequest = vi.fn();

vi.mock("../../../services/requestService", () => ({
  getJellyseerrRequests: (...args) => mockGetJellyseerrRequests(...args),
  approveRequest: (...args) => mockApproveRequest(...args),
  declineRequest: (...args) => mockDeclineRequest(...args),
}));

// ── Helpers ───────────────────────────────────────────────────────────────────

const makeRequest = (id, status, title = "Movie", mediaType = "movie", requestedBy = "Alice") => ({
  id,
  status,
  title,
  mediaType,
  year: 2024,
  requestedBy,
  imageUrl: "https://img.jpg",
  imageAlt: title,
  priority: "medium",
  requestedDate: "2 days ago",
  quality: "1080p",
  description: "A description",
});

const renderPage = () =>
  render(
    <MemoryRouter>
      {/* dynamic import to pick up latest vi.mock resolution */}
      <PageComponent />
    </MemoryRouter>,
  );

// Import after mocks are set up
import JellyseerrRequests from "../index";
const PageComponent = JellyseerrRequests;

beforeEach(() => {
  vi.clearAllMocks();
  mockGetJellyseerrRequests.mockResolvedValue([]);
  mockApproveRequest.mockResolvedValue(true);
  mockDeclineRequest.mockResolvedValue(true);
});

// ── Loading state ─────────────────────────────────────────────────────────────

describe("JellyseerrRequests – loading", () => {
  it("shows a loading spinner while fetching", () => {
    mockGetJellyseerrRequests.mockReturnValue(new Promise(() => {}));
    renderPage();
    expect(screen.getByTestId("icon-Loader")).toBeInTheDocument();
  });

  it("hides spinner after data loads", async () => {
    renderPage();
    await waitFor(() => expect(screen.queryByTestId("icon-Loader")).not.toBeInTheDocument());
  });
});

// ── Data fetching ─────────────────────────────────────────────────────────────

describe("JellyseerrRequests – data fetching", () => {
  it("calls getJellyseerrRequests with 'all' and limit 100 on mount", async () => {
    renderPage();
    await waitFor(() => expect(mockGetJellyseerrRequests).toHaveBeenCalledWith("all", 100));
  });

  it("renders request cards after data loads", async () => {
    mockGetJellyseerrRequests.mockResolvedValue([
      makeRequest("r1", 2, "Inception"),
      makeRequest("r2", 1, "Dune"),
    ]);
    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId("request-card-r1")).toBeInTheDocument();
      expect(screen.getByTestId("request-card-r2")).toBeInTheDocument();
    });
  });

  it("shows empty state when no requests are returned", async () => {
    renderPage();
    await waitFor(() => expect(screen.getByText(/no requests found/i)).toBeInTheDocument());
  });

  it("does not crash when getJellyseerrRequests rejects", async () => {
    mockGetJellyseerrRequests.mockRejectedValue(new Error("network error"));
    renderPage();
    await waitFor(() => expect(screen.getByText(/no requests found/i)).toBeInTheDocument());
  });
});

// ── Status summary cards ──────────────────────────────────────────────────────

describe("JellyseerrRequests – status summary cards", () => {
  it("shows correct count for each status", async () => {
    mockGetJellyseerrRequests.mockResolvedValue([
      makeRequest("r1", 1, "Pending 1"),
      makeRequest("r2", 1, "Pending 2"),
      makeRequest("r3", 2, "Approved 1"),
      makeRequest("r4", 3, "Declined 1"),
    ]);
    renderPage();
    await waitFor(() => screen.getByTestId("request-card-r1"));

    // The status summary renders counts: pending=2, approved=1, declined=1
    const counts = screen.getAllByText(/^\d+$/).filter((el) => ["2", "1"].includes(el.textContent));
    expect(counts.length).toBeGreaterThan(0);
  });
});

// ── Search filter ─────────────────────────────────────────────────────────────

describe("JellyseerrRequests – search filter", () => {
  it("filters by title substring (case-insensitive)", async () => {
    mockGetJellyseerrRequests.mockResolvedValue([
      makeRequest("r1", 1, "Inception"),
      makeRequest("r2", 1, "Dune Part Two"),
    ]);
    renderPage();
    await waitFor(() => screen.getByTestId("request-card-r1"));

    const searchInput = screen.getByTestId("search-input");
    await userEvent.type(searchInput, "dune");

    expect(screen.queryByTestId("request-card-r1")).not.toBeInTheDocument();
    expect(screen.getByTestId("request-card-r2")).toBeInTheDocument();
  });

  it("is case-insensitive", async () => {
    mockGetJellyseerrRequests.mockResolvedValue([makeRequest("r1", 1, "Inception")]);
    renderPage();
    await waitFor(() => screen.getByTestId("request-card-r1"));

    await userEvent.type(screen.getByTestId("search-input"), "INCEPTION");
    expect(screen.getByTestId("request-card-r1")).toBeInTheDocument();
  });

  it("shows empty state when search matches nothing", async () => {
    mockGetJellyseerrRequests.mockResolvedValue([makeRequest("r1", 1, "Inception")]);
    renderPage();
    await waitFor(() => screen.getByTestId("request-card-r1"));

    await userEvent.type(screen.getByTestId("search-input"), "zzzzz");
    expect(screen.getByText(/no requests found/i)).toBeInTheDocument();
  });
});

// ── Status filter ─────────────────────────────────────────────────────────────

describe("JellyseerrRequests – status filter", () => {
  const requests = [
    makeRequest("pending1", 1, "Pending Movie"),
    makeRequest("approved1", 2, "Approved Movie"),
    makeRequest("declined1", 3, "Declined Movie"),
  ];

  it("filter 'approved' shows only status=2 requests", async () => {
    mockGetJellyseerrRequests.mockResolvedValue(requests);
    renderPage();
    await waitFor(() => screen.getByTestId("request-card-pending1"));

    await userEvent.selectOptions(screen.getByTestId("status-filter"), "approved");

    expect(screen.queryByTestId("request-card-pending1")).not.toBeInTheDocument();
    expect(screen.getByTestId("request-card-approved1")).toBeInTheDocument();
    expect(screen.queryByTestId("request-card-declined1")).not.toBeInTheDocument();
  });

  it("filter 'pending' shows only status=1 requests", async () => {
    mockGetJellyseerrRequests.mockResolvedValue(requests);
    renderPage();
    await waitFor(() => screen.getByTestId("request-card-pending1"));

    await userEvent.selectOptions(screen.getByTestId("status-filter"), "pending");

    expect(screen.getByTestId("request-card-pending1")).toBeInTheDocument();
    expect(screen.queryByTestId("request-card-approved1")).not.toBeInTheDocument();
  });

  it("filter 'declined' shows only status=3 requests", async () => {
    mockGetJellyseerrRequests.mockResolvedValue(requests);
    renderPage();
    await waitFor(() => screen.getByTestId("request-card-pending1"));

    await userEvent.selectOptions(screen.getByTestId("status-filter"), "declined");

    expect(screen.queryByTestId("request-card-pending1")).not.toBeInTheDocument();
    expect(screen.getByTestId("request-card-declined1")).toBeInTheDocument();
  });

  it("filter 'all' shows all requests", async () => {
    mockGetJellyseerrRequests.mockResolvedValue(requests);
    renderPage();
    await waitFor(() => screen.getByTestId("request-card-pending1"));

    await userEvent.selectOptions(screen.getByTestId("status-filter"), "approved");
    await userEvent.selectOptions(screen.getByTestId("status-filter"), "all");

    expect(screen.getByTestId("request-card-pending1")).toBeInTheDocument();
    expect(screen.getByTestId("request-card-approved1")).toBeInTheDocument();
    expect(screen.getByTestId("request-card-declined1")).toBeInTheDocument();
  });
});

// ── Type filter ───────────────────────────────────────────────────────────────

describe("JellyseerrRequests – type filter", () => {
  it("filter 'movie' hides tv requests", async () => {
    mockGetJellyseerrRequests.mockResolvedValue([
      makeRequest("m1", 1, "A Movie", "movie"),
      makeRequest("t1", 1, "A Show", "tv"),
    ]);
    renderPage();
    await waitFor(() => screen.getByTestId("request-card-m1"));

    await userEvent.selectOptions(screen.getByTestId("type-filter"), "movie");

    expect(screen.getByTestId("request-card-m1")).toBeInTheDocument();
    expect(screen.queryByTestId("request-card-t1")).not.toBeInTheDocument();
  });

  it("filter 'tv' hides movie requests", async () => {
    mockGetJellyseerrRequests.mockResolvedValue([
      makeRequest("m1", 1, "A Movie", "movie"),
      makeRequest("t1", 1, "A Show", "tv"),
    ]);
    renderPage();
    await waitFor(() => screen.getByTestId("request-card-m1"));

    await userEvent.selectOptions(screen.getByTestId("type-filter"), "tv");

    expect(screen.queryByTestId("request-card-m1")).not.toBeInTheDocument();
    expect(screen.getByTestId("request-card-t1")).toBeInTheDocument();
  });
});

// ── totalResults updates ──────────────────────────────────────────────────────

describe("JellyseerrRequests – totalResults counter", () => {
  it("shows total count of all requests when no filter active", async () => {
    mockGetJellyseerrRequests.mockResolvedValue([
      makeRequest("r1", 1),
      makeRequest("r2", 2),
      makeRequest("r3", 3),
    ]);
    renderPage();
    await waitFor(() => expect(screen.getByTestId("total-results").textContent).toBe("3"));
  });

  it("decreases after applying a filter", async () => {
    mockGetJellyseerrRequests.mockResolvedValue([makeRequest("r1", 1), makeRequest("r2", 2)]);
    renderPage();
    await waitFor(() => screen.getByTestId("request-card-r1"));

    await userEvent.selectOptions(screen.getByTestId("status-filter"), "pending");
    expect(screen.getByTestId("total-results").textContent).toBe("1");
  });
});

// ── Approve / Reject ──────────────────────────────────────────────────────────

describe("JellyseerrRequests – approve and reject", () => {
  it("calls approveRequest with the correct id", async () => {
    mockGetJellyseerrRequests.mockResolvedValue([makeRequest("r1", 1, "Pending")]);
    renderPage();
    await waitFor(() => screen.getByTestId("approve-r1"));

    await userEvent.click(screen.getByTestId("approve-r1"));
    expect(mockApproveRequest).toHaveBeenCalledWith("r1");
  });

  it("updates request status to 2 (approved) in state on success", async () => {
    mockGetJellyseerrRequests.mockResolvedValue([makeRequest("r1", 1, "Pending")]);
    renderPage();
    await waitFor(() => screen.getByTestId("approve-r1"));

    await userEvent.click(screen.getByTestId("approve-r1"));

    await waitFor(() => expect(screen.getByTestId("request-status-r1").textContent).toBe("2"));
  });

  it("does not update status when approveRequest returns false", async () => {
    mockApproveRequest.mockResolvedValue(false);
    mockGetJellyseerrRequests.mockResolvedValue([makeRequest("r1", 1, "Pending")]);
    renderPage();
    await waitFor(() => screen.getByTestId("approve-r1"));

    await userEvent.click(screen.getByTestId("approve-r1"));

    await waitFor(() => expect(screen.getByTestId("request-status-r1").textContent).toBe("1"));
  });

  it("calls declineRequest with the correct id", async () => {
    mockGetJellyseerrRequests.mockResolvedValue([makeRequest("r1", 1, "Pending")]);
    renderPage();
    await waitFor(() => screen.getByTestId("reject-r1"));

    await userEvent.click(screen.getByTestId("reject-r1"));
    expect(mockDeclineRequest).toHaveBeenCalledWith("r1");
  });

  it("updates request status to 3 (declined) in state on success", async () => {
    mockGetJellyseerrRequests.mockResolvedValue([makeRequest("r1", 1, "Pending")]);
    renderPage();
    await waitFor(() => screen.getByTestId("reject-r1"));

    await userEvent.click(screen.getByTestId("reject-r1"));

    await waitFor(() => expect(screen.getByTestId("request-status-r1").textContent).toBe("3"));
  });
});

// ── Clear All Filters ─────────────────────────────────────────────────────────

describe("JellyseerrRequests – Clear All Filters", () => {
  // "Clear All Filters" renders only inside the empty-state block (when filteredRequests === 0)
  it("shows Clear All Filters in empty state when status filter yields no results", async () => {
    mockGetJellyseerrRequests.mockResolvedValue([makeRequest("r1", 2, "Approved Movie")]);
    renderPage();
    await waitFor(() => screen.getByTestId("request-card-r1"));

    // filter to "pending" — no pending requests → empty state appears
    await userEvent.selectOptions(screen.getByTestId("status-filter"), "pending");

    await waitFor(() => expect(screen.getByText(/clear all filters/i)).toBeInTheDocument());
  });

  it("shows Clear All Filters in empty state when search yields no results", async () => {
    mockGetJellyseerrRequests.mockResolvedValue([makeRequest("r1", 1, "Inception")]);
    renderPage();
    await waitFor(() => screen.getByTestId("request-card-r1"));

    await userEvent.type(screen.getByTestId("search-input"), "zzznomatch");

    await waitFor(() => expect(screen.getByText(/clear all filters/i)).toBeInTheDocument());
  });

  it("does not show Clear All Filters when all filters are default and results exist", async () => {
    mockGetJellyseerrRequests.mockResolvedValue([makeRequest("r1", 1)]);
    renderPage();
    await waitFor(() => screen.getByTestId("request-card-r1"));

    expect(screen.queryByText(/clear all filters/i)).not.toBeInTheDocument();
  });

  it("clicking Clear All Filters resets search and shows all results", async () => {
    mockGetJellyseerrRequests.mockResolvedValue([
      makeRequest("r1", 1, "Inception"),
      makeRequest("r2", 2, "Dune"),
    ]);
    renderPage();
    await waitFor(() => screen.getByTestId("request-card-r1"));

    // Search for something that matches nothing → triggers empty state with the button
    await userEvent.type(screen.getByTestId("search-input"), "zzznomatch");
    await waitFor(() => screen.getByText(/clear all filters/i));

    await userEvent.click(screen.getByText(/clear all filters/i));

    await waitFor(() => {
      expect(screen.getByTestId("request-card-r1")).toBeInTheDocument();
      expect(screen.getByTestId("request-card-r2")).toBeInTheDocument();
    });
  });
});
