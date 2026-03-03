import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

// Mock AppIcon so lucide-react doesn't need a full DOM environment
vi.mock("../../../../components/AppIcon", () => ({
  default: ({ name }) => <span data-testid={`icon-${name}`} />,
}));

// Mock AppImage
vi.mock("../../../../components/AppImage", () => ({
  default: ({ src, alt }) => <img src={src} alt={alt} />,
}));

// Mock Button to render a real clickable element
vi.mock("../../../../components/ui/Button", () => ({
  default: ({ children, onClick, variant }) => (
    <button data-variant={variant} onClick={onClick}>
      {children}
    </button>
  ),
}));

import RequestCard from "../RequestCard";

const baseRequest = {
  id: "req-001",
  title: "Inception",
  mediaType: "movie",
  year: 2010,
  requestedBy: "alice",
  requestedDate: "2025-01-10",
  status: 1, // PENDING
  imageUrl: "https://example.com/poster.jpg",
  imageAlt: "Inception poster",
  description: "A mind-bending thriller.",
  priority: "medium",
  quality: "HD-1080p",
};

const renderCard = (props = {}) => {
  const onApprove = vi.fn();
  const onReject = vi.fn();
  const { rerender } = render(
    <RequestCard
      request={{ ...baseRequest, ...props.request }}
      onApprove={props.onApprove ?? onApprove}
      onReject={props.onReject ?? onReject}
    />,
  );
  return { onApprove, onReject, rerender };
};

beforeEach(() => {
  vi.clearAllMocks();
});

// ── Rendering ─────────────────────────────────────────────────────────────────

describe("RequestCard – rendering", () => {
  it("displays the request title", () => {
    renderCard();
    expect(screen.getByText("Inception")).toBeInTheDocument();
  });

  it("displays the year", () => {
    renderCard();
    expect(screen.getByText("2010")).toBeInTheDocument();
  });

  it("displays the media type", () => {
    renderCard();
    expect(screen.getByText("movie")).toBeInTheDocument();
  });

  it("displays the requester name", () => {
    renderCard();
    expect(screen.getByText("alice")).toBeInTheDocument();
  });

  it("displays the requested date", () => {
    renderCard();
    expect(screen.getByText("2025-01-10")).toBeInTheDocument();
  });

  it("displays the description", () => {
    renderCard();
    expect(screen.getByText("A mind-bending thriller.")).toBeInTheDocument();
  });

  it("displays the quality", () => {
    renderCard();
    expect(screen.getByText(/HD-1080p/)).toBeInTheDocument();
  });

  it("displays the priority badge", () => {
    renderCard();
    expect(screen.getByText("medium")).toBeInTheDocument();
  });
});

// ── Media type icons ──────────────────────────────────────────────────────────

describe("RequestCard – media type icons", () => {
  it("renders Film icon for movie media type", () => {
    renderCard({ request: { mediaType: "movie" } });
    expect(screen.getByTestId("icon-Film")).toBeInTheDocument();
  });

  it("renders Tv icon for tv media type", () => {
    renderCard({ request: { mediaType: "tv" } });
    expect(screen.getByTestId("icon-Tv")).toBeInTheDocument();
  });
});

// ── Priority rendering ────────────────────────────────────────────────────────

describe("RequestCard – priority labels", () => {
  it("renders high priority label", () => {
    renderCard({ request: { priority: "high" } });
    expect(screen.getByText("high")).toBeInTheDocument();
  });

  it("renders medium priority label", () => {
    renderCard({ request: { priority: "medium" } });
    expect(screen.getByText("medium")).toBeInTheDocument();
  });

  it("renders low priority label", () => {
    renderCard({ request: { priority: "low" } });
    expect(screen.getByText("low")).toBeInTheDocument();
  });
});

// ── Pending status (status = 1) ───────────────────────────────────────────────

describe("RequestCard – pending state (status=1)", () => {
  it("shows Approve and Reject buttons", () => {
    renderCard({ request: { status: 1 } });
    expect(screen.getByText("Approve")).toBeInTheDocument();
    expect(screen.getByText("Reject")).toBeInTheDocument();
  });

  it("does not show Approved badge", () => {
    renderCard({ request: { status: 1 } });
    expect(screen.queryByText("Approved")).not.toBeInTheDocument();
  });

  it("does not show Declined badge", () => {
    renderCard({ request: { status: 1 } });
    expect(screen.queryByText("Declined")).not.toBeInTheDocument();
  });

  it("calls onApprove with request id when Approve is clicked", async () => {
    const user = userEvent.setup();
    const { onApprove } = renderCard({ request: { status: 1 } });

    await user.click(screen.getByText("Approve"));

    expect(onApprove).toHaveBeenCalledOnce();
    expect(onApprove).toHaveBeenCalledWith("req-001");
  });

  it("calls onReject with request id when Reject is clicked", async () => {
    const user = userEvent.setup();
    const { onReject } = renderCard({ request: { status: 1 } });

    await user.click(screen.getByText("Reject"));

    expect(onReject).toHaveBeenCalledOnce();
    expect(onReject).toHaveBeenCalledWith("req-001");
  });
});

