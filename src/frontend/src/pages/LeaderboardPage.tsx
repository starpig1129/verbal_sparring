// src/frontend/src/pages/LeaderboardPage.tsx
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import type { LeaderboardEntry } from '../types/game'

const API = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'
const CHINESE_RANKS = ['一', '二', '三']

export default function LeaderboardPage() {
  const [entries, setEntries] = useState<LeaderboardEntry[]>([])

  useEffect(() => {
    fetch(`${API}/api/leaderboard`)
      .then(r => r.json())
      .then(d => setEntries(d.entries ?? []))
  }, [])

  return (
    <div className="flex-1 bg-gradient-to-b from-[#120f0a] via-[#0a0905] to-[#050403] px-4 py-8 max-w-2xl mx-auto w-full min-h-[calc(100vh-60px)]">
      <div className="bg-[#0f0e0a]/90 border border-[#4a3f28] shadow-[0_8px_32px_rgba(0,0,0,0.6)] rounded-2xl p-6 backdrop-blur-md">
        {/* Title */}
        <div className="flex items-baseline gap-2 border-b-[3px] border-vermillion pb-3.5 mb-5">
          <span className="font-display text-2xl text-white tracking-[3px] font-bold">武林</span>
          <span className="font-display text-2xl text-vermillion tracking-[3px] font-bold">排行</span>
          <span className="font-mono text-[#a88a6d] text-xs font-semibold tracking-[2px] ml-auto">TOP 50</span>
        </div>
        {/* Header row */}
        <div className="flex gap-3 text-[#e2d6be] font-mono text-xs font-bold px-2 pb-2 mb-2 border-b border-[#3a3020]">
          <span className="w-8">名次</span>
          <span className="flex-1">俠士</span>
          <span className="w-20 text-right">傷害</span>
          <span className="w-12 text-right">勝</span>
          <span className="w-12 text-right">敗</span>
        </div>
        {/* Entries */}
        <div className="space-y-1.5">
          {entries.map((e) => {
            const rankDisplay = e.rank <= 3 ? CHINESE_RANKS[e.rank - 1] : String(e.rank)
            const borderColor = e.rank === 1 ? '#cc3300' : e.rank === 2 ? '#f59e0b' : e.rank <= 3 ? '#a88a6d' : '#2a2018'
            const bg = e.rank === 1 ? 'bg-[#220d00]/40' : e.rank === 2 ? 'bg-[#1a1308]/40' : e.rank === 3 ? 'bg-[#12110c]/40' : 'bg-[#0a0905]/40'
            return (
              <div
                key={e.rank}
                className={`flex gap-3 items-center px-3 py-2.5 rounded-lg border border-[#4a3f28]/30 hover:border-vermillion/30 transition-all ${bg}`}
                style={{ borderLeft: `4px solid ${borderColor}` }}
              >
                <span className={`w-8 font-display text-base font-bold ${e.rank <= 3 ? 'text-vermillion' : 'text-[#a88a6d]'}`}>{rankDisplay}</span>
                <span className="flex-1 font-display text-sm md:text-base tracking-wider text-white font-bold">{e.username.toUpperCase()}</span>
                <span className="w-20 text-right font-mono text-xs md:text-sm text-vermillion font-bold">{(e.total_damage).toLocaleString()}</span>
                <span className="w-12 text-right font-mono text-xs md:text-sm text-emerald-400 font-bold">{e.wins}</span>
                <span className="w-12 text-right font-mono text-xs md:text-sm text-[#a88a6d]">{e.losses}</span>
              </div>
            )
          })}
        </div>
        {entries.length === 0 && (
          <div className="text-[#a88a6d] font-mono text-xs tracking-[2px] text-center py-12">載入中...</div>
        )}
        <div className="text-[#a88a6d]/60 font-body italic text-xs tracking-[3px] text-center border-t border-[#3a3020] pt-5 mt-6">
          ⸺ 以筆傷人，武林稱霸 ⸺
        </div>
      </div>
      <div className="text-center mt-6 w-full flex justify-center">
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
