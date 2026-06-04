import { useParams, useLocation, useNavigate } from "react-router-dom";
import { useGameState } from "../hooks/useGameState";
import { useWebSocket } from "../hooks/useWebSocket";
import HPBar from "../components/HPBar";
import ChatLog from "../components/ChatLog";
import AttackInput from "../components/AttackInput";

export default function BattlePage() {
  const { matchId } = useParams<{ matchId: string }>();
  const location = useLocation();
  const navigate = useNavigate();
  const token: string = location.state?.token ?? localStorage.getItem("token") ?? "";
  const myUsername: string =
    location.state?.myUsername ?? localStorage.getItem("username") ?? "Player";

  const { hp, isMyTurn, chatLog, gameOver, handleMessage } = useGameState(myUsername);
  const { sendAttack } = useWebSocket(matchId!, myUsername, token, handleMessage);

  const myHp = hp[myUsername] ?? 100;
  const opponentEntries = Object.entries(hp).filter(([k]) => k !== myUsername);
  const [opponentName, opponentHp] = opponentEntries[0] ?? ["對手", 100];

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "100vh",
        background: "#171923",
        color: "#e2e8f0",
        fontFamily: "sans-serif",
      }}
    >
      <div style={{ padding: "12px 16px", background: "#2d3748" }}>
        <HPBar label={opponentName} hp={opponentHp as number} />
      </div>

      <ChatLog entries={chatLog} />

      <div style={{ padding: "12px 16px", background: "#2d3748" }}>
        <HPBar label={myUsername} hp={myHp} />
        <div
          style={{
            fontSize: 12,
            color: isMyTurn ? "#68d391" : "#fc8181",
            marginTop: 4,
          }}
        >
          {isMyTurn ? "輪到你出招！" : "等待對手..."}
        </div>
      </div>

      {gameOver ? (
        <div style={{ padding: 16, textAlign: "center" }}>
          <p>{gameOver === myUsername ? "你贏了！" : "你輸了..."}</p>
          <button onClick={() => navigate("/")}>回首頁</button>
        </div>
      ) : (
        <AttackInput onSend={sendAttack} disabled={!isMyTurn} />
      )}
    </div>
  );
}
