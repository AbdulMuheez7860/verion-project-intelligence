import { useEffect } from 'react'
import { cleanup, render, screen, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { CommandPalette } from '@/components/command-palette/command-palette'
import { ShellProvider, useShell } from '@/components/shell/shell-context'

vi.mock('@/hooks/use-theme', () => ({
  useTheme: () => ({ dark: false, toggle: vi.fn() }),
}))

function OpenPaletteOnMount() {
  const { setCommandPaletteOpen } = useShell()
  useEffect(() => {
    setCommandPaletteOpen(true)
  }, [setCommandPaletteOpen])
  return null
}

function renderPalette() {
  return render(
    <MemoryRouter>
      <ShellProvider>
        <OpenPaletteOnMount />
        <CommandPalette />
      </ShellProvider>
    </MemoryRouter>,
  )
}

describe('CommandPalette', () => {
  afterEach(() => {
    cleanup()
  })

  it('filters navigation items by query', async () => {
    renderPalette()

    const search = await screen.findByPlaceholderText(/search pages and actions/i)
    fireEvent.change(search, { target: { value: 'security' } })

    expect(screen.getByRole('option', { name: /security/i })).toBeInTheDocument()
    expect(screen.queryByRole('option', { name: /^dashboard$/i })).not.toBeInTheDocument()
  })

  it('shows disabled run analysis action with explanation', async () => {
    renderPalette()

    const search = await screen.findByPlaceholderText(/search pages and actions/i)
    fireEvent.change(search, { target: { value: 'run analysis' } })

    const option = screen.getByRole('option', { name: /run analysis/i })
    expect(option).toBeDisabled()
    expect(screen.getByText(/select a repository detail page/i)).toBeInTheDocument()
  })

  it('includes settings shortcuts', async () => {
    renderPalette()

    const search = await screen.findByPlaceholderText(/search pages and actions/i)
    fireEvent.change(search, { target: { value: 'audit log' } })

    expect(screen.getByRole('option', { name: /open audit log/i })).toBeInTheDocument()
  })
})
