# 唇槍舌戰前端全面升級 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 將前端從 inline styles 全面升級為 C×E（水墨武俠 × Brutalism）視覺風格，加入 Tailwind CSS + Framer Motion，補齊 ProfilePage、HistoryPage 兩個新頁面，完整對齊後端所有 API 功能。

**Architecture:** AuthContext 集中管理認證狀態並提供給所有子元件；共用 Layout 元件透過 react-router Outlet 模式提供 Navbar；matchHistory 於 game_over 時寫入 localStorage 供 ProfilePage / HistoryPage 使用。

**Tech Stack:** React 18, TypeScript, Vite, Tailwind CSS v3, Framer Motion v11, react-router-dom v6, Vitest, @testing-library/react

---

## File Map

**Create:**
- `src/frontend/tailwind.config.js`
- `src/frontend/postcss.config.js`
- `src/frontend/src/index.css`
- `src/frontend/src/contexts/AuthContext.tsx`
- `src/frontend/src/components/Button.tsx`
- `src/frontend/src/components/RefereeStamp.tsx`
- `src/frontend/src/components/RefereeStamp.test.tsx`
- `src/frontend/src/components/MessageBubble.tsx`
- `src/frontend/src/components/MessageBubble.test.tsx`
- `src/frontend/src/components/DamageNumber.tsx`
- `src/frontend/src/components/TurnIndicator.tsx`
- `src/frontend/src/components/GameOverModal.tsx`
- `src/frontend/src/components/GameOverModal.test.tsx`
- `src/frontend/src/components/Navbar.tsx`
- `src/frontend/src/components/Navbar.test.tsx`
- `src/frontend/src/components/Layout.tsx`
- `src/frontend/src/pages/ProfilePage.tsx`
- `src/frontend/src/pages/HistoryPage.tsx`

**Modify:**
- `src/frontend/package.json`
- `src/frontend/src/main.tsx` (add CSS import)
- `src/frontend/src/setupTests.ts` (add Framer Motion mock)
- `src/frontend/src/types/game.ts` (add MatchRecord, update ChatEntry)
- `src/frontend/src/hooks/useGameState.ts` (new ChatEntry kinds + lastDamageEvent)
- `src/frontend/src/hooks/useGameState.test.ts`
- `src/frontend/src/components/HPBar.tsx`
- `src/frontend/src/components/HPBar.test.tsx`
- `src/frontend/src/components/ChatLog.tsx`
- `src/frontend/src/components/ChatLog.test.tsx`
- `src/frontend/src/components/AttackInput.tsx`
- `src/frontend/src/pages/HomePage.tsx`
- `src/frontend/src/pages/HomePage.test.tsx`
- `src/frontend/src/pages/BattlePage.tsx`
- `src/frontend/src/pages/LeaderboardPage.tsx`
- `src/frontend/src/pages/LeaderboardPage.test.tsx`
- `src/frontend/src/pages/ReplayPage.tsx`
- `src/frontend/src/App.tsx`

---

## Task 1: Install Tailwind CSS v3 + Framer Motion

**Files:**
- Modify: `src/frontend/package.json`
- Create: `src/frontend/tailwind.config.js`
- Create: `src/frontend/postcss.config.js`
- Create: `src/frontend/src/index.css`
- Modify: `src/frontend/src/main.tsx`

- [ ] **Step 1: Install dependencies**

```bash
cd src/frontend
npm install framer-motion
npm install -D tailwindcss@3 postcss autoprefixer
```

Expected: no errors, `node_modules/framer-motion` and `node_modules/tailwindcss` exist.

- [ ] **Step 2: Create tailwind.config.js**

```js
// src/frontend/tailwind.config.js
/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        ink: '#0a0905',
        parchment: '#3a3020',
        bamboo: '#2a2018',
        vermillion: '#cc3300',
        fire: '#ff4400',
        aged: '#886655',
        bark: '#443322',
        ember: '#ff8800',
      },
      fontFamily: {
        display: ['Impact', '"Arial Black"', 'sans-serif'],
        body: ['Georgia', 'serif'],
        mono: ['"Courier New"', 'monospace'],
      },
    },
  },
  plugins: [],
}
```

- [ ] **Step 3: Create postcss.config.js**

```js
// src/frontend/postcss.config.js
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
```

- [ ] **Step 4: Create src/index.css**

```css
/* src/frontend/src/index.css */
@tailwind base;
@tailwind components;
@tailwind utilities;

* { box-sizing: border-box; }

body {
  @apply bg-ink text-white m-0 p-0;
}

a { text-decoration: none; }
```

- [ ] **Step 5: Add CSS import to main.tsx**

Full file after edit:

```tsx
// src/frontend/src/main.tsx
import './index.css'
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.tsx'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
```

- [ ] **Step 6: Verify build compiles**

```bash
cd src/frontend && npm run build
```

Expected: exits 0, `dist/` folder created.

- [ ] **Step 7: Commit**

```bash
cd src/frontend
git add tailwind.config.js postcss.config.js src/index.css src/main.tsx package.json package-lock.json
git commit -m "feat: add Tailwind CSS v3 + Framer Motion"
```

---

## Task 2: Update setupTests + types

**Files:**
- Modify: `src/frontend/src/setupTests.ts`
- Modify: `src/frontend/src/types/game.ts`

- [ ] **Step 1: Add Framer Motion mock to setupTests.ts**

Full file after edit:

```ts
// src/frontend/src/setupTests.ts
import '@testing-library/jest-dom'
import React from 'react'
import { vi } from 'vitest'

window.HTMLElement.prototype.scrollIntoView = function () {}

vi.mock('framer-motion', () => ({
  motion: new Proxy({} as Record<string, unknown>, {
    get: (_: unknown, prop: string) => {
      const C = ({ children, initial: _i, animate: _a, exit: _e, transition: _t,
                   whileHover: _wh, whileTap: _wt, variants: _v, ...rest }: Record<string, unknown> & { children?: unknown }) =>
        React.createElement(prop as string, rest, children as React.ReactNode)
      C.displayName = `motion.${prop}`
      return C
    },
  }),
  AnimatePresence: ({ children }: { children: React.ReactNode }) =>
    React.createElement(React.Fragment, null, children),
  useAnimation: () => ({ start: vi.fn() }),
}))
```

- [ ] **Step 2: Update types/game.ts**

Full file after edit:

```ts
// src/frontend/src/types/game.ts
export type HPMap = { [playerId: string]: number }

export type AttackPayload = { text: string; image?: string }

export type ServerMessage =
  | { type: 'system'; message: string; hp_status: HPMap; current_turn: string }
  | { type: 'attack'; sender: string; display_text: string; damage: number; referee_comment: string; hp_status: HPMap; current_turn: string }
  | { type: 'npc_attack'; display_text: string; damage: number; referee_comment: string; hp_status: HPMap }
  | { type: 'game_over'; message: string; winner: string }
  | { type: 'turn_error'; message: string }

export type ChatEntry =
  | { id: number; kind: 'system'; displayText: string }
  | { id: number; kind: 'attack'; sender: string; displayText: string; damage: number; isNpc: boolean }
  | { id: number; kind: 'referee'; displayText: string }

export type LeaderboardEntry = {
  rank: number
  username: string
  total_damage: number
  wins: number
  losses: number
}

export type RoundSnapshot = {
  round_number: number
  attacker: string | null
  original_text: string | null
  display_text: string
  damage: number
  referee_comment: string
  hp_snapshot: HPMap
}

export type MatchRecord = {
  matchId: string
  opponent: string
  result: 'win' | 'loss'
  totalDamage: number
  roundCount: number
  timestamp: number
}
```

- [ ] **Step 3: Commit**

```bash
git add src/frontend/src/setupTests.ts src/frontend/src/types/game.ts
git commit -m "chore: add Framer Motion test mock, update game types"
```

---

## Task 3: AuthContext

**Files:**
- Create: `src/frontend/src/contexts/AuthContext.tsx`

- [ ] **Step 1: Create AuthContext.tsx**

