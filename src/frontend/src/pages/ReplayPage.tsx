// src/frontend/src/pages/ReplayPage.tsx
import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import HPBar from '../components/HPBar'
import type { RoundSnapshot } from '../types/game'

const API = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export default function ReplayPage() {
  const { matchId } = useParams<{ matchId: string }>()
  const [rounds, setRounds] = useState<RoundSnapshot[]>([])
  const [frame, setFrame] = useState(0)

  useEffect(() => {
    if (!matchId) return
    fetch(`${API}/api/replay/${matchId}`)
      .then(r => r.json())
      .then(d => setRounds(d.rounds ?? []))
  }, [matchId])

  const current = rounds[frame]
  const hpEntries = current ? Object.entries(current.hp_snapshot) : []

  return (
    <div className="flex-1 bg-ink px-4 py-6 max-w-xl mx-auto w-full">
      {/* Title */}
      <div className="flex items-baseline gap-3 border-b-[3px] border-vermillion pb-2 mb-5">
        <span className="font-display text-[18px] text-white tracking-[3px]">回放</span>
        {rounds.length > 0 && (
          <span className="font-mono text-aged text-[10px] tracking-[2px]">
            ROUND <span className="text-vermillion font-display text-[14px]">{frame + 1}</span>/{rounds.length}
          </span>
        )}
      </div>

      {rounds.length === 0 ? (
        <div className="text-bark font-mono text-[9px] tracking-[2px] text-center py-8">載入中...</div>
      ) : (
        <>
          {/* HP Snapshot */}
          <div className="mb-5 space-y-3">
            {hpEntries.map(([player, hp]) => (
              <HPBar key={player} label={player} hp={Number(hp)} />
            ))}
          </div>

          {/* Round card */}
          {current && (
            <div className="bg-parchment border border-[#4a4028] p-4 mb-5">
              <div className="font-mono text-vermillion text-[9px] tracking-[3px] mb-2 uppercase">
                {current.attacker ?? 'NPC'} 出招
              </div>
              {current.original_text && current.original_text !== current.display_text && (
                <div className="font-body italic text-bark text-[10px] mb-1 line-through">
                  {current.original_text}
                </div>
              )}
              <div className="font-body italic text-[#d4c5aa] text-[12px] mb-3 leading-relaxed">
                「{current.display_text}」
              </div>
              <div className="flex items-center gap-3 pt-2 border-t border-bamboo">
                <span className="font-mono text-bark text-[9px]">
                  傷害 <span className="text-fire font-display text-[14px]">-{current.damage}</span>
                </span>
                <span className="font-mono text-bark text-[8px] tracking-[1px] italic">{current.referee_comment}</span>
              </div>
            </div>
          )}

          {/* Scrubber */}
          <div className="flex items-center gap-3">
            <button
              onClick={() => setFrame(f => Math.max(0, f - 1))}
              disabled={frame === 0}
              className="w-8 h-8 bg-vermillion flex items-center justify-center font-display text-white text-[10px] disabled:opacity-40 disabled:cursor-not-allowed hover:bg-fire flex-shrink-0"
            >
              ◀
            </button>
            <div className="relative flex-1 h-1 bg-[#1a1610]">
              <div
                className="absolute left-0 top-0 h-full bg-vermillion"
                style={{ width: `${((frame) / Math.max(1, rounds.length - 1)) * 100}%` }}
              />
              <input
                type="range"
                min={0}
                max={rounds.length - 1}
                value={frame}
                onChange={e => setFrame(Number(e.target.value))}
                className="absolute inset-0 w-full opacity-0 cursor-pointer"
              />
              <div
                className="absolute top-1/2 w-3 h-3 bg-fire rounded-full -translate-y-1/2 -translate-x-1/2 pointer-events-none"
                style={{ left: `${((frame) / Math.max(1, rounds.length - 1)) * 100}%` }}
              />
            </div>
            <button
              onClick={() => setFrame(f => Math.min(rounds.length - 1, f + 1))}
              disabled={frame >= rounds.length - 1}
              className="w-8 h-8 bg-vermillion flex items-center justify-center font-display text-white text-[10px] disabled:opacity-40 disabled:cursor-not-allowed hover:bg-fire flex-shrink-0"
            >
              ▶
            </button>
          </div>
        </>
      )}

      <div className="text-center mt-6">
        <Link to="/" className="font-mono text-bark text-[9px] tracking-[2px] hover:text-aged">← 回首頁</Link>
      </div>
    </div>
  )
}
