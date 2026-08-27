import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import { SettingsLayout } from '@/features/settings/settings-layout'

vi.mock('@/hooks/use-permissions', () => ({
  usePermissions: () => ({
    can: () => true,
    role: 'owner',
    isAdmin: true,
  }),
}))

describe('SettingsLayout', () => {
  it('renders settings navigation links', () => {
    render(
      <MemoryRouter initialEntries={['/app/settings/general']}>
        <Routes>
          <Route path="/app/settings" element={<SettingsLayout />}>
            <Route path="general" element={<div>General content</div>} />
          </Route>
        </Routes>
      </MemoryRouter>,
    )
    expect(screen.getByRole('navigation', { name: 'Settings' })).toBeInTheDocument()
    const nav = screen.getByRole('navigation', { name: 'Settings' })
    expect(nav).toHaveTextContent('Members & Access')
    expect(nav).toHaveTextContent('Audit Log')
  })
})
