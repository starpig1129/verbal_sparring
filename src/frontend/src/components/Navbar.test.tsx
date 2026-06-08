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
