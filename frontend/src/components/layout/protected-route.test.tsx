import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ProtectedRoute } from '@/components/layout/protected-route'

const authState = vi.hoisted(() => ({
  isAuthenticated: false,
  isLoading: false,
}))

vi.mock('@/hooks/use-auth', () => ({
  useAuth: () => ({
    user: authState.isAuthenticated ? { id: '1', name: 'Alex', email: 'alex@acme.dev' } : null,
    organization: authState.isAuthenticated ? { id: 'org-1', name: 'Acme', slug: 'acme' } : null,
    membership: authState.isAuthenticated
      ? { id: 'm-1', organizationId: 'org-1', role: 'owner' as const }
      : null,
    isAuthenticated: authState.isAuthenticated,
    isLoading: authState.isLoading,
    login: vi.fn(),
    signup: vi.fn(),
    logout: vi.fn(),
    refresh: vi.fn(),
  }),
}))

function renderProtectedRoute(initialPath = '/app/dashboard') {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <Routes>
        <Route element={<ProtectedRoute />}>
          <Route path="/app/dashboard" element={<div>Dashboard content</div>} />
        </Route>
        <Route path="/login" element={<div>Login page</div>} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('ProtectedRoute', () => {
  beforeEach(() => {
    authState.isAuthenticated = false
    authState.isLoading = false
  })

  it('shows loading state while auth is resolving', () => {
    authState.isLoading = true
    renderProtectedRoute()
    expect(screen.getByRole('status', { name: /loading your workspace/i })).toBeInTheDocument()
  })

  it('redirects unauthenticated users to login', async () => {
    renderProtectedRoute()
    expect(await screen.findByText('Login page')).toBeInTheDocument()
  })

  it('renders protected content for authenticated users', () => {
    authState.isAuthenticated = true
    renderProtectedRoute()
    expect(screen.getByText('Dashboard content')).toBeInTheDocument()
  })
})
