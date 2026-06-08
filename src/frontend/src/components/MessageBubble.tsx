// src/frontend/src/components/MessageBubble.tsx
import { motion } from 'framer-motion'

type SystemProps = { kind: 'system'; displayText: string }
type AttackProps = { kind: 'attack'; sender: string; displayText: string; damage: number; isNpc: boolean }
type RefereeProps = { kind: 'referee'; displayText: string }

type Props = SystemProps | AttackProps | RefereeProps

export default function MessageBubble(props: Props) {
  if (props.kind === 'system') {
    return (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 0.85 }}
        className="text-[#a88a6d] text-xs font-mono tracking-[2px] text-center my-1.5 py-1"
      >
        {props.displayText}
      </motion.div>
    )
  }

  if (props.kind === 'attack') {
    return (
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.2 }}
        className="flex gap-3 items-center py-1.5 border-b border-[#1b1510]/30"
      >
        <span className={`font-display text-sm md:text-base tracking-wider min-w-[70px] uppercase flex-shrink-0 font-bold ${props.isNpc ? 'text-vermillion' : 'text-white'}`}>
          {props.sender}
        </span>
        <span className="text-[#fff0d4] font-body text-sm md:text-base flex-1 leading-relaxed">{props.displayText}</span>
        <span className="bg-[#2a1100] border border-[#ff4400]/40 text-[#ff8800] px-2.5 py-0.5 font-mono text-xs rounded whitespace-nowrap flex-shrink-0 shadow-[0_0_6px_rgba(255,68,0,0.15)]">
          -<b className="text-white text-sm font-bold ml-0.5">{props.damage}</b>
        </span>
      </motion.div>
    )
  }

  return null
}
