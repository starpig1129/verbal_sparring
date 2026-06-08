import { Link, useLocation } from 'react-router-dom'

type Props = { username: string; onLogout: () => void }

export default function Navbar({ username: _username, onLogout }: Props) {
  const location = useLocation()
  const currentPath = location.pathname

  const linkClass = (path: string) => {
    const isActive = currentPath === path
    return `font-mono text-xs md:text-sm tracking-[2px] pb-1 border-b-2 transition-all duration-200 ${
      isActive
        ? 'text-white border-vermillion font-bold'
        : 'text-[#a88a6d] border-transparent hover:text-white hover:border-vermillion/40'
    }`
  }

  return (
    <nav className="bg-[#0f0e0b] border-b-2 border-bamboo flex justify-between items-center px-6 h-[60px] flex-shrink-0 z-30 relative shadow-lg">
      <Link to="/" className="font-display text-xl md:text-2xl text-white tracking-[3px] hover:text-vermillion transition-colors duration-150 flex items-center gap-1.5">
        唇槍<span className="text-vermillion">舌戰</span>
      </Link>
      
      <div className="flex gap-6 md:gap-8 items-center">
        <Link to="/leaderboard" className={linkClass('/leaderboard')}>
          排行榜
        </Link>
        <Link to="/profile" className={linkClass('/profile')}>
          我的戰績
        </Link>
        <Link to="/history" className={linkClass('/history')}>
          對戰紀錄
        </Link>
        
        <button
          onClick={onLogout}
          className="font-mono text-xs md:text-sm text-rose-400 border border-rose-950 hover:border-rose-500/70 bg-rose-950/20 px-4 py-1.5 rounded-lg tracking-[2px] transition-all duration-100 transform active:scale-95 hover:bg-rose-950/40 hover:text-rose-300"
        >
          登出
        </button>
      </div>
    </nav>
  )
}
