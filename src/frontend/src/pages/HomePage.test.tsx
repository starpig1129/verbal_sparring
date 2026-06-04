import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import HomePage from "./HomePage";

global.fetch = vi.fn();

test("renders login and register tabs", () => {
  render(<MemoryRouter><HomePage /></MemoryRouter>);
  expect(screen.getByText("登入")).toBeInTheDocument();
  expect(screen.getByText("註冊")).toBeInTheDocument();
});

test("shows error on login failure", async () => {
  (global.fetch as any).mockResolvedValueOnce({
    ok: false,
    json: async () => ({ detail: "Invalid credentials" }),
  });
  render(<MemoryRouter><HomePage /></MemoryRouter>);
  fireEvent.change(screen.getByPlaceholderText("用戶名"), { target: { value: "alice" } });
  fireEvent.change(screen.getByPlaceholderText("密碼"), { target: { value: "wrong" } });
  fireEvent.click(screen.getByRole("button", { name: "登入" }));
  await waitFor(() => {
    expect(screen.getByText(/登入失敗/)).toBeInTheDocument();
  });
});
