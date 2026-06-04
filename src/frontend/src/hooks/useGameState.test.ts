import { renderHook, act } from "@testing-library/react";
import { useGameState } from "./useGameState";

test("handles system message and updates hp", () => {
  const { result } = renderHook(() => useGameState("alice"));
  act(() => {
    result.current.handleMessage({
      type: "system",
      message: "遊戲開始",
      hp_status: { alice: 100, bob: 100 },
      current_turn: "alice",
    });
  });
  expect(result.current.hp).toEqual({ alice: 100, bob: 100 });
  expect(result.current.isMyTurn).toBe(true);
});

test("handles attack message and updates hp", () => {
  const { result } = renderHook(() => useGameState("alice"));
  act(() => {
    result.current.handleMessage({
      type: "attack",
      sender: "bob",
      display_text: "你好遜！",
      damage: 25,
      referee_comment: "猛",
      hp_status: { alice: 75, bob: 100 },
      current_turn: "alice",
    });
  });
  expect(result.current.hp.alice).toBe(75);
  expect(result.current.chatLog[0].damage).toBe(25);
});

test("handles game_over", () => {
  const { result } = renderHook(() => useGameState("alice"));
  act(() => {
    result.current.handleMessage({ type: "game_over", message: "結束", winner: "bob" });
  });
  expect(result.current.gameOver).toBe("bob");
});
