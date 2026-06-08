// src/frontend/src/components/AttackInput.tsx
import { useState, useRef } from 'react'
import type { AttackPayload } from '../types/game'

type Props = { onSend: (p: AttackPayload) => void; disabled: boolean }

export default function AttackInput({ onSend, disabled }: Props) {
  const [text, setText] = useState('')
  const fileRef = useRef<HTMLInputElement>(null)

  function handleSend() {
    if (!text.trim() || disabled) return
    onSend({ text })
    setText('')
  }

  function handleImage(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = () => onSend({ text, image: reader.result as string })
    reader.readAsDataURL(file)
    e.target.value = ''
  }

  return (
    <div className="bg-[#0f0e0b] border-t-2 border-[#4a3f28] px-4 py-4.5 flex gap-3 items-center flex-shrink-0">
      <span className="text-[#a88a6d] text-sm font-body font-bold flex-shrink-0">筆▶</span>
      <input
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => e.key === 'Enter' && handleSend()}
        placeholder="執筆出招，揮毫傷人..."
        disabled={disabled}
        className="flex-1 bg-[#080805] border border-[#4a3f28] border-b-2 border-b-vermillion px-4 py-2.5 text-white font-body text-sm placeholder:text-[#a88a6d]/50 focus:outline-none focus:border-vermillion focus:ring-1 focus:ring-vermillion/30 disabled:opacity-40 rounded"
      />
      <button
        onClick={() => fileRef.current?.click()}
        disabled={disabled}
        className="border border-[#4a3f28] text-[#e2d6be] px-3.5 py-2.5 text-base hover:text-white hover:border-vermillion bg-[#120f0a] transition-all duration-150 transform active:scale-95 disabled:opacity-40 rounded"
      >
        📷
      </button>
      <input ref={fileRef} type="file" accept="image/*" className="hidden" onChange={handleImage} />
      <button
        onClick={handleSend}
        disabled={disabled || !text.trim()}
        className="bg-vermillion hover:bg-fire text-white font-display text-xs md:text-sm tracking-[4px] px-6 py-2.5 shadow-[0_0_16px_rgba(204,51,0,0.3)] hover:shadow-[0_0_24px_rgba(204,51,0,0.5)] transition-all duration-150 transform active:scale-95 disabled:opacity-40 disabled:cursor-not-allowed rounded font-bold"
      >
        出手
      </button>
    </div>
  )
}
