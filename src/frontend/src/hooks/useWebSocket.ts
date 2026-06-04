import { useRef, useEffect, useCallback } from "react";
import { ServerMessage, AttackPayload } from "../types/game";

const WS_BASE = import.meta.env.VITE_WS_URL ?? "ws://localhost:8000";

export function useWebSocket(
  matchId: string,
  playerId: string,
  token: string,
  onMessage: (msg: ServerMessage) => void
) {
  const ws = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!matchId || !token) return;
    const url = `${WS_BASE}/ws/battle/${matchId}/${playerId}?token=${token}`;
    ws.current = new WebSocket(url);

    ws.current.onmessage = (e) => {
      try {
        const msg: ServerMessage = JSON.parse(e.data);
        onMessage(msg);
      } catch {}
    };

    return () => {
      ws.current?.close();
    };
  }, [matchId, playerId, token]);

  const sendAttack = useCallback((payload: AttackPayload) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify(payload));
    }
  }, []);

  return { sendAttack };
}
