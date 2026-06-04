import { useState, useCallback } from "react";
import { ServerMessage, HPMap } from "../types/game";

export type ChatEntry = {
  id: number;
  sender: string;
  displayText: string;
  damage?: number;
  refereeComment?: string;
};

export function useGameState(myPlayerId: string) {
  const [hp, setHp] = useState<HPMap>({});
  const [currentTurn, setCurrentTurn] = useState("");
  const [chatLog, setChatLog] = useState<ChatEntry[]>([]);
  const [gameOver, setGameOver] = useState<string | null>(null);

  const handleMessage = useCallback(
    (msg: ServerMessage) => {
      if (msg.type === "system") {
        setHp(msg.hp_status);
        setCurrentTurn(msg.current_turn);
        setChatLog((prev) => [
          ...prev,
          { id: Date.now(), sender: "系統", displayText: msg.message },
        ]);
      } else if (msg.type === "attack") {
        setHp(msg.hp_status);
        setCurrentTurn(msg.current_turn);
        setChatLog((prev) => [
          ...prev,
          {
            id: Date.now(),
            sender: msg.sender,
            displayText: msg.display_text,
            damage: msg.damage,
            refereeComment: msg.referee_comment,
          },
        ]);
      } else if (msg.type === "npc_attack") {
        setHp(msg.hp_status);
        setChatLog((prev) => [
          ...prev,
          {
            id: Date.now(),
            sender: "NPC",
            displayText: msg.display_text,
            damage: msg.damage,
            refereeComment: msg.referee_comment,
          },
        ]);
      } else if (msg.type === "game_over") {
        setGameOver(msg.winner);
        setChatLog((prev) => [
          ...prev,
          { id: Date.now(), sender: "系統", displayText: msg.message },
        ]);
      }
    },
    [myPlayerId]
  );

  const isMyTurn = currentTurn === myPlayerId;

  return { hp, currentTurn, isMyTurn, chatLog, gameOver, handleMessage };
}
