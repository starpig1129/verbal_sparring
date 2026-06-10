import { useRef, useEffect, useCallback, useState } from "react";
import { ServerMessage, AttackPayload } from "../types/game";

const WS_BASE = import.meta.env.VITE_WS_URL ?? "ws://localhost:8000";

// Cloudflare's proxy drops WebSocket connections idle for ~100s, so ping
// well inside that window.
const PING_INTERVAL_MS = 30_000;
const MAX_RECONNECT_DELAY_MS = 30_000;
const AUTH_FAILED_CODE = 4001;

export type ConnectionState = "connecting" | "open" | "reconnecting" | "closed";

export function useWebSocket(
  matchId: string,
  playerId: string,
  token: string,
  onMessage: (msg: ServerMessage) => void
) {
  const ws = useRef<WebSocket | null>(null);
  const [connectionState, setConnectionState] = useState<ConnectionState>("connecting");

  // Keep the latest handler without re-running the connection effect.
  const onMessageRef = useRef(onMessage);
  onMessageRef.current = onMessage;

  useEffect(() => {
    if (!matchId || !token) return;
    let disposed = false;
    let attempt = 0;
    let pingTimer: number | undefined;
    let reconnectTimer: number | undefined;

    const connect = () => {
      if (disposed) return;
      setConnectionState(attempt === 0 ? "connecting" : "reconnecting");
      const socket = new WebSocket(
        `${WS_BASE}/ws/battle/${matchId}/${playerId}?token=${token}`
      );
      ws.current = socket;

      socket.onopen = () => {
        attempt = 0;
        setConnectionState("open");
        pingTimer = window.setInterval(() => {
          if (socket.readyState === WebSocket.OPEN) socket.send("ping");
        }, PING_INTERVAL_MS);
      };

      socket.onmessage = (e) => {
        if (e.data === "pong") return;
        try {
          const msg: ServerMessage = JSON.parse(e.data);
          onMessageRef.current(msg);
        } catch {}
      };

      socket.onclose = (e) => {
        window.clearInterval(pingTimer);
        if (disposed) return;
        if (e.code === AUTH_FAILED_CODE) {
          setConnectionState("closed");
          return;
        }
        setConnectionState("reconnecting");
        const delay = Math.min(1000 * 2 ** attempt, MAX_RECONNECT_DELAY_MS);
        attempt += 1;
        reconnectTimer = window.setTimeout(connect, delay);
      };
    };

    connect();

    return () => {
      disposed = true;
      window.clearInterval(pingTimer);
      window.clearTimeout(reconnectTimer);
      ws.current?.close();
    };
  }, [matchId, playerId, token]);

  const sendAttack = useCallback((payload: AttackPayload) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify(payload));
    }
  }, []);

  return { sendAttack, connectionState };
}
