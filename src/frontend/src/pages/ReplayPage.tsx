import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import type { RoundSnapshot } from "../types/game";

const API = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export default function ReplayPage() {
  const { matchId } = useParams<{ matchId: string }>();
  const [rounds, setRounds] = useState<RoundSnapshot[]>([]);
  const [frame, setFrame] = useState(0);

  useEffect(() => {
    if (!matchId) return;
    fetch(`${API}/api/replay/${matchId}`)
      .then((r) => r.json())
      .then((d) => setRounds(d.rounds ?? []));
  }, [matchId]);

  const current = rounds[frame];

  return (
    <div style={{ maxWidth: 600, margin: "40px auto", fontFamily: "sans-serif" }}>
      <h1>對戰回放</h1>
      <Link to="/">← 回首頁</Link>
      {rounds.length === 0 ? (
        <p>載入中...</p>
      ) : (
        <>
          <div style={{ margin: "16px 0" }}>
            <input
              type="range"
              min={0}
              max={rounds.length - 1}
              value={frame}
              onChange={(e) => setFrame(Number(e.target.value))}
              style={{ width: "100%" }}
            />
            <p>
              回合 {current.round_number} / {rounds.length}
            </p>
          </div>
          {current && (
            <div
              style={{
                background: "#1a202c",
                color: "#e2e8f0",
                padding: 16,
                borderRadius: 8,
              }}
            >
              <p>
                <strong>攻擊者：</strong>
                {current.attacker ?? "NPC"}
              </p>
              <p>
                <strong>攻擊內容：</strong>
                {current.display_text}
              </p>
              <p>
                <strong>傷害：</strong>
                {current.damage}
              </p>
              <p>
                <strong>裁判短評：</strong>
                {current.referee_comment}
              </p>
              <p>
                <strong>HP 快照：</strong>
                {JSON.stringify(current.hp_snapshot)}
              </p>
            </div>
          )}
        </>
      )}
    </div>
  );
}
