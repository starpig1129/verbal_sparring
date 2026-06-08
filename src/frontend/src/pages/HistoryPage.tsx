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
    <div className="flex-1 bg-ink px-4 py-6 max-w-2xl mx-auto w-full">
      {/* Title */}
      <div className="font-display text-[20px] text-white tracking-[3px] border-b-[3px] border-vermillion pb-2 mb-4">
        對戰紀錄
      </div>
      {/* Filter tabs */}
      <div className="flex gap-1 mb-4">
        {tabs.map(t => (
          <button
            key={t.key}
            onClick={() => { setFilter(t.key); setPage(0) }}
            className={`px-3 py-1 font-mono text-[9px] tracking-[2px] ${filter === t.key ? 'bg-vermillion text-white' : 'border border-bamboo text-bark hover:text-aged'}`}
          >
            {t.label}
          </button>
        ))}
      </div>
      {/* Match list */}
      {paged.length === 0 ? (
        <div className="text-bark font-mono text-[9px] text-center py-8">無對戰紀錄</div>
      ) : (
        paged.map((r) => (
          <div
            key={r.matchId}
            className={`border border-bamboo px-4 py-3 mb-2 ${r.result === 'win' ? 'bg-parchment' : ''}`}
          >
            <div className="flex items-center justify-between mb-1">
              <span className="font-display text-[13px] text-white tracking-wider">vs {r.opponent.toUpperCase()}</span>
              <span className={`font-mono text-[9px] tracking-[2px] ${r.result === 'win' ? 'text-[#66cc00]' : 'text-vermillion'}`}>
                {r.result === 'win' ? '勝' : '敗'}
              </span>
            </div>
            <div className="flex items-center gap-3">
              <span className="font-mono text-bark text-[8px]">{r.roundCount} 回合</span>
              <span className="font-mono text-bark text-[8px]">傷害 +{r.totalDamage}</span>
              <Link to={`/replay/${r.matchId}`} className="font-mono text-aged text-[8px] tracking-[2px] hover:text-white ml-auto">
                看回放 ▶
              </Link>
            </div>
          </div>
        ))
      )}
      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex gap-2 justify-center mt-4">
          <button onClick={() => setPage(p => Math.max(0, p - 1))} disabled={page === 0}
            className="font-mono text-bark text-[9px] border border-bamboo px-3 py-1 disabled:opacity-40 hover:text-aged">
            ◀
          </button>
          <span className="font-mono text-aged text-[9px] px-2 py-1">{page + 1} / {totalPages}</span>
          <button onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))} disabled={page >= totalPages - 1}
            className="font-mono text-bark text-[9px] border border-bamboo px-3 py-1 disabled:opacity-40 hover:text-aged">
            ▶
          </button>
        </div>
      )}
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
