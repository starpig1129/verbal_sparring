// src/frontend/src/contexts/AuthContext.tsx
import { createContext, useContext, useState, type ReactNode } from 'react'

const API = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

type Auth = { token: string; username: string; userId: string }

type AuthCtx = Auth & {
  error: string
  isAuthenticated: boolean
  login: (username: string, password: string) => Promise<boolean>
  register: (username: string, password: string) => Promise<boolean>
  logout: () => void
  clearError: () => void
}

const AuthContext = createContext<AuthCtx>({} as AuthCtx)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [auth, setAuth] = useState<Auth>({
    token: localStorage.getItem('token') ?? '',
    username: localStorage.getItem('username') ?? '',
    userId: localStorage.getItem('userId') ?? '',
  })
  const [error, setError] = useState('')

  function persist(token: string, username: string, userId: string) {
    localStorage.setItem('token', token)
    localStorage.setItem('username', username)
    localStorage.setItem('userId', userId)
    setAuth({ token, username, userId })
  }

  async function login(username: string, password: string) {
    setError('')
    try {
      const resp = await fetch(`${API}/api/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      })
      const data = await resp.json()
      if (!resp.ok) { setError('登入失敗：' + (data.detail ?? '')); return false }
      persist(data.access_token, data.username, data.user_id)
      return true
    } catch (err: any) {
      setError(`無法連接至伺服器。請確認後端是否啟動以及 API 設定。呼叫網址：${API}/api/auth/login，錯誤：${err.message || err}`)
      return false
    }
  }

  async function register(username: string, password: string) {
    setError('')
    try {
      const resp = await fetch(`${API}/api/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      })
      const data = await resp.json()
      if (!resp.ok) { setError('註冊失敗：' + (data.detail ?? '')); return false }
      persist(data.access_token, data.username, data.user_id)
      return true
    } catch (err: any) {
      setError(`無法連接至伺服器。請確認後端是否啟動以及 API 設定。呼叫網址：${API}/api/auth/register，錯誤：${err.message || err}`)
      return false
    }
  }

  function logout() {
    localStorage.removeItem('token')
    localStorage.removeItem('username')
    localStorage.removeItem('userId')
    setAuth({ token: '', username: '', userId: '' })
  }

  return (
    <AuthContext.Provider value={{
      ...auth,
      error,
      isAuthenticated: !!auth.token,
      login, register, logout,
      clearError: () => setError(''),
    }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuthContext() {
  return useContext(AuthContext)
}
