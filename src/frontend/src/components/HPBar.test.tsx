import { render, screen } from "@testing-library/react";
import HPBar from "./HPBar";

test("renders hp bar with correct percentage", () => {
  render(<HPBar label="Alice" hp={75} maxHp={100} />);
  expect(screen.getByText("Alice")).toBeInTheDocument();
  expect(screen.getByText("75")).toBeInTheDocument();
  const bar = screen.getByRole("progressbar");
  expect(bar).toHaveStyle("width: 75%");
});

test("renders red when hp is low", () => {
  render(<HPBar label="Bob" hp={15} maxHp={100} />);
  const bar = screen.getByRole("progressbar");
  expect(bar).toHaveStyle("background-color: #e53e3e");
});
