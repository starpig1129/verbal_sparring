// src/frontend/src/components/DamageNumber.tsx
import { createPortal } from 'react-dom'
import { motion, AnimatePresence } from 'framer-motion'

type Props = { damageEvent: { damage: number; id: number; isCrit?: boolean } | null }

export default function DamageNumber({ damageEvent }: Props) {
  const isCrit = damageEvent?.isCrit ?? false

  return createPortal(
    <AnimatePresence>
      {damageEvent && (
        <motion.div
          key={damageEvent.id}
          initial={{ opacity: 1, y: 0, x: '-50%', scale: isCrit ? 1.6 : 1.2 }}
          animate={{ opacity: 0, y: -70, scale: 0.8 }}
          transition={{ duration: isCrit ? 1.1 : 0.8, ease: 'easeOut' }}
          className={`fixed left-1/2 top-1/3 font-display pointer-events-none z-50 ${
            isCrit ? 'text-[72px] text-red-500' : 'text-[56px] text-fire'
          }`}
          style={{
            textShadow: isCrit
              ? '0 0 30px rgba(255,30,30,0.8), 0 0 60px rgba(255,0,0,0.4)'
              : '0 0 20px rgba(255,80,0,0.6), 0 0 40px rgba(200,50,0,0.3)',
          }}
        >
          {isCrit && (
            <span className="block text-center text-lg tracking-[6px] text-red-400">暴擊！</span>
          )}
          -{damageEvent.damage}
        </motion.div>
      )}
    </AnimatePresence>,
    document.body
  )
}
