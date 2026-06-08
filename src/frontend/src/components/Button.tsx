// src/frontend/src/components/Button.tsx
import type { ButtonHTMLAttributes } from 'react'

export type ButtonVariant = 'primary-outline' | 'primary-solid' | 'secondary'

type Props = ButtonHTMLAttributes<HTMLButtonElement> & { variant?: ButtonVariant }

const styles: Record<ButtonVariant, string> = {
  'primary-outline': 'border-2 border-vermillion text-vermillion bg-ink shadow-[0_0_12px_rgba(204,51,0,0.2)] hover:shadow-[0_0_20px_rgba(204,51,0,0.4)] disabled:opacity-40 disabled:cursor-not-allowed',
  'primary-solid': 'bg-vermillion text-white shadow-[0_0_16px_rgba(204,51,0,0.4)] hover:bg-fire disabled:opacity-40 disabled:cursor-not-allowed',
  'secondary': 'border border-bamboo text-bark hover:text-aged disabled:opacity-40 disabled:cursor-not-allowed',
}

export default function Button({ variant = 'primary-outline', className = '', children, ...props }: Props) {
  return (
    <button
      className={`font-display font-black tracking-[3px] uppercase text-[11px] px-4 py-2 transition-all duration-150 ${styles[variant]} ${className}`}
      {...props}
    >
      {children}
    </button>
  )
}
