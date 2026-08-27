import { Link } from 'react-router-dom'
import { AlertTriangle } from 'lucide-react'
import { EmptyState } from '@/components/states/empty-state'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import type { AttentionItem } from '@/types/api'

export function AttentionSection({ items }: { items: AttentionItem[] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Requires attention</CardTitle>
      </CardHeader>
      <CardContent>
        {items.length === 0 ? (
          <EmptyState
            title="No immediate risks"
            description="Critical findings, failed analyses, and high-risk pull requests will appear here."
            icon={<AlertTriangle className="size-5" aria-hidden="true" />}
            className="min-h-32"
          />
        ) : (
          <ul className="divide-y divide-border">
            {items.map((item) => (
              <li key={item.id} className="flex flex-col gap-3 py-4 first:pt-0 last:pb-0 sm:flex-row sm:items-start sm:justify-between">
                <div className="min-w-0 space-y-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge severity={item.severity}>{item.severity}</Badge>
                    {item.repositoryName ? (
                      <span className="text-metadata">{item.repositoryName}</span>
                    ) : null}
                  </div>
                  <p className="text-sm font-medium">{item.title}</p>
                  <p className="text-supporting">{item.description}</p>
                </div>
                <Link
                  to={item.href}
                  className="shrink-0 text-sm font-medium text-primary hover:underline"
                >
                  {item.actionLabel ?? 'View'}
                </Link>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  )
}
