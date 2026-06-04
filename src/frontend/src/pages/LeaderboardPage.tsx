import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import type { LeaderboardEntry } from "../types/game";

const API = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export default function LeaderboardPage() {
  const [entries, setEntries] = useState<LeaderboardEntry[]>([]);

  useEffect(() => {
    fetch(`${API}/api/leaderboard`)
      .then((r) => r.json())
      .then((d) => setEntries(d.entries ?? []));
  }, []);

  return (
    <div style={{ maxWidth: 600, margin: "40px auto", fontFamily: "sans-serif" }}>
      <h1>排行榜</h1>
      <Link to="/">← 回首頁</Link>
      <table style={{ width: "100%", marginTop: 16, borderCollapse: "collapse" }}>
        <thead>
          <tr>
            <th>#</th>
            <th>用戶名</th>
            <th>累計傷害</th>
            <th>勝</th>
            <th>敗</th>
          </tr>
        </thead>
        <tbody>
          {entries.map((e) => (
            <tr key={e.rank}>
              <td>{e.rank}</td>
              <td>{e.username}</td>
              <td>{e.total_damage}</td>
              <td>{e.wins}</td>
              <td>{e.losses}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
