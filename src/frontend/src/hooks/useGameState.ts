// src/frontend/src/hooks/useGameState.ts
import { useState, useCallback, useRef } from 'react'
import type { ChatEntry, HPMap, ServerMessage } from '../types/game'
import { sound } from '../utils/sound'

export function useGameState(myPlayerId: string) {
  const [hp, setHp] = useState<HPMap>({})
  const [currentTurn, setCurrentTurn] = useState('')
  const [chatLog, setChatLog] = useState<ChatEntry[]>([])
  const [gameOver, setGameOver] = useState<string | null>(null)
  const [lastDamageEvent, setLastDamageEvent] = useState<{ damage: number; id: number; isCrit?: boolean } | null>(null)
  const [challengeDeclinedMessage, setChallengeDeclinedMessage] = useState<string | null>(null)
  const [toast, setToast] = useState<{ id: number; message: string } | null>(null)
  // Persona name for the NPC opponent ("NPC" stays the internal key)
  const [npcName, setNpcName] = useState('NPC')
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
      if (msg.message.includes('進入競技場！')) {
        sound.playJoinArena()
      }
    } else if (msg.type === 'attack') {
      setHp(msg.hp_status)
      setCurrentTurn(msg.current_turn)
      if (msg.sender === myPlayerId) {
        sound.playDealDamage()
        // Replace the optimistic pending entry with the confirmed entry + referee
        setChatLog(prev => {
          const withoutPending = prev.filter(
            e => !(e.kind === 'attack' && e.isPending && e.sender === myPlayerId)
          )
          return [...withoutPending,
            { id: nextId(), kind: 'attack', sender: msg.sender, displayText: msg.original_text, damage: msg.damage, isNpc: false, isCrit: msg.is_crit, combo: msg.combo },
            { id: nextId(), kind: 'referee', displayText: `${msg.display_text}　—　${msg.referee_comment}` },
          ]
        })
      } else {
        sound.playReceiveDamage()
        setLastDamageEvent({ damage: msg.damage, id: nextId(), isCrit: msg.is_crit })
        setChatLog(prev => {
          const withoutPending = prev.filter(
            e => !(e.kind === 'attack' && e.isPending && e.sender === msg.sender)
          )
          return [...withoutPending,
            { id: nextId(), kind: 'attack', sender: msg.sender, displayText: msg.original_text, damage: msg.damage, isNpc: false, isCrit: msg.is_crit, combo: msg.combo },
            { id: nextId(), kind: 'referee', displayText: `${msg.display_text}　—　${msg.referee_comment}` },
          ]
        })
      }
    } else if (msg.type === 'npc_typing') {
      sound.playReceiveMessage()
      // NPC words arrived before referee scores — show pending bubble
      setChatLog(prev => [...prev,
        { id: nextId(), kind: 'attack', sender: 'NPC', displayText: msg.npc_text, damage: 0, isNpc: true, isPending: true },
      ])
    } else if (msg.type === 'npc_attack') {
      setHp(msg.hp_status)
      setCurrentTurn(msg.current_turn)
      setLastDamageEvent({ damage: msg.damage, id: nextId(), isCrit: msg.is_crit })
      sound.playReceiveDamage()
      // Replace pending NPC bubble (from npc_typing) with final scored result
      setChatLog(prev => {
        const withoutPending = prev.filter(
          e => !(e.kind === 'attack' && e.isPending && e.sender === 'NPC')
        )
        return [...withoutPending,
          { id: nextId(), kind: 'attack', sender: 'NPC', displayText: msg.npc_text, damage: msg.damage, isNpc: true, isCrit: msg.is_crit, combo: msg.combo },
          { id: nextId(), kind: 'referee', displayText: `${msg.display_text}　—　${msg.referee_comment}` },
        ]
      })
    } else if (msg.type === 'game_over') {
      setGameOver(msg.winner)
      setChatLog(prev => [...prev, { id: nextId(), kind: 'system', displayText: msg.message }])
      if (msg.winner === myPlayerId) {
        sound.playVictory()
      }
    } else if (msg.type === 'error') {
      // Transient — shown as a toast so it doesn't pollute the battle log
      setToast({ id: nextId(), message: msg.message })
    } else if (msg.type === 'turn_error') {
      setToast({ id: nextId(), message: msg.message })
      // Resync with the server's authoritative state and drop the optimistic
      // bubble for the rejected attack
      setHp(msg.hp_status)
      setCurrentTurn(msg.current_turn)
      setChatLog(prev => prev.filter(
        e => !(e.kind === 'attack' && e.isPending && e.sender === myPlayerId)
      ))
    } else if (msg.type === 'turn_timeout') {
      // Server skipped an idle player's turn — record it and resync
      setHp(msg.hp_status)
      setCurrentTurn(msg.current_turn)
      setChatLog(prev => [...prev, { id: nextId(), kind: 'system', displayText: msg.message }])
    } else if (msg.type === 'challenge_declined') {
      setChallengeDeclinedMessage(msg.message)
    } else if (msg.type === 'player_typing') {
      if (msg.sender !== myPlayerId) {
        sound.playReceiveMessage()
        setChatLog(prev => {
          const exists = prev.some(e => e.kind === 'attack' && e.isPending && e.sender === msg.sender)
          if (exists) return prev
          return [...prev, {
            id: nextId(), kind: 'attack', sender: msg.sender,
            displayText: msg.text, damage: 0, isNpc: false, isPending: true,
          }]
        })
      }
    } else if (msg.type === 'history') {
      if (msg.npc_name) setNpcName(msg.npc_name)
      const restoredChatLog: ChatEntry[] = []
      msg.rounds.forEach(r => {
        const isNpc = r.attacker === 'NPC'
        restoredChatLog.push(
          { id: nextId(), kind: 'attack', sender: r.attacker || 'NPC', displayText: r.original_text || '', damage: r.damage, isNpc },
          { id: nextId(), kind: 'referee', displayText: `${r.display_text}　—　${r.referee_comment}` }
        )
      })
      setChatLog(restoredChatLog)
      if (msg.rounds.length > 0) {
        const latestRound = msg.rounds[msg.rounds.length - 1]
        setHp(latestRound.hp_snapshot)
      }
    }
  }, [myPlayerId])

  // Clear all battle state when switching to a new match (e.g. rematch).
  const reset = useCallback(() => {
    setHp({})
    setCurrentTurn('')
    setChatLog([])
    setGameOver(null)
    setLastDamageEvent(null)
    setChallengeDeclinedMessage(null)
    setToast(null)
    setNpcName('NPC')
  }, [])

  const clearToast = useCallback(() => setToast(null), [])

  return {
    hp, currentTurn,
    isMyTurn: currentTurn === myPlayerId,
    chatLog, gameOver, lastDamageEvent,
    challengeDeclinedMessage,
    toast, clearToast, npcName,
    handleMessage, addOptimisticEntry, reset,
  }
}