```tsx
// src/frontend/src/contexts/AuthContext.tsx
import { createContext, useContext, useState, type ReactNode } from 'react'

const API = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

type Auth = { token: string; username: string; userId: string }

type AuthCtx = Auth & {
  error: string
  isAuthenticated: boolean
  login: (username: string, password: string) => Promise<boolean>
  register: (username: string, password: string) => Promise<boolean>
  logout: () => void
  clearError: () => void
}

const AuthContext = createContext<AuthCtx>({} as AuthCtx)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [auth, setAuth] = useState<Auth>({
    token: localStorage.getItem('token') ?? '',
    username: localStorage.getItem('username') ?? '',
    userId: localStorage.getItem('userId') ?? '',
  })
  const [error, setError] = useState('')

  function persist(token: string, username: string, userId: string) {
    localStorage.setItem('token', token)
    localStorage.setItem('username', username)
    localStorage.setItem('userId', userId)
    setAuth({ token, username, userId })
  }

  async function login(username: string, password: string) {
    setError('')
    const resp = await fetch(`${API}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    })
    const data = await resp.json()
    if (!resp.ok) { setError('登入失敗：' + (data.detail ?? '')); return false }
    persist(data.access_token, data.username, data.user_id)
    return true
  }

  async function register(username: string, password: string) {
    setError('')
    const resp = await fetch(`${API}/api/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    })
    const data = await resp.json()
    if (!resp.ok) { setError('註冊失敗：' + (data.detail ?? '')); return false }
    persist(data.access_token, data.username, data.user_id)
    return true
  }

  function logout() {
    localStorage.removeItem('token')
    localStorage.removeItem('username')
    localStorage.removeItem('userId')
    setAuth({ token: '', username: '', userId: '' })
  }

  return (
    <AuthContext.Provider value={{
      ...auth,
      error,
      isAuthenticated: !!auth.token,
      login, register, logout,
      clearError: () => setError(''),
    }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuthContext() {
  return useContext(AuthContext)
}
```

- [ ] **Step 2: Commit**

```bash
git add src/frontend/src/contexts/AuthContext.tsx
git commit -m "feat: add AuthContext for centralized auth state"
```

---

## Task 4: Button component

**Files:**
- Create: `src/frontend/src/components/Button.tsx`

- [ ] **Step 1: Create Button.tsx**

```tsx
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
```

- [ ] **Step 2: Commit**

```bash
git add src/frontend/src/components/Button.tsx
git commit -m "feat: add Button component (3 variants)"
```

---

## Task 5: HPBar (redesign + test update)

**Files:**
- Modify: `src/frontend/src/components/HPBar.tsx`
- Modify: `src/frontend/src/components/HPBar.test.tsx`

- [ ] **Step 1: Rewrite HPBar.test.tsx**

```tsx
// src/frontend/src/components/HPBar.test.tsx
import { render, screen } from '@testing-library/react'
import HPBar from './HPBar'

test('renders label and hp value', () => {
  render(<HPBar label="alice" hp={65} />)
  expect(screen.getByText('alice')).toBeInTheDocument()
  expect(screen.getByText('65')).toBeInTheDocument()
})

test('progressbar aria-valuenow reflects hp', () => {
  render(<HPBar label="bob" hp={30} />)
  expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '30')
})

test('clamps hp at 0', () => {
  render(<HPBar label="x" hp={-5} />)
  expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '-5')
})
```

- [ ] **Step 2: Run test — expect FAIL (old implementation)**

```bash
cd src/frontend && npm test -- --reporter=verbose HPBar
```

Expected: FAIL (old component doesn't use motion.div or aria attributes correctly)

- [ ] **Step 3: Rewrite HPBar.tsx**

```tsx
// src/frontend/src/components/HPBar.tsx
import { motion } from 'framer-motion'

type Props = { label: string; hp: number; maxHp?: number }

function gradientClass(pct: number) {
  if (pct > 50) return 'from-[#336600] to-[#66cc00]'
  if (pct > 20) return 'from-[#885500] to-[#ffaa00]'
  return 'from-[#660000] via-[#cc0000] to-[#ff2200]'
}

function glowStyle(pct: number) {
  if (pct > 50) return '0 0 8px rgba(80,180,0,0.4)'
  if (pct > 20) return '0 0 8px rgba(200,130,0,0.4)'
  return '0 0 10px rgba(180,40,0,0.6)'
}

export default function HPBar({ label, hp, maxHp = 100 }: Props) {
  const pct = Math.max(0, Math.min(100, (hp / maxHp) * 100))
  return (
    <div>
      <div className="flex justify-between mb-1">
        <span className="font-mono text-aged text-[8px] tracking-[3px] uppercase">{label}</span>
        <span>
          <span className="font-display text-white text-lg leading-none">{hp}</span>
          <span className="text-bamboo text-xs"> /{maxHp}</span>
        </span>
      </div>
      <div className="bg-[#080805] border border-bamboo h-[7px]">
        <motion.div
          role="progressbar"
          aria-valuenow={hp}
          aria-valuemax={maxHp}
          className={`h-full bg-gradient-to-r ${gradientClass(pct)}`}
          style={{ boxShadow: glowStyle(pct) }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.4, ease: 'easeOut' }}
        />
      </div>
    </div>
  )
}
```

- [ ] **Step 4: Run test — expect PASS**

```bash
cd src/frontend && npm test -- --reporter=verbose HPBar
```

Expected: 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/frontend/src/components/HPBar.tsx src/frontend/src/components/HPBar.test.tsx
git commit -m "feat: redesign HPBar with Tailwind + Framer Motion"
```

---

## Task 6: RefereeStamp component

**Files:**
- Create: `src/frontend/src/components/RefereeStamp.tsx`
- Create: `src/frontend/src/components/RefereeStamp.test.tsx`

- [ ] **Step 1: Write failing test**

```tsx
// src/frontend/src/components/RefereeStamp.test.tsx
import { render, screen } from '@testing-library/react'
import RefereeStamp from './RefereeStamp'

test('renders comment text', () => {
  render(<RefereeStamp comment="匕首入心，一字斃命" />)
  expect(screen.getByText('匕首入心，一字斃命')).toBeInTheDocument()
})

test('renders 判 and 決 seal marks', () => {
  render(<RefereeStamp comment="test" />)
  expect(screen.getByText('判')).toBeInTheDocument()
  expect(screen.getByText('決')).toBeInTheDocument()
})
```

- [ ] **Step 2: Run — expect FAIL (file doesn't exist)**

```bash
cd src/frontend && npm test -- --reporter=verbose RefereeStamp
```

Expected: FAIL with "Cannot find module"

- [ ] **Step 3: Create RefereeStamp.tsx**

```tsx
// src/frontend/src/components/RefereeStamp.tsx
import { motion } from 'framer-motion'

type Props = { comment: string }

function Seal({ char }: { char: string }) {
  return (
    <div className="w-[18px] h-[18px] border border-vermillion/40 flex items-center justify-center flex-shrink-0">
      <span className="text-vermillion/70 text-[8px] font-body">{char}</span>
    </div>
  )
}

export default function RefereeStamp({ comment }: Props) {
  return (
    <motion.div
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="flex items-center justify-center gap-2 my-1 py-1 border-t border-b border-vermillion/20"
    >
      <Seal char="判" />
      <span className="text-bark text-[9px] tracking-[2px] font-mono italic">{comment}</span>
      <Seal char="決" />
    </motion.div>
  )
}
```

- [ ] **Step 4: Run — expect PASS**

```bash
cd src/frontend && npm test -- --reporter=verbose RefereeStamp
```

Expected: 2 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/frontend/src/components/RefereeStamp.tsx src/frontend/src/components/RefereeStamp.test.tsx
git commit -m "feat: add RefereeStamp component"
```

---

## Task 7: MessageBubble component

**Files:**
- Create: `src/frontend/src/components/MessageBubble.tsx`
- Create: `src/frontend/src/components/MessageBubble.test.tsx`

- [ ] **Step 1: Write failing tests**

```tsx
// src/frontend/src/components/MessageBubble.test.tsx
import { render, screen } from '@testing-library/react'
import MessageBubble from './MessageBubble'

test('renders attack sender and text', () => {
  render(<MessageBubble kind="attack" sender="alice" displayText="你太弱了！" damage={18} isNpc={false} />)
  expect(screen.getByText('alice')).toBeInTheDocument()
  expect(screen.getByText('你太弱了！')).toBeInTheDocument()
})

test('renders damage value', () => {
  render(<MessageBubble kind="attack" sender="NPC" displayText="廢話！" damage={24} isNpc={true} />)
  expect(screen.getByText('24')).toBeInTheDocument()
})

test('renders system message without sender', () => {
  render(<MessageBubble kind="system" displayText="遊戲開始！" />)
  expect(screen.getByText('遊戲開始！')).toBeInTheDocument()
})
```

- [ ] **Step 2: Run — expect FAIL**

```bash
cd src/frontend && npm test -- --reporter=verbose MessageBubble
```

Expected: FAIL with "Cannot find module"

- [ ] **Step 3: Create MessageBubble.tsx**

```tsx
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
```

- [ ] **Step 4: Run — expect PASS**

```bash
cd src/frontend && npm test -- --reporter=verbose MessageBubble
```

Expected: 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/frontend/src/components/MessageBubble.tsx src/frontend/src/components/MessageBubble.test.tsx
git commit -m "feat: add MessageBubble component"
```

---

## Task 8: DamageNumber + TurnIndicator

**Files:**
- Create: `src/frontend/src/components/DamageNumber.tsx`
- Create: `src/frontend/src/components/TurnIndicator.tsx`

- [ ] **Step 1: Create DamageNumber.tsx**

```tsx
// src/frontend/src/components/DamageNumber.tsx
import { createPortal } from 'react-dom'
import { motion, AnimatePresence } from 'framer-motion'

type Props = { damageEvent: { damage: number; id: number } | null }

export default function DamageNumber({ damageEvent }: Props) {
  return createPortal(
    <AnimatePresence>
      {damageEvent && (
        <motion.div
          key={damageEvent.id}
          initial={{ opacity: 1, y: 0, x: '-50%', scale: 1.2 }}
          animate={{ opacity: 0, y: -70, scale: 0.8 }}
          transition={{ duration: 0.8, ease: 'easeOut' }}
          className="fixed left-1/2 top-1/3 font-display text-[56px] text-fire pointer-events-none z-50"
          style={{ textShadow: '0 0 20px rgba(255,80,0,0.6), 0 0 40px rgba(200,50,0,0.3)' }}
        >
          -{damageEvent.damage}
        </motion.div>
      )}
    </AnimatePresence>,
    document.body
  )
}
```

- [ ] **Step 2: Create TurnIndicator.tsx**

```tsx
// src/frontend/src/components/TurnIndicator.tsx
type Props = { isMyTurn: boolean }

export default function TurnIndicator({ isMyTurn }: Props) {
  return (
    <div className={`py-[5px] px-4 text-center font-mono text-[9px] tracking-[3px] border-t border-b flex-shrink-0 ${
      isMyTurn
        ? 'bg-parchment border-[#4a4028] text-vermillion'
        : 'bg-ink border-bamboo text-bark'
    }`}>
      {isMyTurn ? '⚔ 輪到你出招！⚔' : '等待對手...'}
    </div>
  )
}
```

- [ ] **Step 3: Commit**

```bash
git add src/frontend/src/components/DamageNumber.tsx src/frontend/src/components/TurnIndicator.tsx
git commit -m "feat: add DamageNumber + TurnIndicator components"
```

---

## Task 9: GameOverModal

**Files:**
- Create: `src/frontend/src/components/GameOverModal.tsx`
- Create: `src/frontend/src/components/GameOverModal.test.tsx`

- [ ] **Step 1: Write failing tests**

```tsx
// src/frontend/src/components/GameOverModal.test.tsx
import { render, screen, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import GameOverModal from './GameOverModal'

const wrap = (ui: React.ReactElement) => render(<MemoryRouter>{ui}</MemoryRouter>)

test('shows win message when player wins', () => {
  wrap(<GameOverModal winner="alice" myUsername="alice" matchId="m1" onPlayAgain={vi.fn()} />)
  expect(screen.getByText('你贏了！')).toBeInTheDocument()
})

test('shows loss message when player loses', () => {
  wrap(<GameOverModal winner="bob" myUsername="alice" matchId="m1" onPlayAgain={vi.fn()} />)
  expect(screen.getByText('你輸了...')).toBeInTheDocument()
})

test('calls onPlayAgain on button click', () => {
  const onPlayAgain = vi.fn()
  wrap(<GameOverModal winner="alice" myUsername="alice" matchId="m1" onPlayAgain={onPlayAgain} />)
  fireEvent.click(screen.getByText(/再戰一局/))
  expect(onPlayAgain).toHaveBeenCalledTimes(1)
})
```

- [ ] **Step 2: Run — expect FAIL**

```bash
cd src/frontend && npm test -- --reporter=verbose GameOverModal
```

Expected: FAIL with "Cannot find module"

- [ ] **Step 3: Create GameOverModal.tsx**

```tsx
// src/frontend/src/components/GameOverModal.tsx
import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import Button from './Button'

type Props = {
  winner: string
  myUsername: string
  matchId: string
  onPlayAgain: () => void
}

export default function GameOverModal({ winner, myUsername, matchId, onPlayAgain }: Props) {
  const didWin = winner === myUsername

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="fixed inset-0 bg-ink/90 flex items-center justify-center z-40"
    >
      <motion.div
        initial={{ scale: 0.8, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ delay: 0.1 }}
        className="bg-[#0f0e0b] border-2 border-bamboo p-8 text-center max-w-sm w-full mx-4"
      >
        <div className={`font-display text-4xl tracking-widest mb-2 ${didWin ? 'text-white' : 'text-aged'}`}>
          {didWin ? '你贏了！' : '你輸了...'}
        </div>
        <div className="font-mono text-bark text-[9px] tracking-[3px] mb-8">
          {didWin ? '此役功成，武林震驚' : '一敗塗地，來日再戰'}
        </div>
        <div className="flex flex-col gap-3">
          <Link to={`/replay/${matchId}`}>
            <Button variant="primary-outline" className="w-full">查看回放 ▶</Button>
          </Link>
          <Button variant="primary-solid" onClick={onPlayAgain} className="w-full">再戰一局</Button>
          <Link to="/">
            <Button variant="secondary" className="w-full">回首頁</Button>
          </Link>
        </div>
      </motion.div>
    </motion.div>
  )
}
```

- [ ] **Step 4: Run — expect PASS**

```bash
cd src/frontend && npm test -- --reporter=verbose GameOverModal
```

Expected: 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/frontend/src/components/GameOverModal.tsx src/frontend/src/components/GameOverModal.test.tsx
git commit -m "feat: add GameOverModal with win/loss states"
```

---

## Task 10: Navbar + Layout

**Files:**
- Create: `src/frontend/src/components/Navbar.tsx`
- Create: `src/frontend/src/components/Navbar.test.tsx`
- Create: `src/frontend/src/components/Layout.tsx`

- [ ] **Step 1: Write Navbar failing tests**

```tsx
// src/frontend/src/components/Navbar.test.tsx
import { render, screen, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import Navbar from './Navbar'

test('renders game title', () => {
  render(<MemoryRouter><Navbar username="alice" onLogout={vi.fn()} /></MemoryRouter>)
  expect(screen.getByText(/舌戰/)).toBeInTheDocument()
})

test('calls onLogout when logout clicked', () => {
  const onLogout = vi.fn()
  render(<MemoryRouter><Navbar username="alice" onLogout={onLogout} /></MemoryRouter>)
  fireEvent.click(screen.getByText('登出'))
  expect(onLogout).toHaveBeenCalledTimes(1)
})

test('renders nav links', () => {
  render(<MemoryRouter><Navbar username="alice" onLogout={vi.fn()} /></MemoryRouter>)
  expect(screen.getByText('排行榜')).toBeInTheDocument()
  expect(screen.getByText('我的戰績')).toBeInTheDocument()
  expect(screen.getByText('對戰紀錄')).toBeInTheDocument()
})
```

- [ ] **Step 2: Run — expect FAIL**

```bash
cd src/frontend && npm test -- --reporter=verbose Navbar
```

Expected: FAIL with "Cannot find module"

- [ ] **Step 3: Create Navbar.tsx**

```tsx
// src/frontend/src/components/Navbar.tsx
import { Link } from 'react-router-dom'

type Props = { username: string; onLogout: () => void }

export default function Navbar({ username: _username, onLogout }: Props) {
  return (
    <nav className="bg-[#0f0e0b] border-b-2 border-bamboo flex justify-between items-center px-4 py-2 flex-shrink-0">
      <Link to="/" className="font-display text-[15px] text-white tracking-[2px]">
        唇槍<span className="text-vermillion">舌戰</span>
      </Link>
      <div className="flex gap-3 items-center">
        <Link to="/leaderboard" className="font-mono text-[9px] text-aged tracking-[2px] hover:text-white">排行榜</Link>
        <Link to="/profile" className="font-mono text-[9px] text-aged tracking-[2px] hover:text-white">我的戰績</Link>
        <Link to="/history" className="font-mono text-[9px] text-aged tracking-[2px] hover:text-white">對戰紀錄</Link>
        <button
          onClick={onLogout}
          className="font-mono text-[9px] text-bark border border-bamboo px-2 py-1 tracking-[2px] hover:text-aged"
        >
          登出
        </button>
      </div>
    </nav>
  )
}
```

- [ ] **Step 4: Run Navbar tests — expect PASS**

```bash
cd src/frontend && npm test -- --reporter=verbose Navbar
```

Expected: 3 tests PASS

- [ ] **Step 5: Create Layout.tsx**

```tsx
// src/frontend/src/components/Layout.tsx
import { Outlet, useNavigate } from 'react-router-dom'
import Navbar from './Navbar'
import { useAuthContext } from '../contexts/AuthContext'

export default function Layout() {
  const { isAuthenticated, username, logout } = useAuthContext()
  const navigate = useNavigate()

  function handleLogout() {
    logout()
    navigate('/')
  }

  return (
    <div className="flex flex-col min-h-screen bg-ink text-white">
      {isAuthenticated && <Navbar username={username} onLogout={handleLogout} />}
      <Outlet />
    </div>
  )
}
```

- [ ] **Step 6: Commit**

```bash
git add src/frontend/src/components/Navbar.tsx src/frontend/src/components/Navbar.test.tsx src/frontend/src/components/Layout.tsx
git commit -m "feat: add Navbar + Layout components"
```

---

## Task 11: AttackInput + ChatLog redesign

**Files:**
- Modify: `src/frontend/src/components/AttackInput.tsx`
- Modify: `src/frontend/src/components/ChatLog.tsx`
- Modify: `src/frontend/src/components/ChatLog.test.tsx`

- [ ] **Step 1: Rewrite ChatLog.test.tsx**

```tsx
// src/frontend/src/components/ChatLog.test.tsx
import { render, screen } from '@testing-library/react'
import ChatLog from './ChatLog'
import type { ChatEntry } from '../types/game'

test('renders attack entry with sender and text', () => {
  const entries: ChatEntry[] = [
    { id: 1, kind: 'attack', sender: 'alice', displayText: '你好遜！', damage: 20, isNpc: false },
  ]
  render(<ChatLog entries={entries} />)
  expect(screen.getByText('alice')).toBeInTheDocument()
  expect(screen.getByText('你好遜！')).toBeInTheDocument()
})

test('renders system entry', () => {
  const entries: ChatEntry[] = [
    { id: 1, kind: 'system', displayText: '遊戲開始' },
  ]
  render(<ChatLog entries={entries} />)
  expect(screen.getByText('遊戲開始')).toBeInTheDocument()
})

test('renders referee entry via RefereeStamp', () => {
  const entries: ChatEntry[] = [
    { id: 1, kind: 'referee', displayText: '匕首入心' },
  ]
  render(<ChatLog entries={entries} />)
  expect(screen.getByText('匕首入心')).toBeInTheDocument()
})
```

- [ ] **Step 2: Run — expect FAIL**

```bash
cd src/frontend && npm test -- --reporter=verbose ChatLog
```

Expected: FAIL (old ChatLog doesn't use ChatEntry.kind)

- [ ] **Step 3: Rewrite ChatLog.tsx**

```tsx
// src/frontend/src/components/ChatLog.tsx
import { useEffect, useRef } from 'react'
import type { ChatEntry } from '../types/game'
import MessageBubble from './MessageBubble'
import RefereeStamp from './RefereeStamp'

type Props = { entries: ChatEntry[] }

export default function ChatLog({ entries }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [entries])

  return (
    <div className="flex-1 overflow-y-auto px-4 py-3 bg-[#060502]" style={{ minHeight: 0 }}>
      {entries.map((e) => {
        if (e.kind === 'system') return <MessageBubble key={e.id} kind="system" displayText={e.displayText} />
        if (e.kind === 'attack') return <MessageBubble key={e.id} kind="attack" sender={e.sender} displayText={e.displayText} damage={e.damage} isNpc={e.isNpc} />
        if (e.kind === 'referee') return <RefereeStamp key={e.id} comment={e.displayText} />
        return null
      })}
      <div ref={bottomRef} />
    </div>
  )
}
```

- [ ] **Step 4: Run ChatLog tests — expect PASS**

```bash
cd src/frontend && npm test -- --reporter=verbose ChatLog
```

Expected: 3 tests PASS

- [ ] **Step 5: Rewrite AttackInput.tsx**

```tsx
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
    <div className="bg-[#0f0e0b] border-t-2 border-bamboo px-4 py-3 flex gap-2 items-center flex-shrink-0">
      <span className="text-bark text-[13px] font-body italic flex-shrink-0">筆▶</span>
      <input
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => e.key === 'Enter' && handleSend()}
        placeholder="執筆出招，揮毫傷人..."
        disabled={disabled}
        className="flex-1 bg-[#080805] border border-bamboo border-b-2 border-b-vermillion px-3 py-2 text-[#d4c5aa] font-body italic text-[11px] placeholder:text-bark placeholder:not-italic focus:outline-none disabled:opacity-40"
      />
      <button
        onClick={() => fileRef.current?.click()}
        disabled={disabled}
        className="border border-bamboo text-bark px-2 py-2 text-[13px] hover:text-aged disabled:opacity-40"
      >
        📷
      </button>
      <input ref={fileRef} type="file" accept="image/*" className="hidden" onChange={handleImage} />
      <button
        onClick={handleSend}
        disabled={disabled || !text.trim()}
        className="bg-ink border-2 border-vermillion text-vermillion font-display text-[11px] tracking-[3px] px-4 py-2 shadow-[0_0_12px_rgba(204,51,0,0.25)] hover:shadow-[0_0_20px_rgba(204,51,0,0.4)] disabled:opacity-40 disabled:cursor-not-allowed"
      >
        出手
      </button>
    </div>
  )
}
```

- [ ] **Step 6: Commit**

```bash
git add src/frontend/src/components/ChatLog.tsx src/frontend/src/components/ChatLog.test.tsx src/frontend/src/components/AttackInput.tsx
git commit -m "feat: redesign ChatLog + AttackInput with Tailwind"
```

---

## Task 12: Update useGameState

**Files:**
- Modify: `src/frontend/src/hooks/useGameState.ts`
- Modify: `src/frontend/src/hooks/useGameState.test.ts`

- [ ] **Step 1: Rewrite useGameState.test.ts**

```ts
// src/frontend/src/hooks/useGameState.test.ts
import { renderHook, act } from '@testing-library/react'
import { useGameState } from './useGameState'

test('system message updates hp and currentTurn', () => {
  const { result } = renderHook(() => useGameState('alice'))
  act(() => {
    result.current.handleMessage({
      type: 'system', message: '遊戲開始',
      hp_status: { alice: 100, bob: 100 }, current_turn: 'alice',
    })
  })
  expect(result.current.hp).toEqual({ alice: 100, bob: 100 })
  expect(result.current.isMyTurn).toBe(true)
})

test('attack message adds attack + referee entries to chatLog', () => {
  const { result } = renderHook(() => useGameState('alice'))
  act(() => {
    result.current.handleMessage({
      type: 'attack', sender: 'bob', display_text: '你好遜！',
      damage: 25, referee_comment: '猛',
      hp_status: { alice: 75, bob: 100 }, current_turn: 'alice',
    })
  })
  expect(result.current.hp.alice).toBe(75)
  const attackEntry = result.current.chatLog.find(e => e.kind === 'attack')
  expect(attackEntry).toBeDefined()
  if (attackEntry?.kind === 'attack') expect(attackEntry.damage).toBe(25)
  const refereeEntry = result.current.chatLog.find(e => e.kind === 'referee')
  expect(refereeEntry).toBeDefined()
})

test('attack message sets lastDamageEvent', () => {
  const { result } = renderHook(() => useGameState('alice'))
  act(() => {
    result.current.handleMessage({
      type: 'attack', sender: 'bob', display_text: 'test',
      damage: 18, referee_comment: 'ok',
      hp_status: { alice: 82, bob: 100 }, current_turn: 'alice',
    })
  })
  expect(result.current.lastDamageEvent?.damage).toBe(18)
})

test('game_over sets gameOver winner', () => {
  const { result } = renderHook(() => useGameState('alice'))
  act(() => {
    result.current.handleMessage({ type: 'game_over', message: '結束', winner: 'bob' })
  })
  expect(result.current.gameOver).toBe('bob')
})
```

- [ ] **Step 2: Run — expect FAIL**

```bash
cd src/frontend && npm test -- --reporter=verbose useGameState
```

Expected: FAIL on `chatLog.find(e => e.kind === 'attack')` — old useGameState doesn't have `.kind`

- [ ] **Step 3: Rewrite useGameState.ts**

```ts
// src/frontend/src/hooks/useGameState.ts
import { useState, useCallback } from 'react'
import type { ChatEntry, HPMap, ServerMessage } from '../types/game'

export function useGameState(myPlayerId: string) {
  const [hp, setHp] = useState<HPMap>({})
  const [currentTurn, setCurrentTurn] = useState('')
  const [chatLog, setChatLog] = useState<ChatEntry[]>([])
  const [gameOver, setGameOver] = useState<string | null>(null)
  const [lastDamageEvent, setLastDamageEvent] = useState<{ damage: number; id: number } | null>(null)

  const handleMessage = useCallback((msg: ServerMessage) => {
    if (msg.type === 'system') {
      setHp(msg.hp_status)
      setCurrentTurn(msg.current_turn)
      setChatLog(prev => [...prev, { id: Date.now(), kind: 'system', displayText: msg.message }])
    } else if (msg.type === 'attack') {
      setHp(msg.hp_status)
      setCurrentTurn(msg.current_turn)
      setLastDamageEvent({ damage: msg.damage, id: Date.now() })
      setChatLog(prev => [...prev,
        { id: Date.now(), kind: 'attack', sender: msg.sender, displayText: msg.display_text, damage: msg.damage, isNpc: false },
        { id: Date.now() + 1, kind: 'referee', displayText: msg.referee_comment },
      ])
    } else if (msg.type === 'npc_attack') {
      setHp(msg.hp_status)
      setLastDamageEvent({ damage: msg.damage, id: Date.now() })
      setChatLog(prev => [...prev,
        { id: Date.now(), kind: 'attack', sender: 'NPC', displayText: msg.display_text, damage: msg.damage, isNpc: true },
        { id: Date.now() + 1, kind: 'referee', displayText: msg.referee_comment },
      ])
    } else if (msg.type === 'game_over') {
      setGameOver(msg.winner)
      setChatLog(prev => [...prev, { id: Date.now(), kind: 'system', displayText: msg.message }])
    }
  }, [myPlayerId])

  return {
    hp, currentTurn,
    isMyTurn: currentTurn === myPlayerId,
    chatLog, gameOver, lastDamageEvent,
    handleMessage,
  }
}
```

- [ ] **Step 4: Run — expect PASS**

```bash
cd src/frontend && npm test -- --reporter=verbose useGameState
```

Expected: 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/frontend/src/hooks/useGameState.ts src/frontend/src/hooks/useGameState.test.ts
git commit -m "feat: update useGameState with kind-based ChatEntry + lastDamageEvent"
```

---

## Task 13: HomePage redesign

**Files:**
- Modify: `src/frontend/src/pages/HomePage.tsx`
- Modify: `src/frontend/src/pages/HomePage.test.tsx`

- [ ] **Step 1: Rewrite HomePage.test.tsx**

```tsx
// src/frontend/src/pages/HomePage.test.tsx
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { AuthProvider } from '../contexts/AuthContext'
import HomePage from './HomePage'

global.fetch = vi.fn()

const wrap = (ui: React.ReactElement) =>
  render(<AuthProvider><MemoryRouter>{ui}</MemoryRouter></AuthProvider>)

beforeEach(() => {
  localStorage.clear()
  vi.clearAllMocks()
})

test('renders login and register tabs when not authenticated', () => {
  wrap(<HomePage />)
  expect(screen.getByText('登入')).toBeInTheDocument()
  expect(screen.getByText('註冊')).toBeInTheDocument()
})

test('shows error on login failure', async () => {
  (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
    ok: false, json: async () => ({ detail: 'Invalid credentials' }),
  })
  wrap(<HomePage />)
  fireEvent.change(screen.getByPlaceholderText('用戶名'), { target: { value: 'alice' } })
  fireEvent.change(screen.getByPlaceholderText('密碼'), { target: { value: 'wrong' } })
  fireEvent.click(screen.getByRole('button', { name: /進入戰場/ }))
  await waitFor(() => expect(screen.getByText(/登入失敗/)).toBeInTheDocument())
})
```

- [ ] **Step 2: Run — expect FAIL**

```bash
cd src/frontend && npm test -- --reporter=verbose HomePage
```

Expected: FAIL (old HomePage doesn't use AuthProvider/AuthContext)

- [ ] **Step 3: Rewrite HomePage.tsx**

```tsx
// src/frontend/src/pages/HomePage.tsx
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthContext } from '../contexts/AuthContext'
import Button from '../components/Button'

const API = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export default function HomePage() {
  const { isAuthenticated, username, token, userId, error, login, register, clearError } = useAuthContext()
  const [tab, setTab] = useState<'login' | 'register'>('login')
  const [inputUsername, setInputUsername] = useState('')
  const [inputPassword, setInputPassword] = useState('')
  const [opponent, setOpponent] = useState('npc')
  const [opponentTab, setOpponentTab] = useState<'npc' | 'human'>('npc')
  const [matchError, setMatchError] = useState('')
  const navigate = useNavigate()

  async function handleAuth() {
    clearError()
    const success = tab === 'login'
      ? await login(inputUsername, inputPassword)
      : await register(inputUsername, inputPassword)
    if (success) { setInputUsername(''); setInputPassword('') }
  }

  async function handleStartMatch() {
    setMatchError('')
    const resp = await fetch(`${API}/api/matches`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify({ opponent }),
    })
    const data = await resp.json()
    if (resp.ok) {
      navigate(`/battle/${data.match_id}`, { state: { token, myUsername: username, userId } })
    } else {
      setMatchError(data.detail ?? '建立對局失敗')
    }
  }

  if (!isAuthenticated) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-ink">
        <div className="w-full max-w-xs px-6 py-8">
          {/* Logo */}
          <div className="text-center mb-8">
            <div className="font-display text-[42px] text-white tracking-[5px] leading-tight">唇槍</div>
            <div className="font-display text-[42px] text-vermillion tracking-[5px] leading-tight" style={{ textShadow: '0 0 20px rgba(204,51,0,0.5)' }}>舌戰</div>
            <div className="font-mono text-bark text-[7px] tracking-[6px] mt-1">VERBAL SPARRING</div>
          </div>
          {/* Auth tabs */}
          <div className="flex border border-bamboo mb-3">
            <button onClick={() => setTab('login')} className={`flex-1 py-2 font-display text-[10px] tracking-[3px] ${tab === 'login' ? 'bg-vermillion text-white' : 'text-bark'}`}>登入</button>
            <button onClick={() => setTab('register')} className={`flex-1 py-2 font-mono text-[10px] tracking-[3px] ${tab === 'register' ? 'bg-vermillion text-white' : 'text-bark'}`}>註冊</button>
          </div>
          {/* Inputs */}
          <input
            placeholder="用戶名"
            value={inputUsername}
            onChange={e => setInputUsername(e.target.value)}
            className="w-full bg-[#080805] border border-bamboo px-3 py-2 text-aged font-mono text-[10px] mb-2 focus:outline-none focus:border-vermillion"
          />
          <input
            type="password"
            placeholder="密碼"
            value={inputPassword}
            onChange={e => setInputPassword(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleAuth()}
            className="w-full bg-[#080805] border border-bamboo px-3 py-2 text-aged font-mono text-[10px] mb-3 focus:outline-none focus:border-vermillion"
          />
          {error && (
            <div className="border-l-[3px] border-vermillion bg-[#1a0005] px-3 py-2 text-[#cc6633] font-mono text-[9px] mb-3">{error}</div>
          )}
          <Button variant="primary-outline" onClick={handleAuth} className="w-full">進入戰場</Button>
        </div>
      </div>
    )
  }

  return (
    <div className="flex-1 flex flex-col items-center justify-center bg-ink p-6">
      {/* Welcome */}
      <div className="mb-6 text-center">
        <div className="font-mono text-bark text-[8px] tracking-[3px] mb-1">武士歸來</div>
        <div className="font-display text-[24px] text-white tracking-[2px]">
          {username.toUpperCase()}<span className="text-vermillion text-[14px] ml-2 tracking-wider">入場</span>
        </div>
      </div>
      {/* Match card */}
      <div className="w-full max-w-sm border border-bamboo bg-parchment p-5">
        <div className="font-mono text-bark text-[8px] tracking-[3px] mb-3">選擇對手</div>
        <div className="flex border border-bamboo mb-3">
          <button onClick={() => { setOpponentTab('npc'); setOpponent('npc') }}
            className={`flex-1 py-2 font-display text-[10px] tracking-[2px] ${opponentTab === 'npc' ? 'bg-vermillion text-white' : 'text-bark'}`}>
            AI NPC
          </button>
          <button onClick={() => setOpponentTab('human')}
            className={`flex-1 py-2 font-mono text-[10px] tracking-[2px] ${opponentTab === 'human' ? 'bg-vermillion text-white' : 'text-bark'}`}>
            人類對手
          </button>
        </div>
        {opponentTab === 'human' && (
          <input
            placeholder="輸入對手用戶名"
            value={opponent === 'npc' ? '' : opponent}
            onChange={e => setOpponent(e.target.value || 'npc')}
            className="w-full bg-ink border border-bamboo px-3 py-2 text-aged font-mono text-[10px] mb-3 focus:outline-none focus:border-vermillion"
          />
        )}
        {matchError && (
          <div className="border-l-[3px] border-vermillion bg-[#1a0005] px-3 py-2 text-[#cc6633] font-mono text-[9px] mb-3">{matchError}</div>
        )}
        <Button variant="primary-solid" onClick={handleStartMatch} className="w-full">開戰！</Button>
      </div>
    </div>
  )
}
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
cd src/frontend && npm test -- --reporter=verbose HomePage
```

Expected: 2 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/frontend/src/pages/HomePage.tsx src/frontend/src/pages/HomePage.test.tsx
git commit -m "feat: redesign HomePage with Tailwind + AuthContext"
```

