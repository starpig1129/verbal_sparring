// src/frontend/src/components/AttackInput.tsx
import { useState, useRef } from 'react'
import type { AttackPayload } from '../types/game'

type Props = { onSend: (p: AttackPayload) => void; disabled: boolean }

// Vision models don't benefit beyond ~768px, and raw phone photos are
// multi-MB base64 blobs that bloat the WS message, the prompt, and the DB.
const MAX_IMAGE_EDGE = 768
const JPEG_QUALITY = 0.8

function compressImage(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file)
    const img = new Image()
    img.onload = () => {
      URL.revokeObjectURL(url)
      const scale = Math.min(1, MAX_IMAGE_EDGE / Math.max(img.width, img.height))
      const canvas = document.createElement('canvas')
      canvas.width = Math.round(img.width * scale)
      canvas.height = Math.round(img.height * scale)
      const ctx = canvas.getContext('2d')
      if (!ctx) {
        reject(new Error('canvas unavailable'))
        return
      }
      ctx.drawImage(img, 0, 0, canvas.width, canvas.height)
      resolve(canvas.toDataURL('image/jpeg', JPEG_QUALITY))
    }
    img.onerror = () => {
      URL.revokeObjectURL(url)
      reject(new Error('image load failed'))
    }
    img.src = url
  })
}

export default function AttackInput({ onSend, disabled }: Props) {
  const [text, setText] = useState('')
  const fileRef = useRef<HTMLInputElement>(null)

  function handleSend() {
    if (!text.trim() || disabled) return
    onSend({ text })
    setText('')
  }

  async function handleImage(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    e.target.value = ''
    if (!file) return
    const currentText = text
    setText('')
    try {
      const image = await compressImage(file)
      onSend({ text: currentText, image })
    } catch {
      // Fall back to the raw file if canvas compression fails
      const reader = new FileReader()
      reader.onload = () => onSend({ text: currentText, image: reader.result as string })
      reader.readAsDataURL(file)
    }
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
