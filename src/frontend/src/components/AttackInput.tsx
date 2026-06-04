import { useState, useRef } from "react";
import type { AttackPayload } from "../types/game";

type Props = { onSend: (p: AttackPayload) => void; disabled: boolean };

export default function AttackInput({ onSend, disabled }: Props) {
  const [text, setText] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);

  function handleSend() {
    if (!text.trim()) return;
    onSend({ text });
    setText("");
  }

  function handleImage(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => onSend({ text, image: reader.result as string });
    reader.readAsDataURL(file);
  }

  return (
    <div style={{ display: "flex", gap: 8, padding: 8, background: "#2d3748" }}>
      <input
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && !disabled && handleSend()}
        placeholder="輸入你的攻擊..."
        disabled={disabled}
        style={{ flex: 1, padding: "6px 10px", borderRadius: 4 }}
      />
      <button onClick={() => fileRef.current?.click()} disabled={disabled}>📷</button>
      <input ref={fileRef} type="file" accept="image/*" style={{ display: "none" }} onChange={handleImage} />
      <button onClick={handleSend} disabled={disabled || !text.trim()}>出招！</button>
    </div>
  );
}
