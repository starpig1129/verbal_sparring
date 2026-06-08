// src/frontend/src/hooks/useGameState.test.ts
import { renderHook, act } from '@testing-library/react'
import { useGameState } from './useGameState'

test('system message updates hp and currentTurn', () => {
  const { result } = renderHook(() => useGameState('alice'))
  act(() => {
    result.current.handleMessage({
      type: 'system', message: '遊戲開始',
      hp_status: { alice: 100, bob: 100 }, current_turn: 'alice',
    })
  })
  expect(result.current.hp).toEqual({ alice: 100, bob: 100 })
  expect(result.current.isMyTurn).toBe(true)
})

test('attack message adds attack + referee entries to chatLog', () => {
  const { result } = renderHook(() => useGameState('alice'))
  act(() => {
    result.current.handleMessage({
      type: 'attack', sender: 'bob', original_text: '你好遜！', display_text: '你好遜！',
      damage: 25, referee_comment: '猛',
      hp_status: { alice: 75, bob: 100 }, current_turn: 'alice',
    })
  })
  expect(result.current.hp.alice).toBe(75)
  const attackEntry = result.current.chatLog.find(e => e.kind === 'attack')
  expect(attackEntry).toBeDefined()
  if (attackEntry?.kind === 'attack') expect(attackEntry.damage).toBe(25)
  const refereeEntry = result.current.chatLog.find(e => e.kind === 'referee')
  expect(refereeEntry).toBeDefined()
})

test('attack message sets lastDamageEvent', () => {
  const { result } = renderHook(() => useGameState('alice'))
  act(() => {
    result.current.handleMessage({
      type: 'attack', sender: 'bob', original_text: 'test', display_text: 'test',
      damage: 18, referee_comment: 'ok',
      hp_status: { alice: 82, bob: 100 }, current_turn: 'alice',
    })
  })
  expect(result.current.lastDamageEvent?.damage).toBe(18)
})

test('game_over sets gameOver winner', () => {
  const { result } = renderHook(() => useGameState('alice'))
  act(() => {
    result.current.handleMessage({ type: 'game_over', message: '結束', winner: 'bob' })
  })
  expect(result.current.gameOver).toBe('bob')
})
