import { render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { AuthProvider, useAuth } from '@/hooks/use-auth'

const authServiceMock = vi.hoisted(() => ({
  refresh: vi.fn(),
  me: vi.fn(),
  login: vi.fn(),
  signup: vi.fn(),
  logout: vi.fn(),
}))

vi.mock('@/api/authService', () => ({
  authService: authServiceMock,
}))

const session = {
  user: { id: '1', name: 'Alex Morgan', email: 'alex@acme.dev' },
  organization: { id: 'org-1', name: 'Acme Platform', slug: 'acme-platform' },
  membership: { id: 'm-1', organizationId: 'org-1', role: 'owner' as const },
}

function AuthProbe() {
  const { user, organization, membership, isAuthenticated, isLoading } = useAuth()

  if (isLoading) {
    return <div role="status">Loading auth</div>
  }

  return (
    <div>
      <p data-testid="authenticated">{String(isAuthenticated)}</p>
      <p data-testid="email">{user?.email ?? 'none'}</p>
      <p data-testid="organization">{organization?.name ?? 'none'}</p>
      <p data-testid="role">{membership?.role ?? 'none'}</p>
    </div>
  )
}

describe('AuthProvider', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    authServiceMock.refresh.mockRejectedValue(new Error('no refresh cookie'))
    authServiceMock.me.mockResolvedValue(session)
  })

  it('hydrates session from /auth/me when refresh is unavailable', async () => {
    render(
      <AuthProvider>
        <AuthProbe />
      </AuthProvider>,
    )

    await waitFor(() => {
      expect(screen.getByTestId('authenticated')).toHaveTextContent('true')
    })

    expect(screen.getByTestId('email')).toHaveTextContent('alex@acme.dev')
    expect(screen.getByTestId('organization')).toHaveTextContent('Acme Platform')
    expect(screen.getByTestId('role')).toHaveTextContent('owner')
  })

  it('prefers refresh when a valid refresh cookie exists', async () => {
    authServiceMock.refresh.mockResolvedValue(session)

    render(
      <AuthProvider>
        <AuthProbe />
      </AuthProvider>,
    )

    await waitFor(() => {
      expect(screen.getByTestId('authenticated')).toHaveTextContent('true')
    })

    expect(authServiceMock.refresh).toHaveBeenCalled()
    expect(authServiceMock.me).not.toHaveBeenCalled()
  })
})
