// src/frontend/src/components/ChatLog.tsx
import { useEffect, useRef } from 'react'
import type { ChatEntry } from '../types/game'
import MessageBubble from './MessageBubble'
import RefereeStamp from './RefereeStamp'

type Props = { entries: ChatEntry[]; myUsername: string }

export default function ChatLog({ entries, myUsername }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [entries])

  return (
    <div className="flex-1 overflow-y-auto px-4 py-3 bg-[#060502]" style={{ minHeight: 0 }}>
      {entries.map((e) => {
        if (e.kind === 'system') return <MessageBubble key={e.id} kind="system" displayText={e.displayText} />
        if (e.kind === 'attack') return <MessageBubble key={e.id} kind="attack" sender={e.sender} displayText={e.displayText} damage={e.damage} isNpc={e.isNpc} isPending={e.isPending} myUsername={myUsername} />
        if (e.kind === 'referee') return <RefereeStamp key={e.id} comment={e.displayText} />
        return null
      })}
      <div ref={bottomRef} />
    </div>
  )
}
