// src/frontend/src/components/RefereeStamp.tsx
import { motion } from 'framer-motion'

type Props = { comment: string }

function Seal({ char }: { char: string }) {
  return (
    <div className="w-[24px] h-[24px] border-2 border-vermillion/60 flex items-center justify-center flex-shrink-0 rounded bg-vermillion/5">
      <span className="text-vermillion text-xs font-body font-bold">{char}</span>
    </div>
  )
}

export default function RefereeStamp({ comment }: Props) {
  return (
    <motion.div
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="flex items-center justify-center gap-3 my-2.5 py-1.5 border-t border-b border-vermillion/10"
    >
      <Seal char="判" />
      <span className="text-vermillion font-mono text-sm tracking-[2px] font-bold bg-vermillion/[0.04] px-4 py-1.5 border border-vermillion/20 rounded shadow-[inset_0_0_8px_rgba(255,51,0,0.03)]">{comment}</span>
      <Seal char="決" />
    </motion.div>
  )
}
