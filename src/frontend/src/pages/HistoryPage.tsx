import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuthContext } from '../contexts/AuthContext'

const API = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

interface MatchHistoryEntry {
  match_id: string
  player1_username: string
  player2_username: string
  winner_username: string | null
  round_count: number
  total_damage: number
  timestamp: number
}

type Filter = 'all' | 'mine' | 'pvp' | 'pve'

export default function HistoryPage() {
  const { username, token } = useAuthContext()
  const [history, setHistory] = useState<MatchHistoryEntry[]>([])
  const [filter, setFilter] = useState<Filter>('all')
  const [page, setPage] = useState(0)
  const PAGE_SIZE = 15

  async function fetchHistory() {
    try {
      const resp = await fetch(`${API}/api/matches/history`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      if (resp.ok) {
        const data = await resp.json()
        setHistory(data)
      }
    } catch (err) {
      console.error('Failed to fetch history', err)
    }
  }

  useEffect(() => {
    if (token) {
      fetchHistory()
    }
  }, [token])

  const filtered = history.filter((r: MatchHistoryEntry) => {
    if (filter === 'all') return true
    if (filter === 'mine') {
      return r.player1_username === username || r.player2_username === username
    }
    if (filter === 'pvp') {
      return r.player2_username.toLowerCase() !== 'npc'
    }
    if (filter === 'pve') {
      return r.player2_username.toLowerCase() === 'npc'
    }
    return true
  })

  const paged = filtered.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE)
  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE))

  const tabs: { key: Filter; label: string }[] = [
    { key: 'all', label: '所有對決' },
    { key: 'mine', label: '我的對戰' },
    { key: 'pvp', label: '人類對決' },
    { key: 'pve', label: 'AI 對決' },
  ]

  function formatDate(timestamp: number): string {
    if (!timestamp) return '未知時間'
    const date = new Date(timestamp * 1000)
    return date.toLocaleDateString('zh-TW', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  return (
    <div className="flex-1 bg-gradient-to-b from-[#120f0a] via-[#0a0905] to-[#050403] px-4 py-8 max-w-2xl mx-auto w-full min-h-[calc(100vh-60px)]">
      <div className="bg-[#0f0e0a]/90 border border-[#4a3f28] shadow-[0_8px_32px_rgba(0,0,0,0.6)] rounded-2xl p-6 backdrop-blur-md">
        {/* Title */}
        <div className="font-display text-2xl text-white tracking-[3px] border-b-[3px] border-vermillion pb-3.5 mb-5 font-bold flex justify-between items-center">
          <span>對戰紀錄</span>
          <button 
            onClick={fetchHistory}
            className="text-xs font-mono font-normal text-[#a88a6d] hover:text-white transition-colors cursor-pointer"
          >
            🔄 重新整理
          </button>
        </div>
        {/* Filter tabs */}
        <div className="flex gap-2 mb-5 overflow-x-auto pb-1 custom-scrollbar">
          {tabs.map(t => (
            <button
              key={t.key}
              onClick={() => { setFilter(t.key); setPage(0) }}
              className={`px-4.5 py-2 font-mono text-xs md:text-sm tracking-[2px] rounded font-bold transition-all duration-150 flex-shrink-0 cursor-pointer ${filter === t.key ? 'bg-vermillion text-white shadow-[0_0_12px_rgba(204,51,0,0.3)]' : 'border border-[#4a3f28] text-[#a88a6d] hover:text-white bg-[#120f0a]/50'}`}
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
            paged.map((r: MatchHistoryEntry) => {
              const isP1 = r.player1_username === username
              const isP2 = r.player2_username === username
              const userInvolved = isP1 || isP2
              
              let resultBorder = 'border-l-4 border-l-[#3a3020]'
              let resultText = ''
              let resultColor = 'text-zinc-400'

              if (userInvolved) {
                const isWinner = r.winner_username === username
                resultBorder = isWinner ? 'border-l-4 border-l-green-500' : 'border-l-4 border-l-rose-500'
                resultText = isWinner ? '勝利 ⚔' : '戰敗 ☠'
                resultColor = isWinner ? 'text-emerald-400' : 'text-rose-400'
              } else {
                resultText = r.winner_username ? `勝者: ${r.winner_username}` : '平手'
                resultColor = r.winner_username ? 'text-amber-400' : 'text-zinc-400'
              }

              return (
                <div
                  key={r.match_id}
                  className={`border border-[#4a3f28]/40 px-5 py-4.5 rounded-xl bg-[#12100b] hover:bg-[#1a1610] transition-all duration-150 ${resultBorder}`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-display text-sm md:text-base text-white tracking-wider font-bold">
                      {r.player1_username} <span className="text-vermillion font-normal text-xs px-1">VS</span> {r.player2_username}
                    </span>
                    <span className={`font-mono text-xs md:text-sm font-bold tracking-[2px] ${resultColor}`}>
                      {resultText}
                    </span>
                  </div>
                  <div className="flex items-center gap-4.5">
                    <span className="font-mono text-[#a88a6d] text-xs font-semibold">{r.round_count} 回合</span>
                    <span className="font-mono text-[#a88a6d] text-xs font-semibold">傷害 +{r.total_damage}</span>
                    <span className="font-mono text-[#886655] text-[10px] hidden md:inline-block ml-2">{formatDate(r.timestamp)}</span>
                    <Link to={`/replay/${r.match_id}`} className="font-mono text-xs text-amber-500 hover:text-white bg-amber-950/30 hover:bg-amber-600 px-3.5 py-1.5 rounded-lg border border-amber-500/40 hover:border-amber-500 transition-all duration-100 transform active:scale-90 shadow-[0_0_6px_rgba(245,158,11,0.15)] ml-auto cursor-pointer">
                      看回放 ▶
                    </Link>
                  </div>
                </div>
              )
            })
          )}
        </div>
        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex gap-3 justify-center mt-6 items-center">
            <button onClick={() => setPage(p => Math.max(0, p - 1))} disabled={page === 0}
              className="font-mono text-[#e2d6be] text-xs border border-[#4a3f28] hover:border-vermillion bg-[#120f0a] px-3.5 py-1.5 rounded disabled:opacity-30 disabled:cursor-not-allowed transition-all cursor-pointer">
              ◀
            </button>
            <span className="font-mono text-[#a88a6d] text-xs font-bold px-2 py-1">{page + 1} / {totalPages}</span>
            <button onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))} disabled={page >= totalPages - 1}
              className="font-mono text-[#e2d6be] text-xs border border-[#4a3f28] hover:border-vermillion bg-[#120f0a] px-3.5 py-1.5 rounded disabled:opacity-30 disabled:cursor-not-allowed transition-all cursor-pointer">
              ▶
            </button>
          </div>
        )}
      </div>
      <div className="text-center mt-8 w-full flex justify-center">
        <Link
          to="/"
          className="inline-flex items-center justify-center gap-2 font-mono text-xs text-[#a88a6d] hover:text-white border border-[#4a3f28] hover:border-[#886655] bg-[#14100b] hover:bg-[#1a1610] px-6 py-2.5 rounded-xl shadow-sm tracking-[2px] transition-all duration-100 transform active:scale-95 w-full max-w-xs cursor-pointer"
        >
          ← 返回大廳
        </Link>
      </div>
    </div>
  )
}