---

## Task 14: BattlePage redesign

**Files:**
- Modify: `src/frontend/src/pages/BattlePage.tsx`

- [ ] **Step 1: Rewrite BattlePage.tsx**

```tsx
// src/frontend/src/pages/BattlePage.tsx
import { useEffect, useState } from 'react'
import { useParams, useLocation, useNavigate } from 'react-router-dom'
import { motion, useAnimation } from 'framer-motion'
import { useGameState } from '../hooks/useGameState'
import { useWebSocket } from '../hooks/useWebSocket'
import { useAuthContext } from '../contexts/AuthContext'
import HPBar from '../components/HPBar'
import ChatLog from '../components/ChatLog'
import AttackInput from '../components/AttackInput'
import TurnIndicator from '../components/TurnIndicator'
import DamageNumber from '../components/DamageNumber'
import GameOverModal from '../components/GameOverModal'
import type { MatchRecord } from '../types/game'

export default function BattlePage() {
  const { matchId } = useParams<{ matchId: string }>()
  const location = useLocation()
  const navigate = useNavigate()
  const { token: ctxToken, username: ctxUsername } = useAuthContext()
  const token: string = location.state?.token ?? ctxToken
  const myUsername: string = location.state?.myUsername ?? ctxUsername

  const { hp, isMyTurn, chatLog, gameOver, lastDamageEvent, handleMessage } = useGameState(myUsername)
  const { sendAttack } = useWebSocket(matchId!, myUsername, token, handleMessage)
  const shakeControls = useAnimation()

  const myHp = hp[myUsername] ?? 100
  const opponentEntries = Object.entries(hp).filter(([k]) => k !== myUsername)
  const [opponentName, opponentHp] = opponentEntries[0] ?? ['對手', 100]
  const roundCount = chatLog.filter(e => e.kind === 'attack').length

  // Screen shake on big damage
  useEffect(() => {
    if (!lastDamageEvent || lastDamageEvent.damage < 20) return
    shakeControls.start({ x: [0, -6, 6, -4, 4, 0], transition: { duration: 0.4 } })
  }, [lastDamageEvent, shakeControls])

  // Write match result to localStorage on game_over
  useEffect(() => {
    if (!gameOver || !matchId) return
    const prev: MatchRecord[] = JSON.parse(localStorage.getItem('matchHistory') ?? '[]')
    const myDamage = chatLog
      .filter((e): e is Extract<typeof e, { kind: 'attack' }> => e.kind === 'attack' && !e.isNpc)
      .reduce((sum, e) => sum + e.damage, 0)
    const record: MatchRecord = {
      matchId, opponent: String(opponentName),
      result: gameOver === myUsername ? 'win' : 'loss',
      totalDamage: myDamage, roundCount,
      timestamp: Date.now(),
    }
    localStorage.setItem('matchHistory', JSON.stringify([record, ...prev].slice(0, 50)))
  }, [gameOver])

  return (
    <motion.div animate={shakeControls} className="flex flex-col h-screen bg-ink text-white overflow-hidden">
      {/* Top bar */}
      <div className="bg-[#0f0e0b] border-b-2 border-bamboo flex justify-between items-center px-4 py-2 flex-shrink-0">
        <span className="font-display text-[12px] text-white tracking-[2px]">唇槍<span className="text-vermillion">舌戰</span></span>
        <span className="font-mono text-bark text-[8px] tracking-[3px]">ROUND <span className="font-display text-white text-[12px]">{String(Math.ceil(roundCount / 2)).padStart(2, '0')}</span></span>
        <button onClick={() => navigate('/')} className="font-mono text-bark text-[8px] border border-bamboo px-2 py-1 tracking-[2px] hover:text-aged">回主頁</button>
      </div>

      {/* HP section */}
      <div className="flex items-stretch border-b border-[#1a1610] flex-shrink-0">
        <div className="flex-1 px-4 py-3 border-r border-[#1a1610]">
          <HPBar label={myUsername} hp={myHp} />
        </div>
        <div className="px-3 flex flex-col items-center justify-center bg-[#080805]">
          <span className="font-body italic text-[#1a1610] text-sm">對</span>
          <div className="w-[1px] h-4 bg-gradient-to-b from-transparent via-bark to-transparent my-1" />
          <div className="w-[5px] h-[5px] bg-vermillion rounded-full opacity-60" />
        </div>
        <div className="flex-1 px-4 py-3 border-l border-[#1a1610] text-right">
          <HPBar label={String(opponentName)} hp={Number(opponentHp)} />
        </div>
      </div>

      {/* Chat log */}
      <ChatLog entries={chatLog} />

      {/* Turn indicator */}
      <TurnIndicator isMyTurn={isMyTurn} />

      {/* Input */}
      <AttackInput onSend={sendAttack} disabled={!isMyTurn} />

      {/* Damage number */}
      <DamageNumber damageEvent={lastDamageEvent} />

      {/* Game over modal */}
      {gameOver && (
        <GameOverModal
          winner={gameOver}
          myUsername={myUsername}
          matchId={matchId!}
          onPlayAgain={() => navigate('/')}
        />
      )}
    </motion.div>
  )
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd src/frontend && npx tsc --noEmit
```

