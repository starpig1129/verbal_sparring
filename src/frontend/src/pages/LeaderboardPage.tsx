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
    <div className="flex-1 bg-ink px-4 py-6 max-w-2xl mx-auto w-full">
      {/* Title */}
      <div className="flex items-baseline gap-2 border-b-[3px] border-vermillion pb-2 mb-4">
        <span className="font-display text-[20px] text-white tracking-[3px]">武林</span>
        <span className="font-display text-[20px] text-vermillion tracking-[3px]">排行</span>
        <span className="font-mono text-bark text-[8px] tracking-[2px] ml-auto">TOP 50</span>
      </div>
      {/* Header row */}
      <div className="flex gap-2 text-bark font-mono text-[8px] tracking-[2px] px-1 pb-1 mb-1">
        <span className="w-6">位</span>
        <span className="flex-1">俠士</span>
        <span className="w-14 text-right">傷害</span>
        <span className="w-8 text-right">勝</span>
        <span className="w-8 text-right">敗</span>
      </div>
      {/* Entries */}
      {entries.map((e) => {
        const rankDisplay = e.rank <= 3 ? CHINESE_RANKS[e.rank - 1] : String(e.rank)
        const borderColor = e.rank === 1 ? '#cc3300' : e.rank === 2 ? '#662200' : e.rank <= 3 ? '#331100' : '#2a2018'
        const bg = e.rank === 1 ? 'bg-[#1a0d00]' : e.rank === 2 ? 'bg-[#0f0a05]' : ''
        return (
          <div
            key={e.rank}
            className={`flex gap-2 items-center px-1 py-[6px] mb-[2px] ${bg}`}
            style={{ borderLeft: `3px solid ${borderColor}` }}
          >
            <span className="w-6 font-display text-[14px] text-vermillion/70">{rankDisplay}</span>
            <span className="flex-1 font-display text-[13px] tracking-wider text-white">{e.username.toUpperCase()}</span>
            <span className="w-14 text-right font-mono text-[10px] text-vermillion/80">{e.total_damage}</span>
            <span className="w-8 text-right font-mono text-[10px] text-aged">{e.wins}</span>
            <span className="w-8 text-right font-mono text-[10px] text-bark">{e.losses}</span>
          </div>
        )
      })}
      {entries.length === 0 && (
        <div className="text-bark font-mono text-[9px] tracking-[2px] text-center py-8">載入中...</div>
      )}
      <div className="text-[#2a1a0a] font-body italic text-[8px] tracking-[3px] text-center border-t border-[#1a1610] pt-4 mt-6">
        ⸺ 以筆傷人，武林稱霸 ⸺
      </div>
      <div className="text-center mt-6 w-full flex justify-center">
        <Link
          to="/"
          className="inline-flex items-center justify-center gap-2 font-mono text-xs text-[#a88a6d] hover:text-white border border-[#4a3f28] hover:border-[#886655] bg-[#14100b] hover:bg-[#1a1610] px-6 py-2.5 rounded-xl shadow-sm tracking-[2px] transition-all duration-100 transform active:scale-95 w-full max-w-xs"
        >
          ← 返回大廳
        </Link>
      </div>
    </div>
  )
}
