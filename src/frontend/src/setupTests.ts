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
  AnimatePresence: ({ children, ..._ }: { children?: React.ReactNode; [key: string]: unknown }) =>
    React.createElement(React.Fragment, null, children),
  useAnimation: () => ({ start: vi.fn() }),
}))