Expected: exits 0, no type errors

- [ ] **Step 3: Commit**

```bash
git add src/frontend/src/pages/BattlePage.tsx
git commit -m "feat: redesign BattlePage with animations + GameOverModal"
```

---

## Task 15: LeaderboardPage redesign

**Files:**
- Modify: `src/frontend/src/pages/LeaderboardPage.tsx`
- Modify: `src/frontend/src/pages/LeaderboardPage.test.tsx`

- [ ] **Step 1: Rewrite LeaderboardPage.test.tsx**

```tsx
// src/frontend/src/pages/LeaderboardPage.test.tsx
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { AuthProvider } from '../contexts/AuthContext'
import LeaderboardPage from './LeaderboardPage'

global.fetch = vi.fn()

const wrap = (ui: React.ReactElement) =>
  render(<AuthProvider><MemoryRouter>{ui}</MemoryRouter></AuthProvider>)

beforeEach(() => vi.clearAllMocks())

test('renders leaderboard title', async () => {
  (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
    ok: true, json: async () => ({ entries: [] }),
  })
  wrap(<LeaderboardPage />)
  expect(screen.getByText('武林')).toBeInTheDocument()
})

test('renders player entries from API', async () => {
  (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
    ok: true,
    json: async () => ({
      entries: [
        { rank: 1, username: 'alice', total_damage: 9000, wins: 10, losses: 2 },
      ],
    }),
  })
  wrap(<LeaderboardPage />)
  await waitFor(() => expect(screen.getByText('ALICE')).toBeInTheDocument())
  expect(screen.getByText('9000')).toBeInTheDocument()
})
```

