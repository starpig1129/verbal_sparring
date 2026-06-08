// src/frontend/src/pages/HomePage.tsx
import { useState } from 'react'
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

  async function handleAuth() {
    clearError()
    const success = tab === 'login'
      ? await login(inputUsername, inputPassword)
      : await register(inputUsername, inputPassword)
    if (success) { setInputUsername(''); setInputPassword('') }
  }

  async function handleStartMatch() {
    setMatchError('')
    const resp = await fetch(`${API}/api/matches`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify({ opponent }),
    })
    const data = await resp.json()
    if (resp.ok) {
      navigate(`/battle/${data.match_id}`, { state: { token, myUsername: username, userId } })
    } else {
      setMatchError(data.detail ?? '建立對局失敗')
    }
  }

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
    <div className="flex-1 flex flex-col items-center justify-center bg-gradient-to-b from-[#120f0a] via-[#0a0905] to-[#050403] p-6 min-h-[calc(100vh-60px)]">
      {/* Welcome */}
      <div className="mb-8 text-center">
        <div className="font-mono text-[#a88a6d] text-xs tracking-[3px] mb-2 font-semibold">武士歸來</div>
        <div className="font-display text-[28px] text-white tracking-[2px] font-bold">
          {username.toUpperCase()}<span className="text-vermillion text-lg ml-3 tracking-wider">入場</span>
        </div>
      </div>
      {/* Match card */}
      <div className="w-full max-w-md bg-[#0f0e0a]/90 border border-[#4a3f28] shadow-[0_8px_32px_rgba(0,0,0,0.6)] rounded-2xl p-6 backdrop-blur-md">
        <div className="font-mono text-[#e2d6be] text-xs tracking-[3px] mb-4 font-semibold border-b border-[#3a3020] pb-2">選擇對手</div>
        <div className="flex border border-[#4a3f28] mb-4 rounded overflow-hidden">
          <button onClick={() => { setOpponentTab('npc'); setOpponent('npc') }}
            className={`flex-1 py-2.5 font-display text-xs md:text-sm tracking-[2px] font-bold transition-all ${opponentTab === 'npc' ? 'bg-vermillion text-white' : 'text-[#a88a6d] hover:text-white bg-[#120f0a]/50'}`}>
            AI NPC
          </button>
          <button onClick={() => setOpponentTab('human')}
            className={`flex-1 py-2.5 font-mono text-xs md:text-sm tracking-[2px] font-bold transition-all ${opponentTab === 'human' ? 'bg-vermillion text-white' : 'text-[#a88a6d] hover:text-white bg-[#120f0a]/50'}`}>
            人類對手
          </button>
        </div>
        {opponentTab === 'human' && (
          <input
            placeholder="輸入對手用戶名"
            value={opponent === 'npc' ? '' : opponent}
            onChange={e => setOpponent(e.target.value || 'npc')}
            className="w-full bg-[#080805] border border-[#4a3f28] px-4 py-2.5 text-white font-mono text-sm mb-4 focus:outline-none focus:border-vermillion rounded"
          />
        )}
        {matchError && (
          <div className="border-l-[3px] border-vermillion bg-[#1a0005] px-3 py-2.5 text-[#ff6644] font-mono text-xs mb-4 rounded">{matchError}</div>
        )}
        <Button variant="primary-solid" onClick={handleStartMatch} className="w-full py-3 rounded-xl text-xs md:text-sm">開戰！</Button>
      </div>
    </div>
  )
}
