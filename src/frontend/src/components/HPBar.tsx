import { motion } from 'framer-motion'

type Props = { label: string; hp: number; maxHp?: number }

function gradientClass(pct: number) {
  if (pct > 50) return 'from-[#336600] to-[#66cc00]'
  if (pct > 20) return 'from-[#885500] to-[#ffaa00]'
  return 'from-[#660000] via-[#cc0000] to-[#ff2200]'
}

function glowStyle(pct: number) {
  if (pct > 50) return '0 0 8px rgba(80,180,0,0.4)'
  if (pct > 20) return '0 0 8px rgba(200,130,0,0.4)'
  return '0 0 10px rgba(180,40,0,0.6)'
}

export default function HPBar({ label, hp, maxHp = 100 }: Props) {
  const pct = Math.max(0, Math.min(100, (hp / maxHp) * 100))
  return (
    <div>
      <div className="flex justify-between mb-1.5 items-end">
        <span className="font-mono text-[#e2d6be] text-xs font-semibold tracking-[2px] uppercase">{label}</span>
        <span>
          <span className="font-display text-white text-xl leading-none font-bold">{hp}</span>
          <span className="text-[#a88a6d] text-xs"> /{maxHp}</span>
        </span>
      </div>
      <div className="bg-[#080805] border border-[#4a3f28] h-[10px] rounded-full overflow-hidden">
        <motion.div
          role="progressbar"
          aria-valuenow={hp}
          aria-valuemax={maxHp}
          className={`h-full bg-gradient-to-r ${gradientClass(pct)}`}
          style={{ boxShadow: glowStyle(pct) }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.4, ease: 'easeOut' }}
        />
      </div>
    </div>
  )
}
