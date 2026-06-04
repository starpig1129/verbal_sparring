import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import LeaderboardPage from "./LeaderboardPage";

global.fetch = vi.fn();

test("renders leaderboard entries", async () => {
  (global.fetch as any).mockResolvedValueOnce({
    ok: true,
    json: async () => ({
      entries: [
        { rank: 1, username: "topgun", total_damage: 500, wins: 10, losses: 2 },
        { rank: 2, username: "player2", total_damage: 300, wins: 6, losses: 4 },
      ],
    }),
  });
  render(<MemoryRouter><LeaderboardPage /></MemoryRouter>);
  await waitFor(() => {
    expect(screen.getByText("topgun")).toBeInTheDocument();
    expect(screen.getByText("500")).toBeInTheDocument();
  });
});
