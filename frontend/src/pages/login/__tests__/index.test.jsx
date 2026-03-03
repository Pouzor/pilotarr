import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";

// Mock AuthContext
const mockLogin = vi.fn();
const mockUseAuth = vi.fn();
vi.mock("../../../contexts/AuthContext", () => ({
  useAuth: () => mockUseAuth(),
}));

// Mock AppIcon so lucide-react doesn't need a full DOM environment
vi.mock("../../../components/AppIcon", () => ({
  default: ({ name }) => <span data-testid={`icon-${name}`} />,
}));

import Login from "../index";

const renderLogin = () =>
  render(
    <MemoryRouter>
      <Login />
    </MemoryRouter>,
  );

beforeEach(() => {
  vi.clearAllMocks();
  // Default: not initializing, not logged in
  mockUseAuth.mockReturnValue({ initializing: false, user: null, login: mockLogin });
});

describe("Login page – rendering", () => {
  it("renders the sign-in form", () => {
    renderLogin();
    expect(screen.getByRole("heading", { name: /pilotarr/i })).toBeInTheDocument();
    expect(screen.getByPlaceholderText("Your login")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("••••••••")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /sign in/i })).toBeInTheDocument();
  });

  it("returns null while initializing", () => {
    mockUseAuth.mockReturnValue({ initializing: true, user: null, login: mockLogin });
    const { container } = renderLogin();
    expect(container.firstChild).toBeNull();
  });

  it("renders no error by default", () => {
    renderLogin();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });
});

describe("Login page – validation", () => {
  it("shows error when username is empty", async () => {
    const user = userEvent.setup();
    renderLogin();

    await user.click(screen.getByRole("button", { name: /sign in/i }));

    expect(screen.getByText("Username is required")).toBeInTheDocument();
    expect(mockLogin).not.toHaveBeenCalled();
  });

  it("shows error when password is empty", async () => {
    const user = userEvent.setup();
    renderLogin();

    await user.type(screen.getByPlaceholderText("Your login"), "alice");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    expect(screen.getByText("Password is required")).toBeInTheDocument();
    expect(mockLogin).not.toHaveBeenCalled();
  });

  it("shows error when username is too short", async () => {
    const user = userEvent.setup();
    renderLogin();

    await user.type(screen.getByPlaceholderText("Your login"), "ab");
    await user.type(screen.getByPlaceholderText("••••••••"), "password");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    expect(screen.getByText("Username must be at least 5 characters")).toBeInTheDocument();
    expect(mockLogin).not.toHaveBeenCalled();
  });

  it("shows error when password is too short", async () => {
    const user = userEvent.setup();
    renderLogin();

    await user.type(screen.getByPlaceholderText("Your login"), "alice");
    await user.type(screen.getByPlaceholderText("••••••••"), "abc");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    expect(screen.getByText("Password must be at least 5 characters")).toBeInTheDocument();
    expect(mockLogin).not.toHaveBeenCalled();
  });

  it("shows error when username contains spaces", async () => {
    const user = userEvent.setup();
    renderLogin();

    await user.type(screen.getByPlaceholderText("Your login"), "ali ce");
    await user.type(screen.getByPlaceholderText("••••••••"), "password");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    expect(screen.getByText("Username must not contain spaces")).toBeInTheDocument();
    expect(mockLogin).not.toHaveBeenCalled();
  });

  it("shows error when password contains spaces", async () => {
    const user = userEvent.setup();
    renderLogin();

    await user.type(screen.getByPlaceholderText("Your login"), "alice");
    await user.type(screen.getByPlaceholderText("••••••••"), "pass word");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    expect(screen.getByText("Password must not contain spaces")).toBeInTheDocument();
    expect(mockLogin).not.toHaveBeenCalled();
  });

  it("clears field error when user starts typing", async () => {
    const user = userEvent.setup();
    renderLogin();

    await user.click(screen.getByRole("button", { name: /sign in/i }));
    expect(screen.getByText("Username is required")).toBeInTheDocument();

    await user.type(screen.getByPlaceholderText("Your login"), "a");
    expect(screen.queryByText("Username is required")).not.toBeInTheDocument();
  });
});

describe("Login page – form interaction", () => {
  it("calls login with typed username and password", async () => {
    const user = userEvent.setup();
    mockLogin.mockResolvedValue({ ok: true });
    renderLogin();

    await user.type(screen.getByPlaceholderText("Your login"), "alice");
    await user.type(screen.getByPlaceholderText("••••••••"), "mypassword");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    expect(mockLogin).toHaveBeenCalledWith("alice", "mypassword");
  });

  it("shows error message on failed login", async () => {
    const user = userEvent.setup();
    mockLogin.mockResolvedValue({ ok: false, error: "Invalid credentials" });
    renderLogin();

    await user.type(screen.getByPlaceholderText("Your login"), "baduser");
    await user.type(screen.getByPlaceholderText("••••••••"), "wrongpass");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => expect(screen.getByText("Invalid credentials")).toBeInTheDocument());
  });

  it("toggles password visibility", async () => {
    const user = userEvent.setup();
    renderLogin();

    const passwordInput = screen.getByPlaceholderText("••••••••");
    expect(passwordInput).toHaveAttribute("type", "password");

    await user.click(screen.getByRole("button", { name: /show password/i }));
    expect(passwordInput).toHaveAttribute("type", "text");

    await user.click(screen.getByRole("button", { name: /hide password/i }));
    expect(passwordInput).toHaveAttribute("type", "password");
  });
});
