// src/frontend/src/components/MessageBubble.tsx
import { memo } from 'react'
import { motion } from 'framer-motion'

type SystemProps = { kind: 'system'; displayText: string }
type AttackProps = {
  kind: 'attack'
  sender: string
  displayText: string
  damage: number
  isNpc: boolean
  isPending?: boolean
  myUsername: string
}
type RefereeProps = { kind: 'referee'; displayText: string }

type Props = SystemProps | AttackProps | RefereeProps

// Memoised: chat entries are immutable once added, so old bubbles need not
// re-render every time a new message extends the log.
function MessageBubble(props: Props) {
  if (props.kind === 'system') {
    return (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 0.85 }}
        className="text-[#a88a6d] text-xs font-mono tracking-[2px] text-center my-3 py-1 bg-ink/40 rounded-full border border-bark/10 max-w-sm mx-auto shadow-inner"
      >
        {props.displayText}
      </motion.div>
    )
  }

  if (props.kind === 'attack') {
    const { sender, displayText, damage, isNpc, isPending, myUsername } = props
    const isMe = sender === myUsername

    const avatarChar = sender.substring(0, 1).toUpperCase()

    // Determine avatar color gradient based on identity
    let avatarGradient = 'bg-gradient-to-br from-slate-600 to-zinc-800'
    if (isMe) {
      avatarGradient = 'bg-gradient-to-br from-[#ffae19] via-[#ff6f00] to-[#b33600]'
    } else if (isNpc) {
      avatarGradient = 'bg-gradient-to-br from-vermillion to-[#990000]'
    } else {
      avatarGradient = 'bg-gradient-to-br from-[#4b6cb7] to-[#182848]'
    }

    return (
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.25, ease: 'easeOut' }}
        className={`flex ${isMe ? 'flex-row-reverse' : 'flex-row'} items-start gap-3 w-full my-4`}
      >
        {/* User Avatar */}
        <div className={`w-9 h-9 rounded-full flex items-center justify-center font-display font-bold text-sm select-none flex-shrink-0 shadow-lg text-white border ${
          isMe ? 'border-[#ffb732]/30 shadow-[#ff6f00]/10' : 'border-[#a88a6d]/20 shadow-black/40'
        } ${avatarGradient}`}>
          {avatarChar}
        </div>

        {/* Bubble & Info Container */}
        <div className={`flex flex-col max-w-[72%] ${isMe ? 'items-end' : 'items-start'}`}>
          {/* Sender Name */}
          <span className={`text-[11px] text-[#a88a6d]/75 font-mono mb-1 tracking-wider ${isMe ? 'mr-1' : 'ml-1'}`}>
            {isMe ? '你' : sender}
          </span>

          {/* Chat Bubble */}
          <div className={`relative px-4 py-2.5 rounded-2xl text-sm md:text-base leading-relaxed break-words w-full shadow-lg ${
            isMe
              ? 'bg-[#2a2018] border border-[#ff8800]/30 text-white rounded-tr-none shadow-[#ff8800]/5'
              : 'bg-[#13110e] border border-[#a88a6d]/20 text-[#fff0d4] rounded-tl-none shadow-black/20'
          }`}>
            {displayText}
          </div>

          {/* Action/Damage indicator */}
          {!isPending ? (
            <div className={`text-xs mt-1.5 font-mono flex items-center gap-1.5 ${isMe ? 'text-amber-500 mr-1' : 'text-vermillion ml-1'}`}>
              {isMe ? (
                <>
                  <span className="text-[10px] filter drop-shadow">⚔️</span>
                  <span className="tracking-wide">造成 <strong className="text-white font-bold font-sans text-sm ml-0.5">{damage}</strong> 點傷害</span>
                </>
              ) : (
                <>
                  <span className="text-[10px] filter drop-shadow">💥</span>
                  <span className="tracking-wide">承受 <strong className="text-white font-bold font-sans text-sm ml-0.5">{damage}</strong> 點傷害</span>
                </>
              )}
            </div>
          ) : (
            <div className={`text-[11px] mt-1.5 font-mono flex items-center gap-2 text-[#a88a6d]/60 select-none ${isMe ? 'mr-1' : 'ml-1'}`}>
              <div className="flex space-x-1 items-center py-0.5">
                <span className="w-1.5 h-1.5 bg-[#a88a6d]/50 rounded-full animate-bounce [animation-delay:-0.3s]" />
                <span className="w-1.5 h-1.5 bg-[#a88a6d]/50 rounded-full animate-bounce [animation-delay:-0.15s]" />
                <span className="w-1.5 h-1.5 bg-[#a88a6d]/50 rounded-full animate-bounce" />
              </div>
              <span className="tracking-wider">等待裁決...</span>
            </div>
          )}
        </div>
      </motion.div>
    )
  }

  return null
}

export default memo(MessageBubble)
