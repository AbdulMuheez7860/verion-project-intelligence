import { Button } from '@/components/ui/button'

interface TablePaginationProps {
  page: number
  pageSize: number
  total: number
  hasNext: boolean
  onPageChange: (page: number) => void
  label?: string
}

export function TablePagination({
  page,
  pageSize,
  total,
  hasNext,
  onPageChange,
  label = 'results',
}: TablePaginationProps) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize))
  const from = total === 0 ? 0 : (page - 1) * pageSize + 1
  const to = Math.min(page * pageSize, total)

  return (
    <nav
      className="flex flex-col gap-3 border-t border-border px-4 py-3 sm:flex-row sm:items-center sm:justify-between"
      aria-label="Pagination"
    >
      <p className="text-xs text-muted-foreground">
        {total === 0 ? `No ${label}` : `Showing ${from}–${to} of ${total} ${label}`}
      </p>
      <div className="flex items-center gap-2">
        <Button
          type="button"
          variant="outline"
          size="sm"
          disabled={page <= 1}
          onClick={() => onPageChange(page - 1)}
          aria-label="Previous page"
        >
          Previous
        </Button>
        <span className="min-w-24 text-center text-xs text-muted-foreground" aria-live="polite">
          Page {page} of {totalPages}
        </span>
        <Button
          type="button"
          variant="outline"
          size="sm"
          disabled={!hasNext}
          onClick={() => onPageChange(page + 1)}
          aria-label="Next page"
        >
          Next
        </Button>
      </div>
    </nav>
  )
}
