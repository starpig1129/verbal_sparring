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
        animate={{ opacity: 0.4 }}
        className="text-bark text-[9px] font-mono tracking-[2px] text-center my-1 py-1"
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
        className="flex gap-2 items-baseline py-[2px]"
      >
        <span className={`font-display text-[13px] tracking-wider min-w-[55px] uppercase flex-shrink-0 ${props.isNpc ? 'text-vermillion' : 'text-white'}`}>
          {props.sender}
        </span>
        <span className="text-[#d4c5aa] font-body italic text-[11px] flex-1">{props.displayText}</span>
        <span className="bg-[#140a00] border border-[#3a1800] text-aged px-2 py-[1px] font-mono text-[9px] whitespace-nowrap flex-shrink-0">
          -<b className="text-white text-[11px]">{props.damage}</b>
        </span>
      </motion.div>
    )
  }

  return null
}
