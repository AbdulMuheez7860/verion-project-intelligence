import { render, screen, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import { SignupPage } from '@/features/auth/signup-page'

const signupMock = vi.fn()

vi.mock('@/hooks/use-auth', () => ({
  useAuth: () => ({
    signup: signupMock,
  }),
}))

describe('SignupPage', () => {
  it('shows validation errors for incomplete signup', async () => {
    render(
      <MemoryRouter>
        <SignupPage />
      </MemoryRouter>,
    )

    fireEvent.click(screen.getByRole('button', { name: /create workspace/i }))

    expect(await screen.findByText(/full name is required/i)).toBeInTheDocument()
    expect(screen.getByText('Accept the terms to continue.')).toBeInTheDocument()
    expect(signupMock).not.toHaveBeenCalled()
  })
})