// ── Approved status (status = 2) ──────────────────────────────────────────────

describe("RequestCard – approved state (status=2)", () => {
  it("shows Approved badge", () => {
    renderCard({ request: { status: 2 } });
    expect(screen.getByText("Approved")).toBeInTheDocument();
  });

  it("does not show Approve/Reject buttons", () => {
    renderCard({ request: { status: 2 } });
    expect(screen.queryByText("Approve")).not.toBeInTheDocument();
    expect(screen.queryByText("Reject")).not.toBeInTheDocument();
  });

  it("does not show Declined badge", () => {
    renderCard({ request: { status: 2 } });
    expect(screen.queryByText("Declined")).not.toBeInTheDocument();
  });

  it("shows CheckCircle icon", () => {
    renderCard({ request: { status: 2 } });
    expect(screen.getByTestId("icon-CheckCircle")).toBeInTheDocument();
  });
});

// ── Declined status (status = 3) ──────────────────────────────────────────────

describe("RequestCard – declined state (status=3)", () => {
  it("shows Declined badge", () => {
    renderCard({ request: { status: 3 } });
    expect(screen.getByText("Declined")).toBeInTheDocument();
  });

  it("does not show Approve/Reject buttons", () => {
    renderCard({ request: { status: 3 } });
    expect(screen.queryByText("Approve")).not.toBeInTheDocument();
    expect(screen.queryByText("Reject")).not.toBeInTheDocument();
  });

  it("does not show Approved badge", () => {
    renderCard({ request: { status: 3 } });
    expect(screen.queryByText("Approved")).not.toBeInTheDocument();
  });

  it("shows XCircle icon", () => {
    renderCard({ request: { status: 3 } });
    expect(screen.getByTestId("icon-XCircle")).toBeInTheDocument();
  });
});

// ── Unknown status (edge case) ────────────────────────────────────────────────

describe("RequestCard – unknown status (status=4)", () => {
  it("does not show Approve/Reject buttons", () => {
    renderCard({ request: { status: 4 } });
    expect(screen.queryByText("Approve")).not.toBeInTheDocument();
    expect(screen.queryByText("Reject")).not.toBeInTheDocument();
  });

  it("does not show Approved badge", () => {
    renderCard({ request: { status: 4 } });
    expect(screen.queryByText("Approved")).not.toBeInTheDocument();
  });

  it("does not show Declined badge", () => {
    renderCard({ request: { status: 4 } });
    expect(screen.queryByText("Declined")).not.toBeInTheDocument();
  });
});

// ── Optional fields ───────────────────────────────────────────────────────────

describe("RequestCard – optional fields", () => {
  it("does not crash when year is missing", () => {
    renderCard({ request: { year: undefined } });
    expect(screen.getByText("Inception")).toBeInTheDocument();
  });

  it("does not crash when description is missing", () => {
    renderCard({ request: { description: undefined } });
    expect(screen.getByText("Inception")).toBeInTheDocument();
  });

  it("does not crash when requestedDate is missing", () => {
    renderCard({ request: { requestedDate: undefined } });
    expect(screen.getByText("Inception")).toBeInTheDocument();
  });

  it("does not crash when priority is missing", () => {
    renderCard({ request: { priority: undefined } });
    expect(screen.getByText("Inception")).toBeInTheDocument();
  });

  it("does not crash when quality is missing", () => {
    renderCard({ request: { quality: undefined } });
    expect(screen.getByText("Inception")).toBeInTheDocument();
  });

  it("does not render year when missing", () => {
    renderCard({ request: { year: undefined } });
    expect(screen.queryByText("2010")).not.toBeInTheDocument();
  });

  it("does not render description when missing", () => {
    renderCard({ request: { description: undefined } });
    expect(screen.queryByText("A mind-bending thriller.")).not.toBeInTheDocument();
  });

  it("does not render requestedDate when missing", () => {
    renderCard({ request: { requestedDate: undefined } });
    expect(screen.queryByText("2025-01-10")).not.toBeInTheDocument();
  });

  it("does not render quality when missing", () => {
    renderCard({ request: { quality: undefined } });
    expect(screen.queryByText(/HD-1080p/)).not.toBeInTheDocument();
  });
});
