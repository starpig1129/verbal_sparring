// src/frontend/src/components/Navbar.tsx
import { Link } from 'react-router-dom'

type Props = { username: string; onLogout: () => void }

export default function Navbar({ username: _username, onLogout }: Props) {
  return (
    <nav className="bg-[#0f0e0b] border-b-2 border-bamboo flex justify-between items-center px-4 py-2 flex-shrink-0">
      <Link to="/" className="font-display text-[15px] text-white tracking-[2px]">
        唇槍<span className="text-vermillion">舌戰</span>
      </Link>
      <div className="flex gap-3 items-center">
        <Link to="/leaderboard" className="font-mono text-[9px] text-aged tracking-[2px] hover:text-white">排行榜</Link>
        <Link to="/profile" className="font-mono text-[9px] text-aged tracking-[2px] hover:text-white">我的戰績</Link>
        <Link to="/history" className="font-mono text-[9px] text-aged tracking-[2px] hover:text-white">對戰紀錄</Link>
        <button
          onClick={onLogout}
          className="font-mono text-[9px] text-bark border border-bamboo px-2 py-1 tracking-[2px] hover:text-aged"
        >
          登出
        </button>
      </div>
    </nav>
  )
}
