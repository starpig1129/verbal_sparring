import { useState } from "react";
import { useNavigate } from "react-router-dom";

const API = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export default function HomePage() {
  const [tab, setTab] = useState<"login" | "register">("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [token, setToken] = useState(localStorage.getItem("token") ?? "");
  const [myUsername, setMyUsername] = useState(localStorage.getItem("username") ?? "");
  const [opponent, setOpponent] = useState("npc");
  const navigate = useNavigate();

  async function handleAuth() {
    setError("");
    const endpoint = tab === "login" ? "/api/auth/login" : "/api/auth/register";
    const resp = await fetch(`${API}${endpoint}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    const data = await resp.json();
    if (!resp.ok) {
      setError(
        tab === "login"
          ? "登入失敗：" + (data.detail ?? "")
          : "註冊失敗：" + (data.detail ?? "")
      );
      return;
    }
    localStorage.setItem("token", data.access_token);
    localStorage.setItem("username", data.username);
    setToken(data.access_token);
    setMyUsername(data.username);
  }

  async function handleStartMatch() {
    const resp = await fetch(`${API}/api/matches`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ opponent }),
    });
    const data = await resp.json();
    if (resp.ok) {
      navigate(`/battle/${data.match_id}`, { state: { token, myUsername } });
    } else {
      setError(data.detail ?? "建立對局失敗");
    }
  }

  if (!token) {
    return (
      <div style={{ maxWidth: 400, margin: "80px auto", fontFamily: "sans-serif" }}>
        <h1>唇槍舌戰</h1>
        <div>
          <button aria-label="登入頁籤" onClick={() => setTab("login")}>登入</button>
          <button aria-label="註冊頁籤" onClick={() => setTab("register")}>註冊</button>
        </div>
        <input
          placeholder="用戶名"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
        />
        <input
          type="password"
          placeholder="密碼"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        <button aria-label={tab === "login" ? "登入" : "註冊"} onClick={handleAuth}>確認</button>
        {error && <p style={{ color: "red" }}>{error}</p>}
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 400, margin: "80px auto", fontFamily: "sans-serif" }}>
      <h1>歡迎，{myUsername}！</h1>
      <div>
        <label>對手：</label>
        <select value={opponent} onChange={(e) => setOpponent(e.target.value)}>
          <option value="npc">AI NPC</option>
        </select>
        <input
          placeholder="或輸入對手用戶名"
          onChange={(e) => setOpponent(e.target.value || "npc")}
        />
      </div>
      <button onClick={handleStartMatch}>開始對戰</button>
      <br />
      <a href="/leaderboard">排行榜</a>
      {error && <p style={{ color: "red" }}>{error}</p>}
    </div>
  );
}
