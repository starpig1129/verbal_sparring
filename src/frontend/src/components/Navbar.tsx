// src/frontend/src/components/Navbar.tsx
import { Link } from 'react-router-dom'

type Props = { username: string; onLogout: () => void }

export default function Navbar({ username: _username, onLogout }: Props) {
  return (
    <nav className="bg-[#0f0e0b] border-b-2 border-bamboo flex justify-between items-center px-4 py-2.5 flex-shrink-0">
      <Link to="/" className="font-display text-[17px] text-white tracking-[2px] hover:text-vermillion transition-colors duration-150">
        唇槍<span className="text-vermillion">舌戰</span>
      </Link>
      <div className="flex gap-4 items-center">
        <Link to="/leaderboard" className="font-mono text-xs text-[#a88a6d] tracking-[2px] hover:text-white transition-colors duration-150">排行榜</Link>
        <Link to="/profile" className="font-mono text-xs text-[#a88a6d] tracking-[2px] hover:text-white transition-colors duration-150">我的戰績</Link>
        <Link to="/history" className="font-mono text-xs text-[#a88a6d] tracking-[2px] hover:text-white transition-colors duration-150">對戰紀錄</Link>
        <button
          onClick={onLogout}
          className="font-mono text-xs text-rose-400 border border-rose-950 hover:border-rose-500/70 bg-rose-950/20 px-3 py-1 rounded tracking-[2px] transition-all duration-100 transform active:scale-95 hover:bg-rose-950/40 hover:text-rose-300"
        >
          登出
        </button>
      </div>
    </nav>
  )
}
