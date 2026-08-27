import { beforeEach, describe, expect, it, vi } from 'vitest'
import { authService } from '@/api/authService'

describe('authService', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('calls signup with credentials included', async () => {
    const session = {
      user: { id: '1', name: 'Alex', email: 'alex@acme.dev' },
      organization: { id: 'org-1', name: 'Acme', slug: 'acme' },
      membership: { id: 'm-1', organizationId: 'org-1', role: 'owner' as const },
    }

    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify(session), {
        status: 201,
        headers: { 'Content-Type': 'application/json' },
      }),
    )

    const result = await authService.signup({
      name: 'Alex',
      email: 'alex@acme.dev',
      team: 'Acme',
      password: 'password123',
    })

    expect(result).toEqual(session)
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/v1/auth/signup',
      expect.objectContaining({
        method: 'POST',
        credentials: 'include',
      }),
    )
  })

  it('calls refresh endpoint', async () => {
    const session = {
      user: { id: '1', name: 'Alex', email: 'alex@acme.dev' },
      organization: { id: 'org-1', name: 'Acme', slug: 'acme' },
      membership: { id: 'm-1', organizationId: 'org-1', role: 'owner' as const },
    }

    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify(session), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )

    const result = await authService.refresh()
    expect(result.user.email).toBe('alex@acme.dev')
  })
})
