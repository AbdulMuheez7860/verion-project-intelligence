import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Search } from 'lucide-react'
import { allNavItems } from '@/components/navigation/nav-config'
import { useShell } from '@/components/shell/shell-context'
import { Dialog, DialogContent, DialogDescription, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { useTheme } from '@/hooks/use-theme'
import { cn } from '@/lib/utils'

type CommandItem = {
  id: string
  label: string
  description?: string
  keywords?: string[]
  disabled?: boolean
  disabledReason?: string
  action: () => void
}

export function CommandPalette() {
  const navigate = useNavigate()
  const { commandPaletteOpen, setCommandPaletteOpen } = useShell()
  const { dark, toggle } = useTheme()
  const [query, setQuery] = useState('')
  const [activeIndex, setActiveIndex] = useState(0)
  const listRef = useRef<HTMLDivElement>(null)

  const items = useMemo<CommandItem[]>(
    () => [
      ...allNavItems.map((item) => ({
        id: `nav-${item.to}`,
        label: item.label,
        description: item.description,
        keywords: [item.label, item.to],
        action: () => {
          navigate(item.to)
          setCommandPaletteOpen(false)
        },
      })),
      {
        id: 'action-connect-repo',
        label: 'Connect repository',
        description: 'Add a GitHub repository to this workspace',
        keywords: ['connect', 'repository', 'github'],
        action: () => {
          navigate('/app/repositories/connect')
          setCommandPaletteOpen(false)
        },
      },
      {
        id: 'action-run-analysis',
        label: 'Run analysis',
        description: 'Open a repository to run analysis',
        disabled: true,
        disabledReason: 'Select a repository detail page to run analysis.',
        keywords: ['analysis', 'scan'],
        action: () => undefined,
      },
      {
        id: 'action-notifications',
        label: 'Open notifications',
        description: 'View engineering alerts',
        keywords: ['notifications', 'alerts'],
        action: () => {
          navigate('/app/notifications')
          setCommandPaletteOpen(false)
        },
      },
      {
        id: 'action-settings',
        label: 'Open settings',
        description: 'Workspace configuration',
        keywords: ['settings', 'profile'],
        action: () => {
          navigate('/app/settings/general')
          setCommandPaletteOpen(false)
        },
      },
      {
        id: 'action-settings-members',
        label: 'Open members',
        description: 'Manage workspace members and access',
        keywords: ['members', 'team', 'access', 'invite'],
        action: () => {
          navigate('/app/settings/members')
          setCommandPaletteOpen(false)
        },
      },
      {
        id: 'action-settings-integrations',
        label: 'Open integrations',
        description: 'GitHub and external connections',
        keywords: ['integrations', 'github', 'connect'],
        action: () => {
          navigate('/app/settings/integrations')
          setCommandPaletteOpen(false)
        },
      },
      {
        id: 'action-settings-audit',
        label: 'Open audit log',
        description: 'Administrative activity history',
        keywords: ['audit', 'log', 'history', 'admin'],
        action: () => {
          navigate('/app/settings/audit-log')
          setCommandPaletteOpen(false)
        },
      },
      {
        id: 'action-theme',
        label: dark ? 'Switch to light theme' : 'Switch to dark theme',
        description: 'Toggle appearance',
        keywords: ['theme', 'dark', 'light'],
        action: () => {
          toggle()
          setCommandPaletteOpen(false)
        },
      },
    ],
    [dark, navigate, setCommandPaletteOpen, toggle],
  )

  const filtered = useMemo(() => {
    const normalized = query.trim().toLowerCase()
    if (!normalized) return items
    return items.filter((item) => {
      const haystack = [item.label, item.description, ...(item.keywords ?? [])].join(' ').toLowerCase()
      return haystack.includes(normalized)
    })
  }, [items, query])

  useEffect(() => {
    setActiveIndex(0)
  }, [query, commandPaletteOpen])

  useEffect(() => {
    if (!commandPaletteOpen) {
      setQuery('')
      setActiveIndex(0)
    }
  }, [commandPaletteOpen])

  useEffect(() => {
    const activeElement = listRef.current?.querySelector<HTMLElement>(`[data-index="${activeIndex}"]`)
    activeElement?.scrollIntoView?.({ block: 'nearest' })
  }, [activeIndex, filtered])

  const selectItem = (item: CommandItem) => {
    if (item.disabled) return
    item.action()
  }

  return (
    <Dialog open={commandPaletteOpen} onOpenChange={setCommandPaletteOpen}>
      <DialogContent showClose={false} className="gap-0 overflow-hidden p-0 sm:max-w-xl">
        <DialogTitle className="sr-only">Command palette</DialogTitle>
        <DialogDescription className="sr-only">
          Search navigation and actions. Use arrow keys to move and Enter to select.
        </DialogDescription>
        <div className="flex items-center gap-2 border-b border-border px-4 py-3">
          <Search className="size-4 text-muted-foreground" aria-hidden="true" />
          <Input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search pages and actions…"
            className="border-0 bg-transparent px-0 shadow-none focus-visible:ring-0"
            autoFocus
            onKeyDown={(event) => {
              if (event.key === 'ArrowDown') {
                event.preventDefault()
                setActiveIndex((current) => Math.min(current + 1, Math.max(filtered.length - 1, 0)))
              }
              if (event.key === 'ArrowUp') {
                event.preventDefault()
                setActiveIndex((current) => Math.max(current - 1, 0))
              }
              if (event.key === 'Enter') {
                event.preventDefault()
                const item = filtered[activeIndex]
                if (item) selectItem(item)
              }
            }}
          />
        </div>
        <div ref={listRef} className="max-h-80 overflow-y-auto p-2" role="listbox" aria-label="Commands">
          {filtered.length === 0 ? (
            <p className="px-3 py-6 text-center text-supporting">No matching commands.</p>
          ) : (
            filtered.map((item, index) => (
              <button
                key={item.id}
                type="button"
                data-index={index}
                role="option"
                aria-selected={index === activeIndex}
                disabled={item.disabled}
                className={cn(
                  'flex w-full items-start gap-3 rounded-md px-3 py-2.5 text-left transition-colors',
                  index === activeIndex ? 'bg-accent text-accent-foreground' : 'hover:bg-muted/70',
                  item.disabled && 'cursor-not-allowed opacity-60',
                )}
                onMouseEnter={() => setActiveIndex(index)}
                onClick={() => selectItem(item)}
              >
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium">{item.label}</p>
                  <p className="text-metadata">
                    {item.disabled ? item.disabledReason : item.description}
                  </p>
                </div>
              </button>
            ))
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}
