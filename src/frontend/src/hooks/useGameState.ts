// src/frontend/src/hooks/useGameState.ts
import { useState, useCallback, useRef } from 'react'
import type { ChatEntry, HPMap, ServerMessage } from '../types/game'

export function useGameState(myPlayerId: string) {
  const [hp, setHp] = useState<HPMap>({})
  const [currentTurn, setCurrentTurn] = useState('')
  const [chatLog, setChatLog] = useState<ChatEntry[]>([])
  const [gameOver, setGameOver] = useState<string | null>(null)
  const [lastDamageEvent, setLastDamageEvent] = useState<{ damage: number; id: number } | null>(null)
  const [challengeDeclinedMessage, setChallengeDeclinedMessage] = useState<string | null>(null)
  const idCounter = useRef(0)

  function nextId() {
    return ++idCounter.current
  }

  const addOptimisticEntry = useCallback((text: string) => {
    setChatLog(prev => [...prev, {
      id: nextId(), kind: 'attack', sender: myPlayerId,
      displayText: text, damage: 0, isNpc: false, isPending: true,
    }])
    setCurrentTurn('')  // lock input immediately; server will restore on attack/npc_attack message
  }, [myPlayerId])

  const handleMessage = useCallback((msg: ServerMessage) => {
    if (msg.type === 'system') {
      setHp(msg.hp_status)
      setCurrentTurn(msg.current_turn)
      setChatLog(prev => [...prev, { id: nextId(), kind: 'system', displayText: msg.message }])
    } else if (msg.type === 'attack') {
      setHp(msg.hp_status)
      setCurrentTurn(msg.current_turn)
      if (msg.sender === myPlayerId) {
        // Replace the optimistic pending entry with the confirmed entry + referee
        setChatLog(prev => {
          const withoutPending = prev.filter(
            e => !(e.kind === 'attack' && e.isPending && e.sender === myPlayerId)
          )
          return [...withoutPending,
            { id: nextId(), kind: 'attack', sender: msg.sender, displayText: msg.original_text, damage: msg.damage, isNpc: false },
            { id: nextId(), kind: 'referee', displayText: `${msg.display_text}　—　${msg.referee_comment}` },
          ]
        })
      } else {
        setLastDamageEvent({ damage: msg.damage, id: nextId() })
        setChatLog(prev => {
          const withoutPending = prev.filter(
            e => !(e.kind === 'attack' && e.isPending && e.sender === msg.sender)
          )
          return [...withoutPending,
            { id: nextId(), kind: 'attack', sender: msg.sender, displayText: msg.original_text, damage: msg.damage, isNpc: false },
            { id: nextId(), kind: 'referee', displayText: `${msg.display_text}　—　${msg.referee_comment}` },
          ]
        })
      }
    } else if (msg.type === 'npc_typing') {
      // NPC words arrived before referee scores — show pending bubble
      setChatLog(prev => [...prev,
        { id: nextId(), kind: 'attack', sender: 'NPC', displayText: msg.npc_text, damage: 0, isNpc: true, isPending: true },
      ])
    } else if (msg.type === 'npc_attack') {
      setHp(msg.hp_status)
      setCurrentTurn(msg.current_turn)
      setLastDamageEvent({ damage: msg.damage, id: nextId() })
      // Replace pending NPC bubble (from npc_typing) with final scored result
      setChatLog(prev => {
        const withoutPending = prev.filter(
          e => !(e.kind === 'attack' && e.isPending && e.sender === 'NPC')
        )
        return [...withoutPending,
          { id: nextId(), kind: 'attack', sender: 'NPC', displayText: msg.npc_text, damage: msg.damage, isNpc: true },
          { id: nextId(), kind: 'referee', displayText: `${msg.display_text}　—　${msg.referee_comment}` },
        ]
      })
    } else if (msg.type === 'game_over') {
      setGameOver(msg.winner)
      setChatLog(prev => [...prev, { id: nextId(), kind: 'system', displayText: msg.message }])
    } else if (msg.type === 'error') {
      setChatLog(prev => [...prev, { id: nextId(), kind: 'system', displayText: `【系統錯誤】${msg.message}` }])
    } else if (msg.type === 'challenge_declined') {
      setChallengeDeclinedMessage(msg.message)
    } else if (msg.type === 'player_typing') {
      if (msg.sender !== myPlayerId) {
        setChatLog(prev => {
          const exists = prev.some(e => e.kind === 'attack' && e.isPending && e.sender === msg.sender)
          if (exists) return prev
          return [...prev, {
            id: nextId(), kind: 'attack', sender: msg.sender,
            displayText: msg.text, damage: 0, isNpc: false, isPending: true,
          }]
        })
      }
    }
  }, [myPlayerId])

  return {
    hp, currentTurn,
    isMyTurn: currentTurn === myPlayerId,
    chatLog, gameOver, lastDamageEvent,
    challengeDeclinedMessage,
    handleMessage, addOptimisticEntry,
  }
}
