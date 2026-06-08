// src/frontend/src/pages/ProfilePage.tsx
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuthContext } from '../contexts/AuthContext'
import type { LeaderboardEntry, MatchRecord } from '../types/game'

const API = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

function rankTitle(wins: number) {
  if (wins >= 50) return '武林盟主'
  if (wins >= 20) return '武林高手'
  if (wins >= 10) return '初出茅廬'
  return '江湖新人'
}

export default function ProfilePage() {
  const { username, token } = useAuthContext()
  const [stats, setStats] = useState<LeaderboardEntry | null>(null)
  const [history, setHistory] = useState<MatchRecord[]>([])

  useEffect(() => {
    fetch(`${API}/api/leaderboard`)
      .then(r => r.json())
      .then((d: { entries: LeaderboardEntry[] }) => {
        const mine = d.entries.find(e => e.username === username)
        if (mine) setStats(mine)
      })
  }, [username])

  useEffect(() => {
    if (!token) return
    fetch(`${API}/api/matches/history`, {
      headers: { Authorization: `Bearer ${token}` }
    })
      .then(r => {
        if (!r.ok) throw new Error('Failed to fetch')
        return r.json()
      })
      .then(d => {
        if (Array.isArray(d)) {
          const userMatches = d.filter(
            (m: any) => m.player1_username === username || m.player2_username === username
          )
          const formatted: MatchRecord[] = userMatches.map((m: any) => {
            const opponent = m.player1_username === username ? m.player2_username : m.player1_username
            const result = m.winner_username === username ? 'win' : 'loss'
            return {
              matchId: m.match_id,
              opponent,
              result,
              totalDamage: m.total_damage,
              roundCount: m.round_count,
              timestamp: m.timestamp,
            }
          })
          setHistory(formatted.slice(0, 5))
        }
      })
      .catch(err => {
        console.error('Failed to fetch profile matches history', err)
        setHistory([])
      })
  }, [username, token])

  return (
    <div className="flex-1 bg-gradient-to-b from-[#120f0a] via-[#0a0905] to-[#050403] px-4 py-8 max-w-md mx-auto w-full flex flex-col justify-between min-h-[calc(100vh-60px)]">
      <div className="w-full">
        {/* Avatar + name card */}
        <div className="bg-[#0f0e0a]/90 border border-[#4a3f28] shadow-[0_8px_32px_rgba(0,0,0,0.6)] rounded-2xl p-6 mb-6 flex flex-col items-center backdrop-blur-md">
          <div className="w-20 h-20 rounded-full border-2 border-vermillion flex items-center justify-center mb-3 shadow-[0_0_20px_rgba(204,51,0,0.3)] bg-gradient-to-br from-[#221b12] to-[#0d0a07]">
            <span className="font-display text-[32px] text-vermillion font-bold">{username.charAt(0).toUpperCase()}</span>
          </div>
          <div className="font-display text-2xl text-white tracking-[3px] font-bold">{username.toUpperCase()}</div>
          <div className="inline-block font-mono text-[11px] tracking-[2px] font-bold text-[#ffcc00] border border-[#ffcc00]/30 rounded-full px-3.5 py-1 mt-2.5 bg-[#ffcc00]/5 shadow-[inset_0_0_8px_rgba(255,204,0,0.1)]">
            {rankTitle(stats?.wins ?? 0)}
          </div>
        </div>

        {/* Stats grid */}
        <div className="grid grid-cols-3 gap-3 mb-6">
          {/* 勝場 Card */}
          <div className="bg-[#0e2216]/60 border border-emerald-900/50 p-4 rounded-xl text-center flex flex-col justify-between shadow-sm">
            <div className="font-display text-[26px] text-emerald-400 font-bold">{stats?.wins ?? 0}</div>
            <div className="font-mono text-emerald-500/90 text-xs tracking-[1px] mt-1 font-medium">勝場</div>
          </div>
          {/* 敗場 Card */}
          <div className="bg-[#220f0d]/60 border border-rose-950/50 p-4 rounded-xl text-center flex flex-col justify-between shadow-sm">
            <div className="font-display text-[26px] text-rose-400 font-bold">{stats?.losses ?? 0}</div>
            <div className="font-mono text-rose-500/80 text-xs tracking-[1px] mt-1 font-medium">敗場</div>
          </div>
          {/* 累積傷害 Card */}
          <div className="bg-[#24170d]/60 border border-[#5c3311]/50 p-4 rounded-xl text-center flex flex-col justify-between shadow-sm">
            <div className="font-display text-[16px] text-vermillion font-bold mt-1.5 break-all">{(stats?.total_damage ?? 0).toLocaleString()}</div>
            <div className="font-mono text-[#a88a6d] text-xs tracking-[1px] mt-1 font-medium">累積傷害</div>
          </div>
        </div>

        {/* Recent matches */}
        <div className="mb-6">
          <div className="font-mono text-[#e2d6be] text-xs tracking-[2px] mb-3.5 font-semibold border-b border-[#3a3020] pb-2 flex items-center justify-between">
            <span>最近五場</span>
            <span className="text-xs text-[#a88a6d] font-normal">{history.length} 次戰鬥</span>
          </div>
          {history.length === 0 ? (
            <div className="text-[#886655] font-mono text-xs text-center py-8 bg-[#120f0a]/40 border border-[#2a2018]/40 rounded-xl italic">
              尚無對戰紀錄
            </div>
          ) : (
            history.map((r) => (
              <div
                key={r.matchId}
                className="flex items-center gap-3 px-4 py-3 mb-2.5 rounded-xl border border-[#423724]/40 hover:border-vermillion/30 bg-[#12100b] hover:bg-[#1a1610] transition-all duration-200 transform hover:-translate-y-0.5 shadow-sm hover:shadow-[0_4px_12px_rgba(0,0,0,0.4)]"
                style={{ borderLeft: `4px solid ${r.result === 'win' ? '#22c55e' : '#ef4444'}` }}
              >
                {r.result === 'win' ? (
                  <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-emerald-950/80 text-emerald-400 border border-emerald-800/40">勝</span>
                ) : (
                  <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-rose-950/80 text-rose-400 border border-rose-800/40">敗</span>
                )}
                <span className="font-display text-sm text-white flex-1 tracking-wider ml-1">vs {r.opponent.toUpperCase()}</span>
                <span className="font-mono text-vermillion/90 text-xs font-bold bg-vermillion/5 px-2 py-0.5 border border-vermillion/25 rounded">+{r.totalDamage} 傷</span>
                <Link
                  to={`/replay/${r.matchId}`}
                  className="font-mono text-xs text-amber-500 hover:text-white bg-amber-950/30 hover:bg-amber-600 px-3 py-1.5 rounded-lg border border-amber-500/40 hover:border-amber-500 transition-all duration-100 transform active:scale-90 shadow-[0_0_6px_rgba(245,158,11,0.15)] hover:shadow-[0_0_10px_rgba(245,158,11,0.4)] ml-1"
                >
                  回放 ▶
                </Link>
              </div>
            ))
          )}
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
