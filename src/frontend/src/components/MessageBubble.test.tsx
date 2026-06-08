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
