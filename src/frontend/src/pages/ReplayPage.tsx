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
    <div className="flex-1 bg-gradient-to-b from-[#120f0a] via-[#0a0905] to-[#050403] px-4 py-8 max-w-xl mx-auto w-full min-h-[calc(100vh-60px)]">
      <div className="bg-[#0f0e0a]/90 border border-[#4a3f28] shadow-[0_8px_32px_rgba(0,0,0,0.6)] rounded-2xl p-6 backdrop-blur-md">
        {/* Title */}
        <div className="flex items-baseline gap-3 border-b-[3px] border-vermillion pb-3.5 mb-5">
          <span className="font-display text-2xl text-white tracking-[3px] font-bold">對戰回放</span>
          {rounds.length > 0 && (
            <span className="font-mono text-[#a88a6d] text-xs font-semibold tracking-[2px]">
              ROUND <span className="text-vermillion font-display text-base font-bold">{frame + 1}</span>/{rounds.length}
            </span>
          )}
        </div>

        {rounds.length === 0 ? (
          <div className="text-[#a88a6d] font-mono text-xs tracking-[2px] text-center py-12">載入中...</div>
        ) : (
          <>
            {/* HP Snapshot */}
            <div className="mb-6 space-y-4">
              {hpEntries.map(([player, hp]) => (
                <HPBar key={player} label={player} hp={Number(hp)} />
              ))}
            </div>

            {/* Round card */}
            {current && (
              <div className="bg-[#12100b] border border-[#4a3f28] p-5 mb-6 rounded-xl shadow-sm">
                <div className="font-mono text-vermillion text-xs tracking-[3px] mb-2 uppercase font-bold">
                  {current.attacker ?? 'NPC'} 出招
                </div>
                {current.original_text && current.original_text !== current.display_text && (
                  <div className="font-body text-[#a88a6d]/70 text-xs mb-1.5 line-through">
                    {current.original_text}
                  </div>
                )}
                <div className="font-body text-[#fff0d4] text-sm md:text-base mb-4 leading-relaxed">
                  「{current.display_text}」
                </div>
                <div className="flex items-center gap-4 pt-3.5 border-t border-[#4a3f28]/40">
                  <span className="font-mono text-[#e2d6be] text-xs font-bold">
                    傷害 <span className="text-fire font-display text-base font-bold ml-1">-{current.damage}</span>
                  </span>
                  <span className="font-mono text-vermillion font-bold text-xs md:text-sm border-l-2 border-vermillion/30 pl-2">{current.referee_comment}</span>
                </div>
              </div>
            )}

            {/* Scrubber */}
            <div className="flex items-center gap-3.5">
              <button
                onClick={() => setFrame(f => Math.max(0, f - 1))}
                disabled={frame === 0}
                className="w-10 h-10 bg-vermillion flex items-center justify-center font-display text-white text-xs disabled:opacity-35 disabled:cursor-not-allowed hover:bg-fire flex-shrink-0 rounded transition-all transform active:scale-90"
              >
                ◀
              </button>
              <div className="relative flex-1 h-1 bg-[#1a1610] rounded">
                <div
                  className="absolute left-0 top-0 h-full bg-vermillion rounded"
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
                  className="absolute top-1/2 w-4.5 h-4.5 bg-fire rounded-full -translate-y-1/2 -translate-x-1/2 pointer-events-none shadow-[0_0_8px_rgba(255,68,0,0.5)]"
                  style={{ left: `${((frame) / Math.max(1, rounds.length - 1)) * 100}%` }}
                />
              </div>
              <button
                onClick={() => setFrame(f => Math.min(rounds.length - 1, f + 1))}
                disabled={frame >= rounds.length - 1}
                className="w-10 h-10 bg-vermillion flex items-center justify-center font-display text-white text-xs disabled:opacity-35 disabled:cursor-not-allowed hover:bg-fire flex-shrink-0 rounded transition-all transform active:scale-90"
              >
                ▶
              </button>
            </div>
          </>
        )}
      </div>

      <div className="text-center mt-8 w-full flex justify-center">
        <Link
          to="/"
          className="inline-flex items-center justify-center gap-2 font-mono text-xs text-[#a88a6d] hover:text-white border border-[#4a3f28] hover:border-[#886655] bg-[#14100b] hover:bg-[#1a1610] px-6 py-3 rounded-xl shadow-sm tracking-[2px] transition-all duration-100 transform active:scale-95 w-full max-w-xs"
        >
          ← 返回大廳
        </Link>
      </div>
    </div>
  )
}