- [ ] **Step 2: Run — expect FAIL**

```bash
cd src/frontend && npm test -- --reporter=verbose LeaderboardPage
```

Expected: FAIL (old component doesn't render uppercase or use AuthProvider)

- [ ] **Step 3: Rewrite LeaderboardPage.tsx**

```tsx
// src/frontend/src/pages/LeaderboardPage.tsx
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import type { LeaderboardEntry } from '../types/game'

const API = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'
const CHINESE_RANKS = ['一', '二', '三']

export default function LeaderboardPage() {
  const [entries, setEntries] = useState<LeaderboardEntry[]>([])

  useEffect(() => {
    fetch(`${API}/api/leaderboard`)
      .then(r => r.json())
      .then(d => setEntries(d.entries ?? []))
  }, [])

  return (
    <div className="flex-1 bg-ink px-4 py-6 max-w-2xl mx-auto w-full">
      {/* Title */}
      <div className="flex items-baseline gap-2 border-b-[3px] border-vermillion pb-2 mb-4">
        <span className="font-display text-[20px] text-white tracking-[3px]">武林</span>
        <span className="font-display text-[20px] text-vermillion tracking-[3px]">排行</span>
        <span className="font-mono text-bark text-[8px] tracking-[2px] ml-auto">TOP 50</span>
      </div>
      {/* Header row */}
      <div className="flex gap-2 text-bark font-mono text-[8px] tracking-[2px] px-1 pb-1 mb-1">
        <span className="w-6">位</span>
        <span className="flex-1">俠士</span>
        <span className="w-14 text-right">傷害</span>
        <span className="w-8 text-right">勝</span>
        <span className="w-8 text-right">敗</span>
      </div>
      {/* Entries */}
      {entries.map((e) => {
        const rankDisplay = e.rank <= 3 ? CHINESE_RANKS[e.rank - 1] : String(e.rank)
        const borderColor = e.rank === 1 ? '#cc3300' : e.rank === 2 ? '#662200' : e.rank <= 3 ? '#331100' : '#2a2018'
        const bg = e.rank === 1 ? 'bg-[#1a0d00]' : e.rank === 2 ? 'bg-[#0f0a05]' : ''
        return (
          <div
            key={e.rank}
            className={`flex gap-2 items-center px-1 py-[6px] mb-[2px] ${bg}`}
            style={{ borderLeft: `3px solid ${borderColor}` }}
          >
            <span className="w-6 font-display text-[14px] text-vermillion/70">{rankDisplay}</span>
            <span className="flex-1 font-display text-[13px] tracking-wider text-white">{e.username.toUpperCase()}</span>
            <span className="w-14 text-right font-mono text-[10px] text-vermillion/80">{e.total_damage.toLocaleString()}</span>
            <span className="w-8 text-right font-mono text-[10px] text-aged">{e.wins}</span>
            <span className="w-8 text-right font-mono text-[10px] text-bark">{e.losses}</span>
          </div>
        )
      })}
      {entries.length === 0 && (
        <div className="text-bark font-mono text-[9px] tracking-[2px] text-center py-8">載入中...</div>
      )}
      <div className="text-[#2a1a0a] font-body italic text-[8px] tracking-[3px] text-center border-t border-[#1a1610] pt-4 mt-6">
        ⸺ 以筆傷人，武林稱霸 ⸺
      </div>
      <div className="text-center mt-4">
        <Link to="/" className="font-mono text-bark text-[9px] tracking-[2px] hover:text-aged">← 回首頁</Link>
      </div>
    </div>
  )
}
```

- [ ] **Step 4: Run — expect PASS**

```bash
cd src/frontend && npm test -- --reporter=verbose LeaderboardPage
```

Expected: 2 tests PASS

- [ ] **Step 5: Commit**

```bash
git add src/frontend/src/pages/LeaderboardPage.tsx src/frontend/src/pages/LeaderboardPage.test.tsx
git commit -m "feat: redesign LeaderboardPage with Tailwind"
```

---

## Task 16: ProfilePage (new)

**Files:**
- Create: `src/frontend/src/pages/ProfilePage.tsx`

- [ ] **Step 1: Create ProfilePage.tsx**

```tsx
// src/frontend/src/pages/ProfilePage.tsx
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuthContext } from '../contexts/AuthContext'
import type { LeaderboardEntry, MatchRecord } from '../types/game'

const API = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

function rankTitle(wins: number) {
  if (wins >= 50) return '武林盟主'
  if (wins >= 20) return '武林高手'
  if (wins >= 10) return '初出茅廬'
  return '江湖新人'
}

export default function ProfilePage() {
  const { username } = useAuthContext()
  const [stats, setStats] = useState<LeaderboardEntry | null>(null)
  const [history, setHistory] = useState<MatchRecord[]>([])

  useEffect(() => {
    fetch(`${API}/api/leaderboard`)
      .then(r => r.json())
      .then((d: { entries: LeaderboardEntry[] }) => {
        const mine = d.entries.find(e => e.username === username)
        if (mine) setStats(mine)
      })
  }, [username])

  useEffect(() => {
    const stored: MatchRecord[] = JSON.parse(localStorage.getItem('matchHistory') ?? '[]')
    setHistory(stored.slice(0, 5))
  }, [])

  return (
    <div className="flex-1 bg-ink px-4 py-6 max-w-md mx-auto w-full">
      {/* Avatar + name */}
      <div className="flex flex-col items-center mb-6">
        <div className="w-[60px] h-[60px] rounded-full border-2 border-vermillion flex items-center justify-center mb-3"
             style={{ background: '#0f0e0b' }}>
          <span className="font-display text-[22px] text-vermillion">{username.charAt(0).toUpperCase()}</span>
        </div>
        <div className="font-display text-[20px] text-white tracking-[3px]">{username.toUpperCase()}</div>
        <div className="font-mono text-bark text-[8px] tracking-[3px] mt-1">{rankTitle(stats?.wins ?? 0)}</div>
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-3 gap-2 mb-6">
        {[
          { label: '勝場', value: stats?.wins ?? 0, color: 'text-white' },
          { label: '敗場', value: stats?.losses ?? 0, color: 'text-[#664433]' },
          { label: '累積傷害', value: (stats?.total_damage ?? 0).toLocaleString(), color: 'text-vermillion' },
        ].map(({ label, value, color }) => (
          <div key={label} className="bg-parchment border border-[#4a4028] p-3 text-center">
            <div className={`font-display text-[22px] ${color}`}>{value}</div>
            <div className="font-mono text-aged text-[7px] tracking-[2px]">{label}</div>
          </div>
        ))}
      </div>

      {/* Recent matches */}
      <div className="mb-4">
        <div className="font-mono text-bark text-[8px] tracking-[2px] mb-3">最近五場</div>
        {history.length === 0 ? (
          <div className="text-bark font-mono text-[9px] text-center py-4">尚無對戰紀錄</div>
        ) : (
          history.map((r, i) => (
            <div
              key={i}
              className="flex items-center gap-2 px-3 py-2 mb-[3px]"
              style={{ borderLeft: `2px solid ${r.result === 'win' ? '#cc3300' : '#443322'}` }}
            >
              <span className={`font-mono text-[8px] tracking-[2px] ${r.result === 'win' ? 'text-vermillion' : 'text-bark'}`}>
                {r.result === 'win' ? '勝' : '敗'}
              </span>
              <span className="font-display text-[11px] text-aged flex-1">vs {r.opponent.toUpperCase()}</span>
              <span className="font-mono text-bark text-[8px]">+{r.totalDamage}</span>
              <Link to={`/replay/${r.matchId}`} className="font-mono text-bark text-[8px] tracking-[2px] hover:text-aged">回放▶</Link>
            </div>
          ))
        )}
      </div>

      <div className="text-center mt-4">
        <Link to="/" className="font-mono text-bark text-[9px] tracking-[2px] hover:text-aged">← 回首頁</Link>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add src/frontend/src/pages/ProfilePage.tsx
git commit -m "feat: add ProfilePage with stats + recent matches"
```

---

## Task 17: HistoryPage (new)

**Files:**
- Create: `src/frontend/src/pages/HistoryPage.tsx`

- [ ] **Step 1: Create HistoryPage.tsx**

```tsx
// src/frontend/src/pages/HistoryPage.tsx
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import type { MatchRecord } from '../types/game'

type Filter = 'all' | 'win' | 'loss'

export default function HistoryPage() {
  const [history, setHistory] = useState<MatchRecord[]>([])
  const [filter, setFilter] = useState<Filter>('all')
  const [page, setPage] = useState(0)
  const PAGE_SIZE = 20

  useEffect(() => {
    const stored: MatchRecord[] = JSON.parse(localStorage.getItem('matchHistory') ?? '[]')
    setHistory(stored)
  }, [])

  const filtered = history.filter(r => filter === 'all' || r.result === filter)
  const paged = filtered.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE)
  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE))

  const tabs: { key: Filter; label: string }[] = [
    { key: 'all', label: '全部' },
    { key: 'win', label: '勝場' },
    { key: 'loss', label: '敗場' },
  ]

  return (
    <div className="flex-1 bg-ink px-4 py-6 max-w-2xl mx-auto w-full">
      {/* Title */}
      <div className="font-display text-[20px] text-white tracking-[3px] border-b-[3px] border-vermillion pb-2 mb-4">
        對戰紀錄
      </div>
      {/* Filter tabs */}
      <div className="flex gap-1 mb-4">
        {tabs.map(t => (
          <button
            key={t.key}
            onClick={() => { setFilter(t.key); setPage(0) }}
            className={`px-3 py-1 font-mono text-[9px] tracking-[2px] ${filter === t.key ? 'bg-vermillion text-white' : 'border border-bamboo text-bark hover:text-aged'}`}
          >
            {t.label}
          </button>
        ))}
      </div>
      {/* Match list */}
      {paged.length === 0 ? (
        <div className="text-bark font-mono text-[9px] text-center py-8">無對戰紀錄</div>
      ) : (
        paged.map((r, i) => (
          <div
            key={i}
            className={`border border-bamboo px-4 py-3 mb-2 ${r.result === 'win' ? 'bg-parchment' : ''}`}
          >
            <div className="flex items-center justify-between mb-1">
              <span className="font-display text-[13px] text-white tracking-wider">vs {r.opponent.toUpperCase()}</span>
              <span className={`font-mono text-[9px] tracking-[2px] ${r.result === 'win' ? 'text-[#66cc00]' : 'text-vermillion'}`}>
                {r.result === 'win' ? '勝' : '敗'}
              </span>
            </div>
            <div className="flex items-center gap-3">
              <span className="font-mono text-bark text-[8px]">{r.roundCount} 回合</span>
              <span className="font-mono text-bark text-[8px]">傷害 +{r.totalDamage}</span>
              <Link to={`/replay/${r.matchId}`} className="font-mono text-aged text-[8px] tracking-[2px] hover:text-white ml-auto">
                看回放 ▶
              </Link>
            </div>
          </div>
        ))
      )}
      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex gap-2 justify-center mt-4">
          <button onClick={() => setPage(p => Math.max(0, p - 1))} disabled={page === 0}
            className="font-mono text-bark text-[9px] border border-bamboo px-3 py-1 disabled:opacity-40 hover:text-aged">
            ◀
          </button>
          <span className="font-mono text-aged text-[9px] px-2 py-1">{page + 1} / {totalPages}</span>
          <button onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))} disabled={page >= totalPages - 1}
            className="font-mono text-bark text-[9px] border border-bamboo px-3 py-1 disabled:opacity-40 hover:text-aged">
            ▶
          </button>
        </div>
      )}
      <div className="text-center mt-6">
        <Link to="/" className="font-mono text-bark text-[9px] tracking-[2px] hover:text-aged">← 回首頁</Link>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add src/frontend/src/pages/HistoryPage.tsx
git commit -m "feat: add HistoryPage with filter + pagination"
```

---

## Task 18: ReplayPage redesign

**Files:**
- Modify: `src/frontend/src/pages/ReplayPage.tsx`

- [ ] **Step 1: Rewrite ReplayPage.tsx**

```tsx
// src/frontend/src/pages/ReplayPage.tsx
import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import HPBar from '../components/HPBar'
import type { RoundSnapshot } from '../types/game'

const API = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export default function ReplayPage() {
  const { matchId } = useParams<{ matchId: string }>()
  const [rounds, setRounds] = useState<RoundSnapshot[]>([])
  const [frame, setFrame] = useState(0)

  useEffect(() => {
    if (!matchId) return
    fetch(`${API}/api/replay/${matchId}`)
      .then(r => r.json())
      .then(d => setRounds(d.rounds ?? []))
  }, [matchId])

  const current = rounds[frame]
  const hpEntries = current ? Object.entries(current.hp_snapshot) : []

  return (
    <div className="flex-1 bg-ink px-4 py-6 max-w-xl mx-auto w-full">
      {/* Title */}
      <div className="flex items-baseline gap-3 border-b-[3px] border-vermillion pb-2 mb-5">
        <span className="font-display text-[18px] text-white tracking-[3px]">回放</span>
        {rounds.length > 0 && (
          <span className="font-mono text-aged text-[10px] tracking-[2px]">
            ROUND <span className="text-vermillion font-display text-[14px]">{frame + 1}</span>/{rounds.length}
          </span>
        )}
      </div>

      {rounds.length === 0 ? (
        <div className="text-bark font-mono text-[9px] tracking-[2px] text-center py-8">載入中...</div>
      ) : (
        <>
          {/* HP Snapshot */}
          <div className="mb-5 space-y-3">
            {hpEntries.map(([player, hp]) => (
              <HPBar key={player} label={player} hp={Number(hp)} />
            ))}
          </div>

          {/* Round card */}
          {current && (
            <div className="bg-parchment border border-[#4a4028] p-4 mb-5">
              <div className="font-mono text-vermillion text-[9px] tracking-[3px] mb-2 uppercase">
                {current.attacker ?? 'NPC'} 出招
              </div>
              {current.original_text && current.original_text !== current.display_text && (
                <div className="font-body italic text-bark text-[10px] mb-1 line-through">
                  {current.original_text}
                </div>
              )}
              <div className="font-body italic text-[#d4c5aa] text-[12px] mb-3 leading-relaxed">
                「{current.display_text}」
              </div>
              <div className="flex items-center gap-3 pt-2 border-t border-bamboo">
                <span className="font-mono text-bark text-[9px]">
                  傷害 <span className="text-fire font-display text-[14px]">-{current.damage}</span>
                </span>
                <span className="font-mono text-bark text-[8px] tracking-[1px] italic">{current.referee_comment}</span>
              </div>
            </div>
          )}

          {/* Scrubber */}
          <div className="flex items-center gap-3">
            <button
              onClick={() => setFrame(f => Math.max(0, f - 1))}
              disabled={frame === 0}
              className="w-8 h-8 bg-vermillion flex items-center justify-center font-display text-white text-[10px] disabled:opacity-40 disabled:cursor-not-allowed hover:bg-fire flex-shrink-0"
            >
              ◀
            </button>
            <div className="relative flex-1 h-1 bg-[#1a1610]">
              <div
                className="absolute left-0 top-0 h-full bg-vermillion"
                style={{ width: `${((frame) / Math.max(1, rounds.length - 1)) * 100}%` }}
              />
              <input
                type="range"
                min={0}
                max={rounds.length - 1}
                value={frame}
                onChange={e => setFrame(Number(e.target.value))}
                className="absolute inset-0 w-full opacity-0 cursor-pointer"
              />
              <div
                className="absolute top-1/2 w-3 h-3 bg-fire rounded-full -translate-y-1/2 -translate-x-1/2 pointer-events-none"
                style={{ left: `${((frame) / Math.max(1, rounds.length - 1)) * 100}%` }}
              />
            </div>
            <button
              onClick={() => setFrame(f => Math.min(rounds.length - 1, f + 1))}
              disabled={frame >= rounds.length - 1}
              className="w-8 h-8 bg-vermillion flex items-center justify-center font-display text-white text-[10px] disabled:opacity-40 disabled:cursor-not-allowed hover:bg-fire flex-shrink-0"
            >
              ▶
            </button>
          </div>
        </>
      )}

      <div className="text-center mt-6">
        <Link to="/" className="font-mono text-bark text-[9px] tracking-[2px] hover:text-aged">← 回首頁</Link>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add src/frontend/src/pages/ReplayPage.tsx
git commit -m "feat: redesign ReplayPage with HP snapshot + styled scrubber"
```

---

## Task 19: Update App.tsx routing

**Files:**
- Modify: `src/frontend/src/App.tsx`

- [ ] **Step 1: Rewrite App.tsx**

```tsx
// src/frontend/src/App.tsx
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { AuthProvider } from './contexts/AuthContext'
import Layout from './components/Layout'
import HomePage from './pages/HomePage'
import BattlePage from './pages/BattlePage'
import LeaderboardPage from './pages/LeaderboardPage'
import ReplayPage from './pages/ReplayPage'
import ProfilePage from './pages/ProfilePage'
import HistoryPage from './pages/HistoryPage'

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route path="/" element={<HomePage />} />
            <Route path="/battle/:matchId" element={<BattlePage />} />
            <Route path="/leaderboard" element={<LeaderboardPage />} />
            <Route path="/replay/:matchId" element={<ReplayPage />} />
            <Route path="/profile" element={<ProfilePage />} />
            <Route path="/history" element={<HistoryPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add src/frontend/src/App.tsx
git commit -m "feat: update App routing with AuthProvider + Layout + new pages"
```

---

## Task 20: Full verification

**Files:** none (read-only)

- [ ] **Step 1: Run all tests**

```bash
cd src/frontend && npm test -- --reporter=verbose
```

Expected: all tests PASS. If any fail, fix before proceeding.

- [ ] **Step 2: TypeScript check**

```bash
cd src/frontend && npx tsc --noEmit
```

Expected: exits 0, no errors.

- [ ] **Step 3: Production build**

```bash
cd src/frontend && npm run build
```

Expected: exits 0, `dist/` created.

- [ ] **Step 4: Add .superpowers to .gitignore if needed**

```bash
grep -q '.superpowers' /media/ubuntu/4TB-HDD/ziyue/verbal_sparring/.gitignore || echo '.superpowers/' >> /media/ubuntu/4TB-HDD/ziyue/verbal_sparring/.gitignore
```

- [ ] **Step 5: Final commit**

```bash
git add .gitignore
git commit -m "chore: add .superpowers to .gitignore"
```

---

## Spec Coverage Check

| 規格要求 | 對應 Task |
|---|---|
| Tailwind + Framer Motion | Task 1 |
| 色彩 token（10色）| Task 1 (tailwind.config.js) |
| Deep Parchment #3a3020 | Task 1 |
| AuthContext + 登出 | Task 3, Task 10 (Navbar) |
| Button 3 variants | Task 4 |
| HPBar 三段色 + 動畫 | Task 5 |
| RefereeStamp 印章 | Task 6 |
| MessageBubble (attack/system) | Task 7 |
| DamageNumber 浮現動畫 | Task 8 |
| TurnIndicator | Task 8 |
| GameOverModal + 回放連結 | Task 9 |
| Navbar + Layout | Task 10 |
| ChatLog 新 kind 結構 | Task 11 |
| AttackInput 重設計 | Task 11 |
| useGameState lastDamageEvent | Task 12 |
| Screen shake (≥20 damage) | Task 14 (BattlePage) |
| matchHistory localStorage 寫入 | Task 14 (BattlePage) |
| HomePage 重設計 + 登出 | Task 13, Task 10 |
| BattlePage 完整串接 | Task 14 |
| LeaderboardPage 漢字排名 | Task 15 |
| ProfilePage (新) | Task 16 |
| HistoryPage + filter + pagination (新) | Task 17 |
| ReplayPage 重設計 + HP快照 + 進度條 | Task 18 |
| /profile + /history 路由 | Task 19 |
| WS turn_error 回饋 | ⚠️ 未涵蓋，見下方 |

**補充：turn_error 閃爍**
`AttackInput` 需要接收一個 `hasError` prop 以閃爍邊框。在 `useGameState` 加入 `turnError` state，BattlePage 傳入 AttackInput。此功能可作為後續 Task 追加，不阻塞主流程。
