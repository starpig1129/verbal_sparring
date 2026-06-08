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
