// src/frontend/src/components/ChatLog.tsx
import { useEffect, useRef, useState } from 'react'
import type { ChatEntry } from '../types/game'
import MessageBubble from './MessageBubble'
import RefereeStamp from './RefereeStamp'

type Props = { entries: ChatEntry[]; myUsername: string; npcName?: string }

// Long battles (and restored histories) can hold hundreds of entries; only
// the most recent slice is rendered unless the player asks for the rest.
const VISIBLE_LIMIT = 200

export default function ChatLog({ entries, myUsername, npcName }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null)
  const [showAll, setShowAll] = useState(false)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [entries])

  const hidden = !showAll && entries.length > VISIBLE_LIMIT
  const visible = hidden ? entries.slice(-VISIBLE_LIMIT) : entries

  return (
    <div className="flex-1 overflow-y-auto px-4 py-3 bg-[#060502]" style={{ minHeight: 0 }}>
      {hidden && (
        <button
          onClick={() => setShowAll(true)}
          className="block mx-auto mb-3 font-mono text-xs text-[#a88a6d] hover:text-white border border-[#4a3f28] hover:border-vermillion bg-[#120f0a] px-4 py-1.5 rounded-full tracking-[2px] transition-all cursor-pointer"
        >
          顯示更早的 {entries.length - VISIBLE_LIMIT} 則訊息
        </button>
      )}
      {visible.map((e) => {
        if (e.kind === 'system') return <MessageBubble key={e.id} kind="system" displayText={e.displayText} />
        if (e.kind === 'attack') return <MessageBubble key={e.id} kind="attack" sender={e.isNpc && npcName ? npcName : e.sender} displayText={e.displayText} damage={e.damage} isNpc={e.isNpc} isPending={e.isPending} isCrit={e.isCrit} combo={e.combo} myUsername={myUsername} />
        if (e.kind === 'referee') return <RefereeStamp key={e.id} comment={e.displayText} />
        return null
      })}
      <div ref={bottomRef} />
    </div>
  )
}
