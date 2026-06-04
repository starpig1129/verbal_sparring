import { BrowserRouter, Routes, Route } from "react-router-dom";
import HomePage from "./pages/HomePage";
import BattlePage from "./pages/BattlePage";
import LeaderboardPage from "./pages/LeaderboardPage";
import ReplayPage from "./pages/ReplayPage";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/battle/:matchId" element={<BattlePage />} />
        <Route path="/leaderboard" element={<LeaderboardPage />} />
        <Route path="/replay/:matchId" element={<ReplayPage />} />
      </Routes>
    </BrowserRouter>
  );
}
