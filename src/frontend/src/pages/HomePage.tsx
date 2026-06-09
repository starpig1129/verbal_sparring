import React, { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthContext } from '../contexts/AuthContext'
import Button from '../components/Button'

const API = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export default function HomePage() {
  const { isAuthenticated, username, token, userId, error, login, register, clearError } = useAuthContext()
  const [tab, setTab] = useState<'login' | 'register'>('login')
  const [inputUsername, setInputUsername] = useState('')
  const [inputPassword, setInputPassword] = useState('')
  const [opponent, setOpponent] = useState('npc')
  const [opponentTab, setOpponentTab] = useState<'npc' | 'human'>('npc')
  const [matchError, setMatchError] = useState('')
  const navigate = useNavigate()

  // New state variables for matchmaking
  interface MatchmakingPlayer {
    id: string
    username: string
    wins: number
    losses: number
    total_damage: number
    is_online: boolean
  }

  const [players, setPlayers] = useState<MatchmakingPlayer[]>([])
  const [searchQuery, setSearchQuery] = useState('')
  const [showManualInput, setShowManualInput] = useState(false)
  const [matchmakingStatus, setMatchmakingStatus] = useState<'idle' | 'queued' | 'matched'>('idle')
  const [matchmakingTime, setMatchmakingTime] = useState(0)

  interface IncomingChallenge {
    matchId: string
    challenger: string
  }
  const [incomingChallenge, setIncomingChallenge] = useState<IncomingChallenge | null>(null)

  const queueWsRef = useRef<WebSocket | null>(null)

  async function handleAuth() {
    clearError()
    const success = tab === 'login'
      ? await login(inputUsername, inputPassword)
      : await register(inputUsername, inputPassword)
    if (success) { setInputUsername(''); setInputPassword('') }
  }

  async function handleStartMatch(targetOpponent?: string) {
    const opp = targetOpponent ?? opponent
    setMatchError('')
    const resp = await fetch(`${API}/api/matches`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify({ opponent: opp }),
    })
    const data = await resp.json()
    if (resp.ok) {
      navigate(`/battle/${data.match_id}`, { state: { token, myUsername: username, userId } })
    } else {
      setMatchError(data.detail ?? '建立對局失敗')
    }
  }

  async function fetchPlayers() {
    try {
      const resp = await fetch(`${API}/api/matches/players`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      if (resp.ok) {
        const data = await resp.json()
        const sorted = data.sort((a: MatchmakingPlayer, b: MatchmakingPlayer) => {
          if (a.is_online && !b.is_online) return -1
          if (!a.is_online && b.is_online) return 1
          return b.total_damage - a.total_damage
        })
        setPlayers(sorted)
      }
    } catch (err) {
      console.error('Failed to fetch players', err)
    }
  }

  useEffect(() => {
    if (isAuthenticated) {
      fetchPlayers()
      const interval = setInterval(fetchPlayers, 10000)
      return () => clearInterval(interval)
    }
  }, [isAuthenticated])

  useEffect(() => {
    let timer: any
    if (matchmakingStatus === 'queued') {
      timer = setInterval(() => {
        setMatchmakingTime((prev: number) => prev + 1)
      }, 1000)
    }
    return () => clearInterval(timer)
  }, [matchmakingStatus])

  useEffect(() => {
    if (!isAuthenticated || !token) {
      if (queueWsRef.current) {
        queueWsRef.current.close()
        queueWsRef.current = null
      }
      return
    }

    const WS_BASE = (import.meta.env.VITE_WS_URL ?? 'ws://localhost:8000').replace(/^http/, 'ws')
    const url = `${WS_BASE}/ws/queue?token=${token}&searching=false`
    const ws = new WebSocket(url)
    queueWsRef.current = ws

    ws.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data)
        if (data.type === 'queued') {
          setMatchmakingStatus('queued')
        } else if (data.type === 'match_found') {
          setMatchmakingStatus('matched')
          setTimeout(() => {
            navigate(`/battle/${data.match_id}`, { state: { token, myUsername: username, userId } })
          }, 1200)
        } else if (data.type === 'match_challenge') {
          setIncomingChallenge({
            matchId: data.match_id,
            challenger: data.challenger
          })
        }
      } catch (err) {
        console.error(err)
      }
    }

    ws.onclose = () => {
      queueWsRef.current = null
      setMatchmakingStatus(prev => prev === 'matched' ? 'matched' : 'idle')
    }

    ws.onerror = () => {
      setMatchError('配對發生錯誤，請稍後再試')
      setMatchmakingStatus('idle')
    }

    return () => {
      ws.close()
    }
  }, [isAuthenticated, token, username, userId, navigate])

  function startMatchmaking() {
    if (!queueWsRef.current || queueWsRef.current.readyState !== WebSocket.OPEN) {
      setMatchError('連接中，請稍候...')
      return
    }
    setMatchmakingTime(0)
    setMatchError('')
    queueWsRef.current.send(JSON.stringify({ type: 'start_matchmaking' }))
  }

  function cancelMatchmaking() {
    if (!queueWsRef.current || queueWsRef.current.readyState !== WebSocket.OPEN) return
    queueWsRef.current.send(JSON.stringify({ type: 'cancel_matchmaking' }))
    setMatchmakingStatus('idle')
  }

  function handleAcceptChallenge() {
    if (incomingChallenge) {
      const { matchId: mId } = incomingChallenge
      setIncomingChallenge(null)
      navigate(`/battle/${mId}`, { state: { token, myUsername: username, userId } })
    }
  }

  function handleDeclineChallenge() {
    if (queueWsRef.current && incomingChallenge) {
      queueWsRef.current.send(JSON.stringify({
        type: 'decline_challenge',
        match_id: incomingChallenge.matchId
      }))
    }
    setIncomingChallenge(null)
  }

  function formatTime(seconds: number): string {
    const m = Math.floor(seconds / 60).toString().padStart(2, '0')
    const s = (seconds % 60).toString().padStart(2, '0')
    return `${m}:${s}`
  }

  const filteredPlayers = players.filter((p: MatchmakingPlayer) =>
    p.username.toLowerCase().includes(searchQuery.toLowerCase())
  )

  if (!isAuthenticated) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gradient-to-b from-[#120f0a] via-[#0a0905] to-[#050403] px-4">
        <div className="w-full max-w-sm bg-[#0f0e0a]/90 border border-[#4a3f28] shadow-[0_8px_32px_rgba(0,0,0,0.6)] rounded-2xl p-8 backdrop-blur-md">
          {/* Logo */}
          <div className="text-center mb-8">
            <div className="font-display text-[48px] text-white tracking-[5px] leading-tight">唇槍</div>
            <div className="font-display text-[48px] text-vermillion tracking-[5px] leading-tight" style={{ textShadow: '0 0 25px rgba(204,51,0,0.5)' }}>舌戰</div>
            <div className="font-mono text-[#a88a6d] text-xs tracking-[6px] mt-2 font-semibold">VERBAL SPARRING</div>
          </div>
          {/* Auth tabs */}
          <div className="flex border border-[#4a3f28] mb-4 rounded overflow-hidden">
            <button onClick={() => setTab('login')} className={`flex-1 py-2.5 font-display text-xs md:text-sm tracking-[3px] font-bold transition-all ${tab === 'login' ? 'bg-vermillion text-white' : 'text-[#a88a6d] hover:text-white bg-[#120f0a]/50'}`}>登入</button>
            <button onClick={() => setTab('register')} className={`flex-1 py-2.5 font-mono text-xs md:text-sm tracking-[3px] font-bold transition-all ${tab === 'register' ? 'bg-vermillion text-white' : 'text-[#a88a6d] hover:text-white bg-[#120f0a]/50'}`}>註冊</button>
          </div>
          {/* Inputs */}
          <input
            placeholder="用戶名"
            value={inputUsername}
            onChange={e => setInputUsername(e.target.value)}
            className="w-full bg-[#080805] border border-[#4a3f28] px-4 py-2.5 text-white font-mono text-sm mb-3 focus:outline-none focus:border-vermillion rounded"
          />
          <input
            type="password"
            placeholder="密碼"
            value={inputPassword}
            onChange={e => setInputPassword(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleAuth()}
            className="w-full bg-[#080805] border border-[#4a3f28] px-4 py-2.5 text-white font-mono text-sm mb-4 focus:outline-none focus:border-vermillion rounded"
          />
          {error && (
            <div className="border-l-[3px] border-vermillion bg-[#1a0005] px-3 py-2.5 text-[#ff6644] font-mono text-xs mb-4 rounded">{error}</div>
          )}
          <Button variant="primary-outline" onClick={handleAuth} className="w-full py-2.5 rounded-lg text-xs md:text-sm">進入戰場</Button>
        </div>
      </div>
    )
  }

  return (
    <div className="flex-1 flex flex-col lg:flex-row bg-gradient-to-b from-[#120f0a] via-[#0a0905] to-[#050403] min-h-[calc(100vh-60px)]">
      {/* Main Content Area */}
      <div className="flex-1 flex flex-col items-center justify-center p-6 lg:p-12">
        {/* Welcome */}
        <div className="mb-8 text-center">
          <div className="font-mono text-[#a88a6d] text-xs tracking-[3px] mb-2 font-semibold">武士歸來</div>
          <div className="font-display text-[28px] text-white tracking-[2px] font-bold">
            {username.toUpperCase()}<span className="text-vermillion text-lg ml-3 tracking-wider">入場</span>
          </div>
        </div>

        {/* Center Card: Match Control Panel */}
        <div className="w-full max-w-md bg-[#0f0e0a]/90 border border-[#4a3f28] shadow-[0_8px_32px_rgba(0,0,0,0.6)] rounded-2xl p-6 backdrop-blur-md flex flex-col justify-between min-h-[380px]">
          <div>
            <div className="font-mono text-[#e2d6be] text-xs tracking-[3px] mb-4 font-semibold border-b border-[#3a3020] pb-2">選擇對戰模式</div>
            
            <div className="flex border border-[#4a3f28] rounded overflow-hidden mb-4">
              <button onClick={() => { setOpponentTab('npc'); setOpponent('npc') }}
                className={`flex-1 py-2.5 font-display text-xs md:text-sm tracking-[2px] font-bold transition-all ${opponentTab === 'npc' ? 'bg-vermillion text-white' : 'text-[#a88a6d] hover:text-white bg-[#120f0a]/50'}`}>
                AI NPC
              </button>
              <button onClick={() => setOpponentTab('human')}
                className={`flex-1 py-2.5 font-mono text-xs md:text-sm tracking-[2px] font-bold transition-all ${opponentTab === 'human' ? 'bg-vermillion text-white' : 'text-[#a88a6d] hover:text-white bg-[#120f0a]/50'}`}>
                人類對手
              </button>
            </div>

            {opponentTab === 'npc' ? (
              <div className="flex flex-col gap-4 py-2">
                <div className="text-sm text-[#a88a6d] mb-4 font-body leading-relaxed text-center">
                  挑戰強大的毒舌 AI，磨練你的嗆聲技巧。AI 將會即時回嗆並由裁判做出判定。
                </div>
                <Button variant="primary-solid" onClick={() => handleStartMatch('npc')} className="w-full py-3 rounded-xl text-xs md:text-sm">對戰 AI NPC</Button>
              </div>
            ) : (
              <div className="flex flex-col gap-4">
                {/* Quick Match Section */}
                <div className="border border-[#4a3f28]/60 bg-[#120f0a]/40 p-4 rounded-xl text-center flex flex-col justify-center">
                  <div className="text-xs text-[#a88a6d] tracking-wider mb-2 font-semibold">尋找任何在線對手</div>
                  <div className="text-sm text-[#e2d6be] mb-4 font-body leading-normal">
                    與大廳中其他排隊玩家進行隨機快速匹配，一鍵對抗！
                  </div>
                  <Button
                    variant="primary-solid"
                    onClick={startMatchmaking}
                    className="w-full py-3 rounded-xl text-xs md:text-sm font-bold bg-gradient-to-r from-vermillion to-orange-600 shadow-[0_0_15px_rgba(204,51,0,0.4)] hover:shadow-[0_0_25px_rgba(204,51,0,0.6)]"
                  >
                    ⚡ 快速配對對決
                  </Button>
                </div>

                {/* Manual Invite */}
                <div className="border border-[#4a3f28]/60 bg-[#120f0a]/40 p-4 rounded-xl">
                  <div className="text-center">
                    <button
                      onClick={() => setShowManualInput(!showManualInput)}
                      className="text-xs text-[#a88a6d] hover:text-white underline tracking-wide font-semibold"
                    >
                      {showManualInput ? '隱藏手動輸入' : '使用用戶名手動建立對局'}
                    </button>
                  </div>
                  {showManualInput && (
                    <div className="flex gap-2 mt-3">
                      <input
                        placeholder="輸入對手用戶名"
                        value={opponent === 'npc' ? '' : opponent}
                        onChange={(e: React.ChangeEvent<HTMLInputElement>) => setOpponent(e.target.value || 'npc')}
                        className="flex-1 bg-[#080805] border border-[#4a3f28] px-3 py-1.5 text-white font-mono text-xs focus:outline-none focus:border-vermillion rounded"
                      />
                      <button
                        onClick={() => handleStartMatch()}
                        className="px-4 py-1.5 bg-vermillion text-white text-xs rounded hover:bg-red-600 transition-all font-bold"
                      >
                        開戰
                      </button>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>

          {matchError && (
            <div className="border-l-[3px] border-vermillion bg-[#1a0005] px-3 py-2.5 text-[#ff6644] font-mono text-xs mt-4 rounded">{matchError}</div>
          )}
        </div>
      </div>

      {/* Right Sidebar: Online Player Selection Panel */}
      <div className="w-full max-w-md mx-auto mt-8 lg:mt-0 lg:max-w-none lg:w-[280px] xl:w-[320px] bg-[#0f0e0a]/90 lg:bg-[#070604]/95 border border-[#3a3020] lg:border-t-0 lg:border-r-0 lg:border-b-0 lg:border-l lg:border-l-[#3a3020]/75 shadow-[0_8px_32px_rgba(0,0,0,0.6)] lg:shadow-none rounded-2xl lg:rounded-none flex flex-col lg:h-[calc(100vh-60px)] lg:sticky lg:top-[60px] z-20 overflow-hidden flex-shrink-0">
        
        {/* User profile header (desktop only) */}
        <div className="p-4 border-b border-[#3a3020]/60 hidden lg:flex items-center gap-3 bg-[#120f0a]/40">
          <div className="relative">
            <div className="w-9 h-9 rounded-full border border-[#4a3f28] bg-[#1a1712] flex items-center justify-center text-vermillion font-bold font-display text-sm">
              {username[0]?.toUpperCase()}
            </div>
            <span className="absolute bottom-0 right-0 w-2.5 h-2.5 rounded-full bg-green-500 border-2 border-[#0f0e0a] animate-pulse" />
          </div>
          <div className="flex flex-col">
            <span className="font-mono text-xs text-white font-bold tracking-wide">{username.toUpperCase()}</span>
            <span className="text-[9px] text-green-500 font-medium">在線大廳</span>
          </div>
        </div>

        {/* List title & refresh info */}
        <div className="font-mono text-[#e2d6be] text-xs tracking-[3px] p-4 lg:py-3 font-semibold border-b border-[#3a3020]/60 flex justify-between items-center bg-[#0a0806]/50 flex-shrink-0">
          <span>在線玩家列表</span>
          <span className="text-[9px] text-[#a88a6d] font-normal animate-pulse">每 10 秒重新整理</span>
        </div>

        {/* Search */}
        <div className="p-3 bg-[#050403]/40 border-b border-[#3a3020]/30 flex-shrink-0">
          <div className="relative flex items-center">
            <input
              type="text"
              placeholder="搜尋玩家名稱..."
              value={searchQuery}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => setSearchQuery(e.target.value)}
              className="w-full bg-[#050403]/80 border border-[#3a3020] pl-3 pr-8 py-2 text-white font-mono text-xs focus:outline-none focus:border-vermillion rounded transition-all"
            />
            <span className="absolute right-3 text-[10px] opacity-70">🔍</span>
          </div>
        </div>

        {/* Player list scrollable */}
        <div className="flex-1 overflow-y-auto flex flex-col gap-2 p-3 custom-scrollbar max-h-[320px] lg:max-h-none">
          {filteredPlayers.length === 0 ? (
            <div className="text-xs text-[#a88a6d] italic text-center py-8">無其他註冊玩家</div>
          ) : (
            filteredPlayers.map((p: MatchmakingPlayer) => (
              <div key={p.id} className="flex justify-between items-center p-2.5 rounded bg-[#16140f]/60 border border-[#3e3420]/50 hover:border-[#4a3f28] hover:bg-[#1f1b14]/70 transition-all duration-200 animate-fade-in">
                <div className="flex flex-col gap-0.5">
                  <div className="font-mono text-xs text-white font-bold">{p.username}</div>
                  <div className="text-[10px] text-[#a88a6d] font-mono">
                    勝 {p.wins} | 敗 {p.losses} | 傷害 {p.total_damage}
                  </div>
                </div>
                
                {/* Online indicator & challenge button */}
                <div className="flex items-center gap-2.5">
                  <div className="flex flex-col items-end">
                    <span className={`w-2 h-2 rounded-full ${p.is_online ? 'bg-green-500 animate-pulse' : 'bg-zinc-600'}`} />
                    <span className="text-[9px] text-[#a88a6d] mt-0.5">{p.is_online ? '在線' : '離線'}</span>
                  </div>
                  <button
                    onClick={() => handleStartMatch(p.username)}
                    disabled={!p.is_online}
                    className={`text-[10px] tracking-wider px-3 py-1.5 rounded font-bold transition-all ${
                      p.is_online
                        ? 'bg-vermillion hover:bg-red-600 text-white shadow-[0_0_8px_rgba(204,51,0,0.3)] cursor-pointer'
                        : 'bg-zinc-800 text-zinc-500 border border-zinc-700 opacity-40 cursor-not-allowed'
                    }`}
                  >
                    挑戰
                  </button>
                </div>
              </div>
            ))
          )}
        </div>

        {/* Footer (desktop only) */}
        <div className="p-3 bg-[#050403]/90 border-t border-[#3a3020]/40 text-center font-mono text-[9px] text-[#a88a6d] hidden lg:block flex-shrink-0">
          ⚔️ 唇槍舌戰大廳 ⚔️
        </div>
      </div>

      {/* Matchmaking Overlay Modal */}
      {matchmakingStatus !== 'idle' && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm transition-all duration-300">
          <div className="w-full max-w-sm p-8 bg-[#0f0e0a] border-2 border-[#4a3f28] shadow-[0_0_50px_rgba(204,51,0,0.5)] rounded-2xl text-center flex flex-col items-center gap-6">
            {/* Spinning/pulsing animation */}
            <div className="relative w-24 h-24 flex items-center justify-center">
              <div className="absolute inset-0 rounded-full border-4 border-[#3a3020] opacity-40"></div>
              {matchmakingStatus === 'queued' ? (
                <>
                  <div className="absolute inset-0 rounded-full border-4 border-t-vermillion border-r-transparent border-b-transparent border-l-transparent animate-spin"></div>
                  <div className="absolute inset-2 rounded-full border-2 border-dashed border-[#a88a6d] animate-pulse"></div>
                  <span className="text-vermillion text-2xl font-mono animate-bounce">⚔️</span>
                </>
              ) : (
                <>
                  <div className="absolute inset-0 rounded-full border-4 border-green-500 scale-110 transition-all duration-300 animate-pulse"></div>
                  <span className="text-green-500 text-3xl font-mono animate-ping">🏁</span>
                </>
              )}
            </div>

            <div className="flex flex-col gap-2">
              <h2 className="font-display text-xl text-white tracking-[3px] font-bold">
                {matchmakingStatus === 'queued' ? '尋找對手中' : '配對成功！'}
              </h2>
              <p className="text-xs text-[#a88a6d] font-body tracking-wider leading-relaxed">
                {matchmakingStatus === 'queued'
                  ? '正在搜尋同時間加入佇列的挑戰者...'
                  : '正在載入戰場，請做好戰鬥準備！'}
              </p>
            </div>

            {matchmakingStatus === 'queued' && (
              <div className="flex flex-col items-center gap-4 w-full">
                <div className="font-mono text-3xl text-white font-bold tracking-wider">
                  {formatTime(matchmakingTime)}
                </div>
                <Button
                  variant="primary-outline"
                  onClick={cancelMatchmaking}
                  className="px-6 py-2 rounded-lg text-xs"
                >
                  取消配對
                </Button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Incoming Challenge Modal */}
      {incomingChallenge && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm transition-all duration-300">
          <div className="w-full max-w-sm p-8 bg-[#0f0e0a] border-2 border-vermillion shadow-[0_0_50px_rgba(204,51,0,0.5)] rounded-2xl text-center flex flex-col items-center gap-6">
            <div className="w-16 h-16 rounded-full border border-vermillion flex items-center justify-center text-vermillion font-bold font-display text-xl animate-pulse">
              ⚔️
            </div>
            <div className="flex flex-col gap-2">
              <h2 className="font-display text-xl text-white tracking-[2px] font-bold">收到挑戰！</h2>
              <p className="text-sm text-[#e2d6be] font-mono font-bold">
                【{incomingChallenge.challenger.toUpperCase()}】
              </p>
              <p className="text-xs text-[#a88a6d] font-body tracking-wider leading-relaxed">
                向你發起了指定對決！你是否接受挑戰？
              </p>
            </div>
            <div className="flex gap-4 w-full">
              <button
                onClick={handleDeclineChallenge}
                className="flex-1 py-2.5 border border-[#4a3f28] hover:border-zinc-500 hover:text-white bg-[#120f0a] text-zinc-400 text-xs rounded transition-all font-bold"
              >
                拒絕
              </button>
              <button
                onClick={handleAcceptChallenge}
                className="flex-1 py-2.5 bg-vermillion hover:bg-red-600 text-white text-xs rounded transition-all font-bold shadow-[0_0_15px_rgba(204,51,0,0.4)]"
              >
                接受挑戰
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

