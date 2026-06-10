// src/frontend/src/pages/BattlePage.tsx
import { useCallback, useEffect, useState } from 'react'
import { useParams, useLocation, useNavigate } from 'react-router-dom'
import { motion, useAnimation } from 'framer-motion'
import { useGameState } from '../hooks/useGameState'
import { useWebSocket } from '../hooks/useWebSocket'
import { useAuthContext } from '../contexts/AuthContext'
import { sound } from '../utils/sound'
import HPBar from '../components/HPBar'
import ChatLog from '../components/ChatLog'
import AttackInput from '../components/AttackInput'
import TurnIndicator from '../components/TurnIndicator'
import DamageNumber from '../components/DamageNumber'
import GameOverModal from '../components/GameOverModal'
import type { MatchRecord } from '../types/game'

const API = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export default function BattlePage() {
  const { matchId } = useParams<{ matchId: string }>()
  const location = useLocation()
  const navigate = useNavigate()
  const { token: ctxToken, username: ctxUsername } = useAuthContext()
  const token: string = location.state?.token ?? ctxToken
  const myUsername: string = location.state?.myUsername ?? ctxUsername

  const { hp, isMyTurn, chatLog, gameOver, lastDamageEvent, handleMessage, addOptimisticEntry, challengeDeclinedMessage, reset } = useGameState(myUsername)
  const { sendAttack, connectionState } = useWebSocket(matchId!, myUsername, token, handleMessage)

  // Rematches navigate to a fresh match URL — wipe the previous battle state.
  useEffect(() => {
    reset()
  }, [matchId, reset])

  const handleSend = useCallback((payload: { text: string; image?: string }) => {
    if (payload.text) addOptimisticEntry(payload.text)
    sendAttack(payload)
    sound.playSendMessage()
  }, [addOptimisticEntry, sendAttack])
  const shakeControls = useAnimation()

  const myHp = hp[myUsername] ?? 100
  const opponentEntries = Object.entries(hp).filter(([k]) => k !== myUsername)
  const [opponentName, opponentHp] = opponentEntries[0] ?? ['對手', 100]
  const roundCount = chatLog.filter(e => e.kind === 'attack').length

  // NPC rematch: the finished match stays finished — create a fresh one and
  // jump to it. PvP rematches go through the lobby challenge flow.
  const handlePlayAgain = useCallback(async () => {
    if (String(opponentName) !== 'NPC') {
      navigate('/')
      return
    }
    try {
      const resp = await fetch(`${API}/api/matches`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ opponent: 'npc' }),
      })
      if (!resp.ok) throw new Error('create match failed')
      const data = await resp.json()
      navigate(`/battle/${data.match_id}`, { state: { token, myUsername } })
    } catch {
      navigate('/')
    }
  }, [opponentName, token, myUsername, navigate])

  // Screen shake on big damage
  useEffect(() => {
    if (!lastDamageEvent || lastDamageEvent.damage < 20) return
    shakeControls.start({ x: [0, -6, 6, -4, 4, 0], transition: { duration: 0.4 } })
  }, [lastDamageEvent, shakeControls])

  // Write match result to localStorage on game_over
  useEffect(() => {
    if (!gameOver || !matchId) return
    const prev: MatchRecord[] = JSON.parse(localStorage.getItem('matchHistory') ?? '[]')
    const myDamage = chatLog
      .filter((e): e is Extract<typeof e, { kind: 'attack' }> => e.kind === 'attack' && !e.isNpc)
      .reduce((sum, e) => sum + e.damage, 0)
    const record: MatchRecord = {
      matchId, opponent: String(opponentName),
      result: gameOver === myUsername ? 'win' : 'loss',
      totalDamage: myDamage, roundCount,
      timestamp: Date.now(),
    }
    localStorage.setItem('matchHistory', JSON.stringify([record, ...prev].slice(0, 50)))
  }, [gameOver])

  return (
    <motion.div animate={shakeControls} className="flex flex-col h-screen bg-ink text-white overflow-hidden">
      {/* Top bar */}
      <div className="bg-[#0f0e0b] border-b-2 border-[#4a3f28] flex justify-between items-center px-4 py-3 flex-shrink-0">
        <span className="font-display text-base md:text-lg text-white tracking-[2px]">唇槍<span className="text-vermillion">舌戰</span></span>
        <span className="font-mono text-[#a88a6d] text-xs tracking-[3px] font-semibold">ROUND <span className="font-display text-white text-base font-bold">{String(Math.ceil(roundCount / 2)).padStart(2, '0')}</span></span>
        <button onClick={() => navigate('/')} className="font-mono text-[#e2d6be] text-xs border border-[#4a3f28] hover:border-vermillion hover:text-white bg-[#120f0a] px-3.5 py-1.5 tracking-[2px] rounded transition-all duration-150 transform active:scale-95">回主頁</button>
      </div>

      {/* HP section */}
      <div className="flex items-stretch border-b border-[#1a1610] flex-shrink-0">
        <div className="flex-1 px-4 py-3 border-r border-[#1a1610]">
          <HPBar label={String(opponentName)} hp={Number(opponentHp)} />
        </div>
        <div className="px-3 flex flex-col items-center justify-center bg-[#080805]">
          <span className="font-body italic text-[#1a1610] text-sm">對</span>
          <div className="w-[1px] h-4 bg-gradient-to-b from-transparent via-bark to-transparent my-1" />
          <div className="w-[5px] h-[5px] bg-vermillion rounded-full opacity-60" />
        </div>
        <div className="flex-1 px-4 py-3 border-l border-[#1a1610] text-right">
          <HPBar label={myUsername} hp={myHp} />
        </div>
      </div>

      {/* Connection status banner */}
      {connectionState === 'reconnecting' && (
        <div className="bg-vermillion/90 text-white text-xs font-mono text-center py-1.5 tracking-[2px] flex-shrink-0 animate-pulse">
          連線中斷，重新連線中…
        </div>
      )}
      {connectionState === 'closed' && (
        <div className="bg-[#4a3f28] text-[#e2d6be] text-xs font-mono text-center py-1.5 tracking-[2px] flex-shrink-0">
          連線已失效，請重新登入
        </div>
      )}

      {/* Chat log */}
      <ChatLog entries={chatLog} myUsername={myUsername} />

      {/* Turn indicator */}
      <TurnIndicator isMyTurn={isMyTurn} />

      {/* Input */}
      <AttackInput onSend={handleSend} disabled={!isMyTurn} />

      {/* Damage number */}
      <DamageNumber damageEvent={lastDamageEvent} />

      {/* Game over modal */}
      {gameOver && (
        <GameOverModal
          winner={gameOver}
          myUsername={myUsername}
          matchId={matchId!}
          onPlayAgain={handlePlayAgain}
        />
      )}

      {/* Challenge Declined Modal */}
      {challengeDeclinedMessage && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm">
          <div className="w-full max-w-sm p-6 bg-[#0f0e0a] border-2 border-vermillion shadow-[0_0_30px_rgba(204,51,0,0.5)] rounded-2xl text-center flex flex-col items-center gap-4">
            <h2 className="font-display text-lg text-white font-bold tracking-[2px]">挑戰被拒絕</h2>
            <p className="text-xs text-[#a88a6d] font-body leading-relaxed">{challengeDeclinedMessage}</p>
            <button
              onClick={() => navigate('/')}
              className="px-6 py-2 bg-vermillion hover:bg-red-600 text-white rounded font-bold transition-all text-xs"
            >
              返回大廳
            </button>
          </div>
        </div>
      )}
    </motion.div>
  )
}
