import { useEffect, useRef } from "react";
import type { ChatEntry } from "../hooks/useGameState";

type Props = { entries: ChatEntry[] };

export default function ChatLog({ entries }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [entries]);

  return (
    <div style={{ flex: 1, overflowY: "auto", padding: "8px", background: "#1a202c", color: "#e2e8f0" }}>
      {entries.map((e) => (
        <div key={e.id} style={{ marginBottom: 6 }}>
          <strong>{e.sender}：</strong>
          {e.displayText}
          {e.damage != null && (
            <span style={{ marginLeft: 8 }}>
              <span style={{ color: "#fc8181" }}>-{e.damage}</span>
              {e.refereeComment && (
                <span style={{ marginLeft: 4 }}>{e.refereeComment}</span>
              )}
            </span>
          )}
        </div>
      ))}
      <div ref={bottomRef} />
    </div>
  );
}
