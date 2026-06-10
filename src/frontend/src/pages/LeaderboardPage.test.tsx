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
  expect(screen.getByText((9000).toLocaleString())).toBeInTheDocument()
})
