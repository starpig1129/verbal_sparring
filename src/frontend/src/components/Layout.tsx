// src/frontend/src/components/Layout.tsx
import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import Navbar from './Navbar'
import { useAuthContext } from '../contexts/AuthContext'

export default function Layout() {
  const { isAuthenticated, username, logout } = useAuthContext()
  const navigate = useNavigate()
  const location = useLocation()
  const isBattlePage = location.pathname.startsWith('/battle/')

  function handleLogout() {
    logout()
    navigate('/')
  }

  return (
    <div className="flex flex-col min-h-screen bg-ink text-white">
      {isAuthenticated && !isBattlePage && <Navbar username={username} onLogout={handleLogout} />}
      <Outlet />
    </div>
  )
}
