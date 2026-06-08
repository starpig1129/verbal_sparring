// src/frontend/src/pages/HistoryPage.tsx
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import type { MatchRecord } from '../types/game'

type Filter = 'all' | 'win' | 'loss'

export default function HistoryPage() {
  const [history, setHistory] = useState<MatchRecord[]>([])
  const [filter, setFilter] = useState<Filter>('all')
  const [page, setPage] = useState(0)
  const PAGE_SIZE = 20

  useEffect(() => {
    try {
      const stored: MatchRecord[] = JSON.parse(localStorage.getItem('matchHistory') ?? '[]')
      setHistory(stored)
    } catch {
      setHistory([])
    }
  }, [])

  const filtered = history.filter(r => filter === 'all' || r.result === filter)
  const paged = filtered.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE)
  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE))

  const tabs: { key: Filter; label: string }[] = [
    { key: 'all', label: '全部' },
    { key: 'win', label: '勝場' },
    { key: 'loss', label: '敗場' },
  ]

  return (
    <div className="flex-1 bg-gradient-to-b from-[#120f0a] via-[#0a0905] to-[#050403] px-4 py-8 max-w-2xl mx-auto w-full min-h-[calc(100vh-60px)]">
      <div className="bg-[#0f0e0a]/90 border border-[#4a3f28] shadow-[0_8px_32px_rgba(0,0,0,0.6)] rounded-2xl p-6 backdrop-blur-md">
        {/* Title */}
        <div className="font-display text-2xl text-white tracking-[3px] border-b-[3px] border-vermillion pb-3.5 mb-5 font-bold">
          對戰紀錄
        </div>
        {/* Filter tabs */}
        <div className="flex gap-2 mb-5">
          {tabs.map(t => (
            <button
              key={t.key}
              onClick={() => { setFilter(t.key); setPage(0) }}
              className={`px-4.5 py-2 font-mono text-xs md:text-sm tracking-[2px] rounded font-bold transition-all duration-150 ${filter === t.key ? 'bg-vermillion text-white shadow-[0_0_12px_rgba(204,51,0,0.3)]' : 'border border-[#4a3f28] text-[#a88a6d] hover:text-white bg-[#120f0a]/50'}`}
            >
              {t.label}
            </button>
          ))}
        </div>
        {/* Match list */}
        <div className="space-y-3">
          {paged.length === 0 ? (
            <div className="text-[#a88a6d] font-mono text-xs text-center py-12 bg-[#120f0a]/40 border border-[#2a2018]/40 rounded-xl italic">無對戰紀錄</div>
          ) : (
            paged.map((r) => (
              <div
                key={r.matchId}
                className="border border-[#4a3f28]/40 px-5 py-4.5 rounded-xl bg-[#12100b] hover:bg-[#1a1610] transition-all"
                style={{ borderLeft: `4px solid ${r.result === 'win' ? '#22c55e' : '#ef4444'}` }}
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="font-display text-sm md:text-base text-white tracking-wider font-bold">vs {r.opponent.toUpperCase()}</span>
                  <span className={`font-mono text-xs md:text-sm font-bold tracking-[2px] ${r.result === 'win' ? 'text-emerald-400' : 'text-rose-400'}`}>
                    {r.result === 'win' ? '勝 ⚔' : '敗 ☠'}
                  </span>
                </div>
                <div className="flex items-center gap-4.5">
                  <span className="font-mono text-[#a88a6d] text-xs font-semibold">{r.roundCount} 回合</span>
                  <span className="font-mono text-[#a88a6d] text-xs font-semibold">傷害 +{r.totalDamage}</span>
                  <Link to={`/replay/${r.matchId}`} className="font-mono text-xs text-amber-500 hover:text-white bg-amber-950/30 hover:bg-amber-600 px-3.5 py-1.5 rounded-lg border border-amber-500/40 hover:border-amber-500 transition-all duration-100 transform active:scale-90 shadow-[0_0_6px_rgba(245,158,11,0.15)] ml-auto">
                    看回放 ▶
                  </Link>
                </div>
              </div>
            ))
          )}
        </div>
        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex gap-3 justify-center mt-6 items-center">
            <button onClick={() => setPage(p => Math.max(0, p - 1))} disabled={page === 0}
              className="font-mono text-[#e2d6be] text-xs border border-[#4a3f28] hover:border-vermillion bg-[#120f0a] px-3.5 py-1.5 rounded disabled:opacity-30 disabled:cursor-not-allowed transition-all">
              ◀
            </button>
            <span className="font-mono text-[#a88a6d] text-xs font-bold px-2 py-1">{page + 1} / {totalPages}</span>
            <button onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))} disabled={page >= totalPages - 1}
              className="font-mono text-[#e2d6be] text-xs border border-[#4a3f28] hover:border-vermillion bg-[#120f0a] px-3.5 py-1.5 rounded disabled:opacity-30 disabled:cursor-not-allowed transition-all">
              ▶
            </button>
          </div>
        )}
      </div>
      <div className="text-center mt-8 w-full flex justify-center">
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
