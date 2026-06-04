import { render, screen } from "@testing-library/react";
import ChatLog from "./ChatLog";
import type { ChatEntry } from "../hooks/useGameState";

const entries: ChatEntry[] = [
  { id: 1, sender: "alice", displayText: "你好遜！", damage: 20, refereeComment: "猛" },
  { id: 2, sender: "系統", displayText: "遊戲開始" },
];

test("renders all chat entries", () => {
  render(<ChatLog entries={entries} />);
  expect(screen.getByText("你好遜！")).toBeInTheDocument();
  expect(screen.getByText("遊戲開始")).toBeInTheDocument();
});

test("shows damage amount", () => {
  render(<ChatLog entries={entries} />);
  expect(screen.getByText("-20")).toBeInTheDocument();
});
